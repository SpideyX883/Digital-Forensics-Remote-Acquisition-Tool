"""
Heartbeat management
"""
import threading
import time
from config import debug_print, log_error

class HeartbeatManager:
    def __init__(self, client, heartbeat_interval=30, debug_mode=False):
        self.client = client
        self.heartbeat_interval = heartbeat_interval
        self.debug_mode = debug_mode
        self.running = False
        self.thread = None
        self.agent_id = None
    
    def start(self, agent_id):
        """Start heartbeat thread"""
        try:
            self.agent_id = agent_id
            self.running = True
            
            self.thread = threading.Thread(
                target=self._heartbeat_loop,
                daemon=True,
                name="HeartbeatThread"
            )
            self.thread.start()
            
            debug_print(f"✅ Heartbeat started (every {self.heartbeat_interval}s)")
            return True
            
        except Exception as e:
            log_error("Failed to start heartbeat", e)
            return False
    
    def stop(self):
        """Stop heartbeat thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        debug_print("Heartbeat stopped")
    
    def _heartbeat_loop(self):
        """Heartbeat loop"""
        heartbeat_count = 0
        
        while self.running:
            try:
                heartbeat_count += 1
                
                if self.agent_id:
                    success = self.client.send_heartbeat(self.agent_id)
                    
                    if success:
                        debug_print(f"Heartbeat #{heartbeat_count}: ✅ Success")
                    else:
                        debug_print(f"Heartbeat #{heartbeat_count}: ❌ Failed")
                
                # Wait for next heartbeat
                for _ in range(self.heartbeat_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                debug_print(f"Heartbeat error: {e}")
                time.sleep(self.heartbeat_interval)