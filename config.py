"""
Configuration for Forensic Acquisition System - SIMPLIFIED
"""

# Server Configuration
CONTROLLER_HOST = '0.0.0.0'
CONTROLLER_PORT = 5000
CONTROLLER_URL = f"http://{CONTROLLER_HOST}:{CONTROLLER_PORT}"
SECRET_KEY = 'forensic-server-secret-2024'

# Database
DATABASE_FILE = 'forensic.db'
EVIDENCE_DIR = 'evidence'

# Agent Configuration
AGENT_TIMEOUT_MINUTES = 5  # Mark agents offline after 5 minutes
HEARTBEAT_INTERVAL = 30    # Agent heartbeat interval (seconds)
AGENT_POLL_INTERVAL = 5    # Agent task polling interval (seconds)
# Agent Configuration - INCREASE TIMES
AGENT_TIMEOUT_MINUTES = 10  # Increased from 5 to 10 minutes
HEARTBEAT_INTERVAL = 60     # Increased from 30 to 60 seconds
AGENT_POLL_INTERVAL = 10    # Increased from 5 to 10 seconds
# Forensic Settings
HASH_ALGORITHM = 'sha256'
CHUNK_SIZE = 1024 * 1024  # 1MB

# Debug mode
DEBUG_MODE = True

def debug_print(message, data=None):
    """Print debug messages if debug mode is enabled"""
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")
        if data:
            print(f"[DEBUG DATA] {data}")

def log_error(error_message, exception=None):
    """Log errors with full traceback"""
    print(f"\n{'='*60}")
    print(f"❌ ERROR: {error_message}")
    if exception:
        print(f"Exception: {exception}")
        import traceback
        traceback.print_exc()
    print(f"{'='*60}\n")
