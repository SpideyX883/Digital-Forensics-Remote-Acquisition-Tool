"""
API endpoint handlers for the controller
"""

import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime

from flask import request, jsonify

from config import EVIDENCE_DIR, debug_print, log_error
from controller.database import get_connection, close_connection
from controller.forensic_utils import ForensicUtils
from controller.logging_utils import log_system_event, log_chain_of_custody


# -------------------------
# Helpers
# -------------------------
def _safe_json_loads(value, default=None):
    if default is None:
        default = {}
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _ensure_case_exists(case_id: str):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT case_id FROM cases WHERE case_id = ?", (case_id,))
        return cursor.fetchone() is not None
    finally:
        try:
            if cursor:
                cursor.close()
        finally:
            close_connection()


def _ensure_agent_exists(agent_id: str):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT agent_id FROM agents WHERE agent_id = ?", (agent_id,))
        return cursor.fetchone() is not None
    finally:
        try:
            if cursor:
                cursor.close()
        finally:
            close_connection()


def _make_case_dir(case_id: str) -> str:
    case_dir = os.path.join(EVIDENCE_DIR, f"case_{case_id}")
    os.makedirs(case_dir, exist_ok=True)
    return case_dir


def _pick_first_evidence_file(directory: str):
    exts = (".raw", ".dd", ".pcap", ".bin", ".dmp", ".txt", ".log", ".csv")
    for name in os.listdir(directory):
        if name.lower().endswith(exts):
            return name
    return None


