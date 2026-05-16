"""
System info and utilities
"""
import platform
import os
import socket
import uuid
from datetime import datetime

class SystemInfo:
    @staticmethod
    def get_hostname():
        """Get system hostname"""
        try:
            return platform.node() or socket.gethostname() or "Unknown"
        except:
            return "Unknown"
    
    @staticmethod
    def get_os_info():
        """Get OS information"""
        try:
            return f"{platform.system()} {platform.release()} {platform.machine()}"
        except:
            return "Unknown OS"
    
    @staticmethod
    def generate_agent_id(agent_name=None):
        """Generate unique agent ID"""
        try:
            hostname = SystemInfo.get_hostname()
            pid = os.getpid()
            timestamp = datetime.now().strftime("%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            
            if agent_name:
                return f"{agent_name}_{pid}_{timestamp}_{unique_id}"
            else:
                return f"{hostname}_{pid}_{timestamp}_{unique_id}"
                
        except Exception as e:
            # Fallback to simple ID
            return f"agent_{os.getpid()}_{int(datetime.now().timestamp())}"
    
    @staticmethod
    def get_ip_address():
        """Get local IP address"""
        try:
            # Create a socket to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()
            return ip_address
        except:
            return "127.0.0.1"
    
    @staticmethod
    def get_system_info():
        """Get comprehensive system information"""
        info = {
            'hostname': SystemInfo.get_hostname(),
            'os': SystemInfo.get_os_info(),
            'python_version': platform.python_version(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor(),
            'ip_address': SystemInfo.get_ip_address(),
            'timestamp': datetime.now().isoformat()
        }
        return info