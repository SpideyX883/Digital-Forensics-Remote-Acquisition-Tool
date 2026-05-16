# ===========================
# agent_core.py (REWRITTEN)
# ===========================

import time
from datetime import datetime

from config import debug_print, log_error, AGENT_POLL_INTERVAL
from agent.controller_client import ControllerClient
from agent.heartbeat import HeartbeatManager
from agent.acquisition import AcquisitionDispatcher
from agent.evidence_processor import EvidenceProcessor
from agent.system_utils import SystemInfo


class ForensicAgent:
    def __init__(self, controller_url, agent_name=None, heartbeat_interval=30, debug_mode=False):
        self.controller_url = controller_url
        self.agent_name = agent_name
        self.heartbeat_interval = heartbeat_interval
        self.debug_mode = debug_mode

        self.running = False
        self.agent_id = None

        # Components
        self.client = ControllerClient(controller_url, debug_mode)
        self.heartbeat = HeartbeatManager(self.client, heartbeat_interval, debug_mode)
        self.dispatcher = AcquisitionDispatcher(debug_mode)
        self.processor = EvidenceProcessor(debug_mode)

    # -------------------------
    # Safe cleanup helpers
    # -------------------------
    def _safe_cleanup_processor(self):
        """
        EvidenceProcessor in your project doesn't always have cleanup().
        Call it only if it exists; otherwise do nothing.
        """
        try:
            fn = getattr(self.processor, "cleanup", None)
            if callable(fn):
                fn()
        except Exception as e:
            log_error("EvidenceProcessor cleanup failed", e)

    # -------------------------
    # Registration
    # -------------------------
    def register(self):
        """Register with controller"""
        try:
            debug_print("Starting agent registration...")

            self.agent_id = SystemInfo.generate_agent_id(self.agent_name)

            print(f"Agent ID: {self.agent_id}")
            print(f"Agent Name: {self.agent_name or SystemInfo.get_hostname()}")
            print(f"Hostname: {SystemInfo.get_hostname()}")
            print(f"OS: {SystemInfo.get_os_info()}")
            print(f"Controller: {self.controller_url}")

            success = self.client.register(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                debug_mode=self.debug_mode,
            )

            if success:
                debug_print("✅ Agent registered successfully")
                return True

            debug_print("❌ Agent registration failed")
            return False

        except Exception as e:
            log_error("Agent registration failed", e)
            return False

    # -------------------------
    # Main loop
    # -------------------------
    def run(self):
        """Main agent loop"""
        try:
            debug_print("Starting agent main loop...")

            # Start heartbeat
            self.heartbeat.start(self.agent_id)

            self.running = True
            poll_count = 0

            while self.running:
                try:
                    poll_count += 1
                    debug_print(f"Poll #{poll_count}: Checking for tasks...")

                    tasks = self.client.get_tasks(self.agent_id)

                    if tasks:
                        debug_print(f"Received {len(tasks)} task(s)")
                        for task in tasks:
                            self.execute_task(task)
                    else:
                        if poll_count % 10 == 0:
                            print(f"⏳ Waiting for tasks... (Poll #{poll_count})")

                    time.sleep(AGENT_POLL_INTERVAL)

                except KeyboardInterrupt:
                    print("\n⚠️  Shutting down agent...")
                    self.running = False
                    break

                except Exception as e:
                    log_error("Error in main loop", e)
                    time.sleep(10)

        except Exception as e:
            log_error("Agent run loop failed", e)

        finally:
            self.cleanup()

    # -------------------------
    # Task execution
    # -------------------------
    def execute_task(self, task):
        """
        Expected controller payload (from your logs):
        task = {
          "task_id": 3,
          "task_type": "...",
          "command": {"action":"disk", "case_id":"...", ...}
        }
        """
        task_id = task.get("task_id")
        command = task.get("command") or {}
        action = (command.get("action") or "").lower()

        print(f"🎯 TASK {task_id}: {action.upper() if action else 'UNKNOWN'}")

        try:
            if not task_id:
                raise ValueError("Task payload missing task_id")

            if not isinstance(command, dict):
                raise ValueError(f"Task command must be dict, got {type(command).__name__}")

            if action != "disk":
                raise ValueError(f"Unsupported task action: {action}")

            # ✅ Correct call: pass action + FULL command dict
            evidence_path, evidence_type = self.dispatcher.acquire(action, command)

            if not evidence_path:
                raise Exception("Failed to acquire disk evidence (evidence_path is empty)")

            # Process evidence into forensic package
            case_id = command.get("case_id", "UNKNOWN")
            archive_path, verification_data = self.processor.process(
                evidence_path, case_id, evidence_type, self.agent_id
            )

            if not archive_path:
                raise Exception("Failed to process evidence (archive_path is empty)")

            # Upload to controller
            success = self.client.upload_evidence(
                task_id=task_id,
                archive_path=archive_path,
                verification_data=verification_data,
                case_id=case_id,
                evidence_type=evidence_type,
                agent_id=self.agent_id,
            )

            if not success:
                raise Exception("Upload failed")

            self.client.report_task_status(task_id, "completed")
            print(f"✅ Task {task_id} completed successfully")

        except Exception as e:
            print(f"❌ Task {task_id} failed: {e}")
            try:
                self.client.report_task_status(task_id, "failed", {"error": str(e)})
            except Exception as report_err:
                log_error("Failed to report task failure", report_err)

        finally:
            self._safe_cleanup_processor()
            print("=" * 50 + "\n")

    # -------------------------
    # Cleanup
    # -------------------------
    def cleanup(self):
        """Cleanup before exit"""
        print("\n🧹 Cleaning up agent...")
        try:
            self.heartbeat.stop()
        except Exception as e:
            log_error("Failed to stop heartbeat", e)

        self._safe_cleanup_processor()
        print("👋 Agent shutdown complete")
