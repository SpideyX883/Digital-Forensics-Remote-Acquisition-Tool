"""
Database models and operations - FIXED for concurrency
"""
import sqlite3
import json
import threading
from datetime import datetime
from config import DATABASE_FILE, debug_print, log_error

# Thread-local storage for DB connections
thread_local = threading.local()


def get_connection():
    """Get database connection with thread safety"""
    try:
        if not hasattr(thread_local, "connection") or thread_local.connection is None:
            conn = sqlite3.connect(
                DATABASE_FILE,
                timeout=30,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row

            # Concurrency and safety settings
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute("PRAGMA foreign_keys = ON")

            thread_local.connection = conn
            debug_print("Created new database connection for thread")

        return thread_local.connection

    except Exception as e:
        log_error("Failed to get database connection", e)
        raise


def close_connection():
    """Close database connection for this thread"""
    try:
        if hasattr(thread_local, "connection") and thread_local.connection:
            thread_local.connection.close()
            thread_local.connection = None
            debug_print("Closed database connection for thread")
    except Exception as e:
        debug_print(f"Error closing connection: {e}")


def init_database():
    """Initialize database with all tables"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'investigator',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Cases
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                case_name TEXT NOT NULL,
                investigator TEXT,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)

        # Agents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                hostname TEXT NOT NULL,
                ip_address TEXT,
                os TEXT,
                status TEXT DEFAULT 'offline',
                last_seen TIMESTAMP,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved BOOLEAN DEFAULT TRUE
            )
        """)

        # Evidence
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT,
                agent_id TEXT,
                task_id INTEGER,
                evidence_type TEXT NOT NULL,
                original_filename TEXT,
                stored_filename TEXT,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                compressed_size INTEGER,
                original_hash TEXT NOT NULL,
                archive_hash TEXT NOT NULL,
                hash_match BOOLEAN DEFAULT TRUE,
                acquisition_time TIMESTAMP,
                metadata_json TEXT,
                status TEXT DEFAULT 'verified',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Chain of custody
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chain_of_custody (
                custody_id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id INTEGER,
                action_type TEXT NOT NULL,
                action_details TEXT,
                actor_id TEXT,
                actor_type TEXT,
                action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hash_before TEXT,
                hash_after TEXT,
                integrity_maintained BOOLEAN
            )
        """)

        # Tasks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT,
                agent_id TEXT,
                task_type TEXT NOT NULL,
                task_status TEXT DEFAULT 'pending',
                command_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                result_json TEXT,
                created_by TEXT
            )
        """)

        # System logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                log_level TEXT,
                log_component TEXT,
                log_message TEXT NOT NULL,
                user_id TEXT,
                agent_id TEXT,
                evidence_id INTEGER,
                case_id TEXT,
                extra_data TEXT
            )
        """)

        # Indexes
        indexes = [
            ("idx_evidence_case", "evidence(case_id)"),
            ("idx_evidence_hash", "evidence(original_hash)"),
            ("idx_custody_evidence", "chain_of_custody(evidence_id)"),
            ("idx_tasks_status", "tasks(task_status)"),
            ("idx_agents_status", "agents(status)"),
            ("idx_cases_id", "cases(case_id)"),
            ("idx_agents_lastseen", "agents(last_seen)")
        ]

        for name, definition in indexes:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {definition}")

        # Default admin
        cursor.execute("SELECT 1 FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                ("admin", "admin123", "admin")
            )

        conn.commit()
        debug_print("Database initialized successfully")

    except Exception as e:
        log_error("Database initialization failed", e)
        raise
    finally:
        close_connection()


def execute_query(query, params=(), fetch_one=False, fetch_all=False, commit=True):
    """Execute SQL query safely"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(query, params)

        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = cursor.lastrowid

        if commit:
            conn.commit()

        return result

    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            import time
            time.sleep(0.1)
            cursor.execute(query, params)
            if commit:
                conn.commit()
            return cursor.fetchone() if fetch_one else cursor.fetchall()
        log_error("Operational DB error", e)
        raise

    except Exception as e:
        log_error("Query execution failed", e)
        raise
