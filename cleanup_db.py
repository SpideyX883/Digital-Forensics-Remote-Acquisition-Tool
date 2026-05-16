#!/usr/bin/env python3
"""
Clean up database locks and restart system
"""
import os
import time
import sqlite3

def cleanup_database():
    """Clean up database locks and WAL files"""
    db_file = "forensic.db"
    
    if os.path.exists(db_file):
        print(f"🗑️  Removing database: {db_file}")
        os.remove(db_file)
    
    # Remove WAL and SHM files if they exist
    for suffix in ['-wal', '-shm']:
        wal_file = db_file + suffix
        if os.path.exists(wal_file):
            print(f"🗑️  Removing WAL file: {wal_file}")
            os.remove(wal_file)
    
    # Also remove from controller directory if exists
    controller_db = "controller/forensic.db"
    if os.path.exists(controller_db):
        print(f"🗑️  Removing controller database: {controller_db}")
        os.remove(controller_db)
    
    print("✅ Database cleanup complete")

if __name__ == "__main__":
    print("=" * 60)
    print("🔄 DATABASE CLEANUP UTILITY")
    print("=" * 60)
    
    cleanup_database()
    
    print("\n✅ Now you can restart the system:")
    print("1. python3 -m controller.server")
    print("2. python3 -m agent.main --name 'MyAgent'")
    print("=" * 60)
