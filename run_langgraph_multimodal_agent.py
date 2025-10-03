#!/usr/bin/env python
"""Run the LangGraph Multimodal Agent (Audio + Text + Image via CLI).

This runner enables:
- Audio input via microphone (server VAD)
- Typed text input (press Enter)
- Image attachments (CLI flag and interactive /attach command)

Usage examples:
  python run_langgraph_multimodal_agent.py --text --audio --display-json
  python run_langgraph_multimodal_agent.py --text --no-audio --attach ./photo.jpg image/jpeg

While running:
- Type a message and press Enter to send text.
- Use: /attach <path> [mime] to add an image to the next message.
"""

import asyncio
import sys
import os
import argparse

# Ensure the voice_langgraph module can be imported
sys.path.insert(0, '.')

from voice_langgraph import VoiceAgent
from voice_langgraph.settings import voice_settings
from voice_langgraph.settings import validate_voice_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LangGraph Multimodal Agent (CLI)")
    parser.add_argument("--audio", dest="audio", action="store_true", help="Enable microphone audio input")
    parser.add_argument("--no-audio", dest="audio", action="store_false", help="Disable microphone audio input")
    parser.set_defaults(audio=True)

    parser.add_argument("--text", dest="text", action="store_true", help="Enable typed text input")
    parser.add_argument("--no-text", dest="text", action="store_false", help="Disable typed text input")
    parser.set_defaults(text=True)

    parser.add_argument("--images", dest="images", action="store_true", help="Enable image attachments")
    parser.add_argument("--no-images", dest="images", action="store_false", help="Disable image attachments")
    parser.set_defaults(images=True)

    parser.add_argument("--display-json", action="store_true", help="Display claim JSON updates periodically")
    parser.add_argument("--display-interval", type=float, default=1.0, help="Seconds between JSON display updates")

    parser.add_argument("--attach", nargs="+", metavar=("PATH", "MIME"), help="Pre-attach an image before start: PATH [MIME]")

    return parser.parse_args()


async def main():
    args = parse_args()

    # Apply modality flags to settings
    try:
        voice_settings.ENABLE_AUDIO_INPUT = bool(args.audio)
        voice_settings.ENABLE_TEXT_INPUT = bool(args.text)
        voice_settings.ENABLE_IMAGE_INPUT = bool(args.images)
    except Exception:
        # If settings object is frozen, rely on defaults and warn
        print("⚠️ Could not update modality flags on settings; using defaults.")

    # Validate required environment
    validate_voice_settings()

    # Create agent
    agent = VoiceAgent(
        display_json=args.display_json,
        display_interval=args.display_interval,
    )

    # Pre-attach image if provided
    if args.attach:
        if len(args.attach) >= 1:
            path = args.attach[0]
            mime = args.attach[1] if len(args.attach) > 1 else None
            if not voice_settings.ENABLE_IMAGE_INPUT:
                print("⚠️ Image attachments are disabled; enable with --images")
            else:
                ok_msg = await agent.attach_image_from_path(path, mime)
                prefix = "✅" if ok_msg[0] else "❌"
                print(f"{prefix} {ok_msg[1]}")

    print("🎛️ Modalities: audio=%s, text=%s, images=%s" % (
        "on" if voice_settings.ENABLE_AUDIO_INPUT else "off",
        "on" if voice_settings.ENABLE_TEXT_INPUT else "off",
        "on" if voice_settings.ENABLE_IMAGE_INPUT else "off",
    ))
    print("⌨️  Type messages and press Enter. Use /attach <path> [mime] to add an image.")

    try:
        await agent.start()
    except KeyboardInterrupt:
        print("\n👋 Stopped by user")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


