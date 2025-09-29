#!/usr/bin/env python3
"""
Run Voice Agent - Main entry point for Claims Handler Voice Interface

This script starts the voice agent using the OpenAI Realtime Agents supervisor pattern.
"""

import asyncio
import sys
import os
import argparse

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.voice_agent import main
from src.config.settings import settings

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Claims Handler Voice Agent")
    parser.add_argument(
        "--disable-ssl-verify", 
        action="store_true", 
        help="Disable SSL certificate verification (for corporate environments)"
    )
    parser.add_argument(
        "--display-json",
        action="store_true",
        help="Display updated claim JSON after each field update"
    )
    return parser.parse_args()

if __name__ == "__main__":
    # Parse arguments
    args = parse_args()
    
    print("🎤 Starting Claims Handler Voice Agent...")
    print("📋 Using Junior/Supervisor Pattern from OpenAI Realtime Agents")
    print("🔧 You will be prompted to select your microphone device")
    print("💡 Tip: If you experience false starts, increase MIN_SPEECH_MS (e.g., 500)")
    
    # Handle SSL configuration
    if args.disable_ssl_verify:
        os.environ["OPENAI_DISABLE_SSL_VERIFY"] = "true"
        print("⚠️  SSL verification disabled for corporate environment")
    elif os.getenv("OPENAI_DISABLE_SSL_VERIFY", "").lower() == "true":
        print("⚠️  SSL verification disabled for corporate environment")
    else:
        print("💡 If you get SSL certificate errors, use: --disable-ssl-verify")
    
    # Enable JSON payload display for field updates
    if args.display_json:
        try:
            # Prefer settings flag over environment variables
            settings.DISPLAY_CLAIM_JSON = True
        except Exception:
            # Fallback env for any modules that may read it early
            os.environ["DISPLAY_CLAIM_JSON"] = "true"
        print("🧾 JSON payload display enabled (fetches latest status from background thread)")

    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Voice agent stopped by user")
    except Exception as e:
        print(f"❌ Error starting voice agent: {e}")
        sys.exit(1)

