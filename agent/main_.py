import sys
import os
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import debug_print, log_error, CONTROLLER_URL, HEARTBEAT_INTERVAL
from agent.agent_core import ForensicAgent

def main():
    """Start the forensic agent"""
    parser = argparse.ArgumentParser(description='Forensic Acquisition Agent')
    parser.add_argument('--controller', default=CONTROLLER_URL, 
                       help=f'Controller URL (default: {CONTROLLER_URL})')
    parser.add_argument('--name', help='Agent name (default: hostname)')
    parser.add_argument('--heartbeat', type=int, default=HEARTBEAT_INTERVAL,
                       help=f'Heartbeat interval in seconds (default: {HEARTBEAT_INTERVAL})')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🤖 FORENSIC ACQUISITION AGENT")
    print("=" * 60)
    
    try:
        agent = ForensicAgent(
            controller_url=args.controller,
            agent_name=args.name,
            heartbeat_interval=args.heartbeat,
            debug_mode=args.debug
        )
        
        if agent.register():
            print("\n" + "=" * 60)
            print("✅ AGENT STARTED SUCCESSFULLY")
            print("=" * 60)
            print(f"Agent ID: {agent.agent_id}")
            print(f"Controller: {args.controller}")
            print(f"Heartbeat: Every {args.heartbeat} seconds")
            print("=" * 60)
            print("\nPress Ctrl+C to stop the agent\n")
            
            agent.run()
        else:
            print("\n❌ Failed to register with controller. Exiting.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n👋 Agent stopped by user")
        sys.exit(0)
    except Exception as e:
        log_error("Fatal agent error", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
