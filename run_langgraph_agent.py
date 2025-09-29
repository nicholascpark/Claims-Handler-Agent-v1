#!/usr/bin/env python
"""Run the LangGraph Voice Agent.

This is a simple wrapper to run the modular LangGraph implementation.
It provides the same interface as the original but with better architecture.

Usage:
    python run_langgraph_agent.py [--display-json] [--display-interval SECONDS]
"""

import asyncio
import sys

# Ensure the voice_langgraph module can be imported
sys.path.insert(0, '.')

from voice_langgraph import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