# -------------------------
# Main registration
# -------------------------
def register_api_endpoints(app):
    """Register all API endpoints"""

    # ==================== STATS ENDPOINTS ====================
    @app.route("/api/stats")
    def get_stats():
        """Get dashboard statistics"""
        conn = None
        cursor = None
        try:
            debug_print("Getting dashboard stats")
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM cases")
            cases = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM agents")
            total_agents = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM agents WHERE status = 'online'")
            online_agents = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM evidence")
            evidence = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tasks WHERE task_status = 'pending'")
            tasks = cursor.fetchone()[0]

            return jsonify(
                {
                    "success": True,
                    "cases": cases,
                    "agents": total_agents,
                    "online_agents": online_agents,
                    "evidence": evidence,
                    "tasks": tasks,
                }
            )
        except Exception as e:
            log_error("Failed to get stats", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            finally:
                close_connection()

    # ==================== AGENT ENDPOINTS ====================
    @app.route("/api/agents")
    def list_agents():
        """List all agents"""
        conn = None
        cursor = None
        try:
            status_filter = request.args.get("status")

            conn = get_connection()
            cursor = conn.cursor()

            if status_filter:
                cursor.execute(
                    """
                    SELECT agent_id, hostname, os, status, last_seen, ip_address
                    FROM agents
                    WHERE status = ?
                    ORDER BY last_seen DESC
                    """,
                    (status_filter,),
                )
            else:
                cursor.execute(
                    """
                    SELECT agent_id, hostname, os, status, last_seen, ip_address
                    FROM agents
                    ORDER BY status DESC, last_seen DESC
                    """
                )

            rows = cursor.fetchall()
            agents = [
                {
                    "agent_id": r[0],
                    "hostname": r[1],
                    "os": r[2],
                    "status": r[3],
                    "last_seen": r[4],
                    "ip_address": r[5],
                }
                for r in rows
            ]
            return jsonify({"success": True, "agents": agents})
        except Exception as e:
            log_error("Failed to list agents", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            finally:
                close_connection()

    @app.route("/api/agents/register", methods=["POST"])
    def register_agent():
        """Agent registration"""
        conn = None
        cursor = None
        try:
            data = request.get_json(silent=True) or {}
            agent_id = data.get("agent_id")
            hostname = data.get("hostname", "Unknown")
            os_info = data.get("os", "Unknown")
            ip_address = request.remote_addr

            if not agent_id:
                return jsonify({"success": False, "error": "Agent ID required"}), 400

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO agents
                    (agent_id, hostname, ip_address, os, status, last_seen)
                VALUES (?, ?, ?, ?, 'online', CURRENT_TIMESTAMP)
                """,
                (agent_id, hostname, ip_address, os_info),
            )
            conn.commit()

            log_system_event(
                "INFO",
                "agent",
                f"Agent registered: {agent_id}",
                {"hostname": hostname, "os": os_info, "ip": ip_address},
            )

            return jsonify(
                {"success": True, "message": "Agent registered", "server_time": datetime.now().isoformat()}
            )
        except Exception as e:
            log_error("Agent registration failed", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            finally:
                close_connection()

    @app.route("/api/agents/<agent_id>/tasks")
    def get_agent_tasks(agent_id):
        """Get pending tasks for agent (marks them executing)"""
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE agents
                SET last_seen = CURRENT_TIMESTAMP, status = 'online'
                WHERE agent_id = ?
                """,
                (agent_id,),
            )

            cursor.execute(
                """
                SELECT task_id, task_type, command_json
                FROM tasks
                WHERE agent_id = ? AND task_status = 'pending'
                ORDER BY created_at
                """,
                (agent_id,),
            )
            rows = cursor.fetchall()

            tasks = []
            for task_id, task_type, command_json in rows:
                cursor.execute(
                    """
                    UPDATE tasks
                    SET task_status = 'executing', started_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                    """,
                    (task_id,),
                )

                command = _safe_json_loads(command_json, default={"raw": command_json} if command_json else {})
                tasks.append({"task_id": task_id, "task_type": task_type, "command": command})

            conn.commit()

            log_system_event("INFO", "agent_tasks", f"Agent {agent_id} fetched {len(tasks)} tasks")
            return jsonify({"success": True, "tasks": tasks})
        except Exception as e:
            log_error(f"Failed to get tasks for agent {agent_id}", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            finally:
                close_connection()

    # ==================== TASK ENDPOINTS ====================
    @app.route("/api/tasks/create", methods=["POST"])
    def create_task():
        """Create new task"""
        conn = None
        cursor = None
        try:
            data = request.get_json(silent=True) or {}
            agent_id = data.get("agent_id")
            case_id = data.get("case_id")
            task_type = data.get("task_type")

            if not all([agent_id, case_id, task_type]):
                return jsonify({"success": False, "error": "Missing required fields"}), 400

            # Validate existence
            if not _ensure_case_exists(case_id):
                return jsonify({"success": False, "error": f"Case {case_id} not found"}), 404
            if not _ensure_agent_exists(agent_id):
                return jsonify({"success": False, "error": f"Agent {agent_id} not found"}), 404

            command = {"action": task_type, "case_id": case_id, "timestamp": datetime.now().isoformat()}

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tasks
                    (agent_id, case_id, task_type, command_json, created_by, task_status)
                VALUES (?, ?, ?, ?, 'system', 'pending')
                """,
                (agent_id, case_id, task_type, json.dumps(command)),
            )
            task_id = cursor.lastrowid
            conn.commit()

            log_system_event(
                "INFO",
                "task",
                f"Task created: {task_id}",
                {"agent_id": agent_id, "case_id": case_id, "task_type": task_type},
            )

            return jsonify({"success": True, "task_id": task_id, "message": f"Task created for agent {agent_id}"})
        except Exception as e:
            log_error("Task creation failed", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            finally:
                close_connection()

    @app.route("/api/tasks/<int:task_id>/update", methods=["POST"])
    def update_task_status(task_id):
        """Update task status"""
        conn = None
        cursor = None
        try:
            data = request.get_json(silent=True) or {}
            status = data.get("status")
            result = data.get("result", {})

            if not status:
                return jsonify({"success": False, "error": "Missing status"}), 400

            conn = get_connection()
            cursor = conn.cursor()

            if status in ["completed", "failed"]:
                cursor.execute(
                    """
                    UPDATE tasks
                    SET task_status = ?, completed_at = CURRENT_TIMESTAMP, result_json = ?
                    WHERE task_id = ?
                    """,
                    (status, json.dumps(result), task_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE tasks
                    SET task_status = ?, result_json = ?
                    WHERE task_id = ?
                    """,
                    (status, json.dumps(result), task_id),
                )

            conn.commit()
            log_system_event("INFO", "task", f"Task {task_id} status updated to {status}", result)
            return jsonify({"success": True})
        except Exception as e:
            log_error(f"Failed to update task {task_id}", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            finally:
                close_connection()

    @app.route("/api/tasks")
    def list_tasks():
        """List all tasks"""
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT task_id, task_type, agent_id, case_id, task_status, created_at
                FROM tasks
                ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall()
            tasks = [
                {
                    "task_id": r[0],
                    "task_type": r[1],
                    "agent_id": r[2],
                    "case_id": r[3],
                    "task_status": r[4],
                    "created_at": r[5],
                }
                for r in rows
            ]
            return jsonify({"success": True, "tasks": tasks})
        except Exception as e:
            log_error("Failed to list tasks", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            finally:
                close_connection()

    # ==================== EVIDENCE ENDPOINTS ====================
    @app.route("/api/evidence/upload_forensic", methods=["POST"])
    def upload_forensic_evidence():
        """
        Upload forensic evidence package from agent.
        IMPORTANT: evidence_id is INTEGER AUTOINCREMENT in DB, so we do NOT insert it.
        """
        debug_print("=" * 60)
        debug_print("📥 FORENSIC EVIDENCE UPLOAD")
        debug_print("=" * 60)

        temp_dir = None
        conn = None
        cursor = None

        try:
            task_id = request.form.get("task_id")
            evidence_type = request.form.get("evidence_type")
            case_id = request.form.get("case_id")
            original_hash = request.form.get("original_hash")
            archive_hash = request.form.get("archive_hash")
            agent_id = request.form.get("agent_id")

            if not case_id or not evidence_type or not original_hash or not archive_hash:
                return jsonify({"success": False, "error": "Missing required form fields"}), 400

            if "archive" not in request.files:
                return jsonify({"success": False, "error": "No archive provided"}), 400

            archive_file = request.files["archive"]
            if not archive_file or archive_file.filename == "":
                return jsonify({"success": False, "error": "No archive selected"}), 400

            verification_data = _safe_json_loads(request.form.get("verification_data"), default={})

            # Save archive temporarily
            temp_dir = tempfile.mkdtemp(prefix="forensic_upload_")
            archive_path = os.path.join(temp_dir, archive_file.filename)
            archive_file.save(archive_path)

            # Step 1: Verify archive hash
            archive_match, actual_archive_hash = ForensicUtils.verify_hash(archive_path, archive_hash)
            if not archive_match:
                log_system_event(
                    "ERROR",
                    "evidence",
                    "Archive hash mismatch",
                    {"expected": archive_hash, "actual": actual_archive_hash, "task_id": task_id},
                )
                return jsonify({"success": False, "error": "Archive integrity check failed"}), 400

            # Step 2: Extract and verify archive
            verification_report = ForensicUtils.extract_and_verify_archive(archive_path, archive_hash)
            if not verification_report.get("success"):
                log_system_event("ERROR", "evidence", "Archive verification failed", verification_report)
                return jsonify(
                    {"success": False, "error": "Archive verification failed", "details": verification_report.get("errors")}
                ), 400

            extracted_path = verification_report.get("extracted_path")
            if not extracted_path or not os.path.exists(extracted_path):
                return jsonify({"success": False, "error": "Extracted evidence not found"}), 400

            # Pick evidence file from extracted folder
            evidence_file_name = _pick_first_evidence_file(extracted_path)
            if not evidence_file_name:
                return jsonify({"success": False, "error": "No evidence file found in package"}), 400

            # Insert DB record FIRST to get integer evidence_id (schema)
            conn = get_connection()
            cursor = conn.cursor()

            # We store the agent-provided evidence tag (if any) in metadata_json for reference
            metadata = verification_report.get("metadata", {}) or {}
            if verification_data:
                metadata["verification_data"] = verification_data

            # We don't know final file_path yet because we will move to evidence_<id>
            # We'll set file_path after moving, via UPDATE.
            cursor.execute(
                """
                INSERT INTO evidence (
                    case_id, agent_id, task_id, evidence_type,
                    original_filename, stored_filename, file_path, file_size,
                    compressed_size,
                    original_hash, archive_hash, hash_match, acquisition_time,
                    metadata_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id,
                    agent_id,
                    int(task_id) if task_id else None,
                    evidence_type,
                    evidence_file_name,
                    evidence_file_name,
                    "",  # placeholder file_path, updated after move
                    None,  # file_size updated after move
                    None,  # compressed_size optional
                    original_hash,
                    archive_hash,
                    True,
                    datetime.now().isoformat(),
                    json.dumps(metadata),
                    "verified",
                ),
            )
            db_evidence_id = cursor.lastrowid

            # Move extracted folder to permanent location: case_<case_id>/evidence_<db_id>/
            case_dir = _make_case_dir(case_id)
            permanent_dir = os.path.join(case_dir, f"evidence_{db_evidence_id}")
            if os.path.exists(permanent_dir):
                shutil.rmtree(permanent_dir, ignore_errors=True)
            shutil.move(extracted_path, permanent_dir)

            evidence_file_path = os.path.join(permanent_dir, evidence_file_name)
            file_size = os.path.getsize(evidence_file_path)

            # Update evidence row with real file_path + file_size
            cursor.execute(
                """
                UPDATE evidence
                SET file_path = ?, file_size = ?
                WHERE evidence_id = ?
                """,
                (evidence_file_path, file_size, db_evidence_id),
            )

            # Update task if task_id provided
            if task_id:
                cursor.execute(
                    """
                    UPDATE tasks
                    SET task_status = 'completed',
                        completed_at = CURRENT_TIMESTAMP,
                        result_json = ?
                    WHERE task_id = ?
                    """,
                    (json.dumps({"evidence_id": db_evidence_id, "verification_success": True}), int(task_id)),
                )

            # Update agent last_seen
            if agent_id:
                cursor.execute(
                    "UPDATE agents SET last_seen = CURRENT_TIMESTAMP WHERE agent_id = ?",
                    (agent_id,),
                )

            conn.commit()

            # Chain of custody uses INTEGER evidence_id (schema)
            log_chain_of_custody(
                evidence_id=db_evidence_id,
                action="received_and_verified",
                actor_id=agent_id,
                actor_type="agent",
                hash_before=original_hash,
                hash_after=original_hash,
            )

            log_system_event(
                "INFO",
                "evidence",
                f"Evidence {db_evidence_id} stored successfully",
                {
                    "evidence_id": db_evidence_id,
                    "case_id": case_id,
                    "original_hash": original_hash,
                    "archive_hash": archive_hash,
                    "file_path": evidence_file_path,
                    "file_size": file_size,
                },
            )

            return jsonify(
                {
                    "success": True,
                    "evidence_id": db_evidence_id,
                    "case_id": case_id,
                    "original_hash": original_hash,
                    "archive_hash": archive_hash,
                    "storage_path": permanent_dir,
                    "verification_report": verification_report,
                    "message": "Evidence verified and stored",
                }
            )

        except sqlite3.Error as db_err:
            log_error("Evidence processing database error", db_err)
            return jsonify({"success": False, "error": str(db_err)}), 500
        except Exception as e:
            log_error("Evidence upload endpoint failed", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            finally:
                close_connection()

            if temp_dir:
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass

    @app.route("/api/evidence/upload_file", methods=["POST"])
    def upload_file_evidence():
        """
        Upload evidence from web UI.
        IMPORTANT: do NOT store file_path inside a temp folder that you later delete.
        """
        debug_print("=" * 60)
        debug_print("📁 FILE EVIDENCE UPLOAD (Web Interface)")
        debug_print("=" * 60)

        temp_dir = None
        conn = None
        cursor = None

        try:
            case_id = request.form.get("case_id")
            evidence_type = request.form.get("evidence_type", "file_transfer")
            description = request.form.get("description", "")

            if not case_id:
                return jsonify({"success": False, "error": "Case ID required"}), 400
            if not _ensure_case_exists(case_id):
                return jsonify({"success": False, "error": f"Case {case_id} not found"}), 404

            if "file" not in request.files:
                return jsonify({"success": False, "error": "No file provided"}), 400

            up_file = request.files["file"]
            if not up_file or up_file.filename == "":
                return jsonify({"success": False, "error": "No file selected"}), 400

            # Save upload to temp (just for packaging/hash), but we will move to permanent folder after DB insert
            temp_dir = tempfile.mkdtemp(prefix="file_upload_")
            temp_file_path = os.path.join(temp_dir, up_file.filename)
            up_file.save(temp_file_path)

            metadata = {
                "description": description,
                "upload_method": "web_interface",
                "uploader_ip": request.remote_addr,
            }

            # Create forensic package (keeps your existing flow)
            archive_path, verification_data = ForensicUtils.create_forensic_package(
                source_file=temp_file_path,
                case_id=case_id,
                evidence_type=evidence_type,
                metadata=metadata,
            )
            if not archive_path or not verification_data:
                return jsonify({"success": False, "error": "Failed to create forensic package"}), 500

            original_hash = verification_data.get("original_hash")
            archive_hash = verification_data.get("archive_hash")
            if not original_hash or not archive_hash:
                return jsonify({"success": False, "error": "Verification data missing hashes"}), 500

            # Insert evidence row to get db_evidence_id
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO evidence (
                    case_id, agent_id, task_id, evidence_type,
                    original_filename, stored_filename, file_path, file_size,
                    compressed_size,
                    original_hash, archive_hash, hash_match, acquisition_time,
                    metadata_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id,
                    None,
                    None,
                    evidence_type,
                    up_file.filename,
                    up_file.filename,
                    "",  # placeholder path (updated after move)
                    None,  # updated after move
                    None,  # compressed_size optional
                    original_hash,
                    archive_hash,
                    True,
                    datetime.now().isoformat(),
                    json.dumps(verification_data.get("metadata", metadata)),
                    "verified",
                ),
            )
            db_evidence_id = cursor.lastrowid

            # Permanent storage
            case_dir = _make_case_dir(case_id)
            permanent_dir = os.path.join(case_dir, f"evidence_{db_evidence_id}")
            os.makedirs(permanent_dir, exist_ok=True)

            permanent_path = os.path.join(permanent_dir, up_file.filename)
            shutil.move(temp_file_path, permanent_path)

            file_size = os.path.getsize(permanent_path)

            cursor.execute(
                "UPDATE evidence SET file_path = ?, file_size = ? WHERE evidence_id = ?",
                (permanent_path, file_size, db_evidence_id),
            )

            conn.commit()

            # Chain of custody uses INTEGER evidence_id
            log_chain_of_custody(
                evidence_id=db_evidence_id,
                action="file_upload",
                actor_id="web_interface",
                actor_type="system",
                hash_before=original_hash,
                hash_after=original_hash,
            )

            log_system_event(
                "INFO",
                "evidence",
                f"File evidence uploaded: {db_evidence_id}",
                {"evidence_id": db_evidence_id, "case_id": case_id, "filename": up_file.filename, "size": file_size},
            )

            return jsonify(
                {
                    "success": True,
                    "evidence_id": db_evidence_id,
                    "case_id": case_id,
                    "original_hash": original_hash,
                    "archive_hash": archive_hash,
                    "filename": up_file.filename,
                    "size": file_size,
                    "storage_path": permanent_dir,
                    "message": "File uploaded as forensic evidence",
                }
            )

        except sqlite3.Error as db_err:
            log_error("SQLite database error during file upload", db_err)
            return jsonify({"success": False, "error": str(db_err)}), 500
        except Exception as e:
            log_error("File evidence upload failed", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            finally:
                close_connection()

            # Cleanup only temp workspace (NOT permanent evidence)
            if temp_dir:
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass

            # If your forensic_utils creates an archive in temp somewhere else, you can optionally delete it there.
            # We do NOT delete permanent stored evidence.

    @app.route("/api/evidence")
    def list_evidence():
        """List all evidence"""
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT evidence_id, case_id, agent_id, evidence_type, original_hash,
                       file_size, created_at, original_filename
                FROM evidence
                ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall()

            evidence_list = [
                {
                    "evidence_id": r[0],
                    "case_id": r[1],
                    "agent_id": r[2],
                    "evidence_type": r[3],
                    "original_hash": r[4],
                    "file_size": r[5],
                    "created_at": r[6],
                    "original_filename": r[7],
                }
                for r in rows
            ]
            return jsonify({"success": True, "evidence": evidence_list})
        except Exception as e:
            log_error("Failed to list evidence", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            finally:
                close_connection()

    @app.route("/api/evidence/<int:evidence_id>/verify")
    def verify_evidence(evidence_id: int):
        """Verify evidence integrity"""
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT file_path, original_hash, original_filename
                FROM evidence
                WHERE evidence_id = ?
                """,
                (evidence_id,),
            )
            row = cursor.fetchone()
            if not row:
                return jsonify({"success": False, "error": "Evidence not found"}), 404

            file_path, expected_hash, filename = row

            verification = {"evidence_id": evidence_id, "filename": filename, "steps": [], "success": False}

            if os.path.exists(file_path):
                verification["steps"].append({"step": "file_exists", "success": True, "message": "Evidence file found on disk"})
            else:
                verification["steps"].append({"step": "file_exists", "success": False, "message": "Evidence file not found on disk"})
                return jsonify({"success": True, "verification": verification})

            current_hash = ForensicUtils.calculate_hash(file_path)
            verification["steps"].append(
                {"step": "hash_calculation", "success": current_hash is not None, "message": "Current hash calculated", "current_hash": current_hash}
            )

            if current_hash:
                match = current_hash == expected_hash
                verification["steps"].append(
                    {
                        "step": "hash_verification",
                        "success": match,
                        "message": "Hash verification",
                        "expected_hash": expected_hash,
                        "current_hash": current_hash,
                        "match": match,
                    }
                )
                verification["success"] = match

            return jsonify({"success": True, "verification": verification})
        except Exception as e:
            log_error(f"Failed to verify evidence {evidence_id}", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            finally:
                close_connection()

    # ==================== CASE ENDPOINTS ====================
    @app.route("/api/cases")
    def list_cases():
        """List all cases"""
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT case_id, case_name, investigator, status, created_at, description
                FROM cases
                ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall()
            cases = [
                {
                    "case_id": r[0],
                    "case_name": r[1],
                    "investigator": r[2],
                    "status": r[3],
                    "created_at": r[4],
                    "description": r[5],
                }
                for r in rows
            ]
            return jsonify({"success": True, "cases": cases})
        except Exception as e:
            log_error("Failed to list cases", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            finally:
                close_connection()

    @app.route("/api/cases/create", methods=["POST"])
    def create_case():
        """Create new case"""
        conn = None
        cursor = None
        try:
            data = request.get_json(silent=True) or {}
            case_id = data.get("case_id")
            case_name = data.get("case_name", "")
            description = data.get("description", "")

            if not case_id:
                return jsonify({"success": False, "error": "Case ID required"}), 400

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT case_id FROM cases WHERE case_id = ?", (case_id,))
            if cursor.fetchone():
                return jsonify({"success": False, "error": f"Case {case_id} already exists"}), 400

            cursor.execute(
                """
                INSERT INTO cases (case_id, case_name, investigator, status, description)
                VALUES (?, ?, 'admin', 'open', ?)
                """,
                (case_id, case_name, description),
            )
            conn.commit()

            log_system_event("INFO", "case", f"Case created: {case_id}", {"case_id": case_id, "case_name": case_name})
            return jsonify({"success": True, "case_id": case_id, "message": "Case created successfully"})
        except Exception as e:
            log_error("Case creation failed", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            finally:
                close_connection()

    # ==================== SYSTEM ENDPOINTS ====================
    @app.route("/api/status")
    def server_status():
        """Server status endpoint"""
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM agents WHERE status = 'online'")
            online_agents = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM agents")
            total_agents = cursor.fetchone()[0]

            return jsonify(
                {
                    "success": True,
                    "status": "online",
                    "server_time": datetime.now().isoformat(),
                    "version": "1.0",
                    "agents": {"online": online_agents, "total": total_agents},
                }
            )
        except Exception as e:
            log_error("Status endpoint failed", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            finally:
                close_connection()

    @app.route("/api/debug/logs")
    def get_debug_logs():
        """Get recent system logs for debugging"""
        conn = None
        cursor = None
        try:
            limit_raw = request.args.get("limit", "100")
            try:
                limit = int(limit_raw)
            except ValueError:
                limit = 100

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT log_timestamp, log_level, log_component, log_message, extra_data
                FROM system_logs
                ORDER BY log_timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

            logs = [{"timestamp": r[0], "level": r[1], "component": r[2], "message": r[3], "extra": r[4]} for r in rows]
            return jsonify({"success": True, "logs": logs})
        except Exception as e:
            log_error("Failed to get debug logs", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            finally:
                close_connection()

    @app.route("/api/debug/schema")
    def debug_schema():
        """Debug endpoint to check database schema"""
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(evidence)")
            schema = cursor.fetchall()

            schema_info = [
                {"cid": c[0], "name": c[1], "type": c[2], "notnull": c[3], "default": c[4], "pk": c[5]}
                for c in schema
            ]
            return jsonify({"success": True, "schema": schema_info, "message": "Evidence table schema"})
        except Exception as e:
            log_error("Failed to get schema", e)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                if cursor:
                    cursor.close()
            finally:
                close_connection()

    debug_print("✅ All API endpoints registered")
    return app
