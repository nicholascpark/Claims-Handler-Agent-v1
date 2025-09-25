#!/usr/bin/env python3
"""
Convenient test runner for Claims Handler Agent v1

This script provides an easy way to run the conversation tester
without import path issues.

Usage:
    python run_test.py
"""

import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import and run the test script
if __name__ == "__main__":
    try:
        from src.test_conversation import main
        import asyncio
        
        print("🚀 Starting Claims Handler Agent v1 Test Suite...")
        print(f"📁 Project root: {project_root}")
        print("=" * 50)
        
        asyncio.run(main())
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\n🔧 Try installing dependencies:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test Error: {e}")
        sys.exit(1)
