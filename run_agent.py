#!/usr/bin/env python3
"""
Simple agent runner - Run this from project root
"""
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import and run agent
from agent.main_ import main

if __name__ == "__main__":
    main()
