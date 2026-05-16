import os
import sys
from flask import Flask
from config import CONTROLLER_HOST, CONTROLLER_PORT, EVIDENCE_DIR, debug_print, log_error

class ForensicController:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'forensic-server-secret-2024'
        
    def setup(self):
        """Setup all controller components"""
        try:
            debug_print("Starting controller setup...")
            
            # Import components - use absolute imports now that path is set
            from controller.database import init_database
            from controller.api_handlers import register_api_endpoints
            from controller.web_ui import register_web_routes
            from controller.health_monitor import start_health_monitor
            
            # Initialize database
            debug_print("Initializing database...")
            init_database()
            
            # Create evidence directory
            os.makedirs(EVIDENCE_DIR, exist_ok=True)
            debug_print(f"Evidence directory created/verified: {EVIDENCE_DIR}")
            
            # Register routes
            debug_print("Registering web routes...")
            register_web_routes(self.app)
            
            debug_print("Registering API endpoints...")
            register_api_endpoints(self.app)
            
            # Start health monitor
            debug_print("Starting health monitor...")
            start_health_monitor()
            
            debug_print("✅ Controller setup complete")
            return True
            
        except Exception as e:
            log_error("Controller setup failed", e)
            return False
        
    def run(self):
        """Run the controller server"""
        if not self.setup():
            print("❌ Failed to setup controller. Exiting.")
            sys.exit(1)
        
        print("=" * 60)
        print("🔬 FORENSIC ACQUISITION CONTROLLER")
        print("=" * 60)
        print(f"🌐 Web Interface: http://{CONTROLLER_HOST}:{CONTROLLER_PORT}")
        print(f"🔐 Default Login: admin / admin123")
        print(f"📁 Evidence Directory: {EVIDENCE_DIR}")
        print("=" * 60)
        
        try:
            self.app.run(
                debug=True, 
                host=CONTROLLER_HOST, 
                port=CONTROLLER_PORT
            )
        except Exception as e:
            log_error("Server runtime error", e)

def main():
    """Main entry point"""
    controller = ForensicController()
    controller.run()

if __name__ == "__main__":
    main()
