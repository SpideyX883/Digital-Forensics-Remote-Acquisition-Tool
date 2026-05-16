"""
Agent health monitoring - FIXED for concurrency
"""
import threading
import time
from datetime import datetime, timedelta
from config import AGENT_TIMEOUT_MINUTES, debug_print, log_error


def cleanup_offline_agents():
    """Mark agents as offline if they haven't checked in recently"""
    while True:
        try:
            from controller.database import execute_query
            from controller.logging_utils import log_system_event

            threshold = datetime.now() - timedelta(minutes=AGENT_TIMEOUT_MINUTES)
            threshold_str = threshold.strftime('%Y-%m-%d %H:%M:%S')

            execute_query("""
                UPDATE agents
                SET status = 'offline'
                WHERE status = 'online'
                AND (last_seen < ? OR last_seen IS NULL)
            """, (threshold_str,), commit=True)

            log_system_event(
                "INFO",
                "agent_health",
                "Health monitor ran successfully"
            )

        except Exception as e:
            log_error("Health monitor error", e)

        # Reduced DB load
        time.sleep(120)


def start_health_monitor():
    """Start the health monitor in background thread"""
    try:
        for thread in threading.enumerate():
            if thread.name == "HealthMonitor":
                debug_print("Health monitor already running")
                return True

        t = threading.Thread(
            target=cleanup_offline_agents,
            daemon=True,
            name="HealthMonitor"
        )
        t.start()

        debug_print("✅ Health monitor started (runs every 2 minutes)")
        return True

    except Exception as e:
        log_error("Failed to start health monitor", e)
        return False
