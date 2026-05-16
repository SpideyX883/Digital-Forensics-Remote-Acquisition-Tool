"""
System logging and chain of custody utilities
"""
import json
from datetime import datetime
from config import DATABASE_FILE, debug_print, log_error

def log_system_event(level, component, message, extra_data=None):
    """Log system event to database"""
    try:
        import sqlite3
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO system_logs (log_level, log_component, log_message, extra_data)
            VALUES (?, ?, ?, ?)
        """, (level, component, message, json.dumps(extra_data) if extra_data else '{}'))
        
        conn.commit()
        conn.close()
        
        debug_print(f"[{level}] {component}: {message}")
        if extra_data:
            debug_print(f"Extra data: {extra_data}")
            
    except Exception as e:
        print(f"[LOG ERROR] Failed to log event: {e}")
        print(f"Level: {level}, Component: {component}, Message: {message}")

def log_chain_of_custody(evidence_id, action, actor_id, actor_type='system', 
                        hash_before=None, hash_after=None):
    """Log chain of custody event"""
    try:
        import sqlite3
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        integrity = (hash_before == hash_after) if hash_before and hash_after else True
        
        cursor.execute("""
            INSERT INTO chain_of_custody 
            (evidence_id, action_type, action_details, actor_id, actor_type, 
             hash_before, hash_after, integrity_maintained)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (evidence_id, action, f"Action: {action}", actor_id, actor_type,
              hash_before, hash_after, integrity))
        
        conn.commit()
        conn.close()
        
        debug_print(f"Chain of custody: Evidence {evidence_id}, Action: {action}, Actor: {actor_id}")
        
    except Exception as e:
        print(f"[CUSTODY LOG ERROR] {e}")