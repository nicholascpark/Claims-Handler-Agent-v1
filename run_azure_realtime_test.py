"""Minimal Azure OpenAI Realtime connectivity test.

Reads Azure settings from src/config/settings.py (.env) and attempts to
open a WebSocket connection to the Azure Realtime endpoint.

Usage:
  python run_azure_realtime_test.py
"""

import asyncio
import os
import ssl
import sys
import traceback

try:
    import websockets
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install websockets")
    sys.exit(1)

from src.config.settings import settings, validate_required_settings


def build_ws_url() -> str:
    endpoint = (settings.AZURE_OPENAI_ENDPOINT or "").rstrip('/')
    api_version = settings.AZURE_OPENAI_REALTIME_API_VERSION
    deployment = settings.AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME
    base_https = f"{endpoint}/openai/realtime?api-version={api_version}&deployment={deployment}"
    # Convert to ws(s)
    return base_https.replace("https://", "wss://").replace("http://", "ws://")


async def try_connect(headers, subprotocols=None):
    ws_url = build_ws_url()

    # Optional SSL relaxation for corp envs
    ssl_context = None
    if os.getenv("OPENAI_DISABLE_SSL_VERIFY", "").lower() == "true":
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    print("Connecting to:")
    print(f"  URL: {ws_url}")
    print(f"  Endpoint: {settings.AZURE_OPENAI_ENDPOINT}")
    print(f"  Deployment: {settings.AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME}")
    print(f"  API Version: {settings.AZURE_OPENAI_REALTIME_API_VERSION}")

    async with websockets.connect(
        ws_url,
        additional_headers=headers,
        subprotocols=subprotocols,
        ssl=ssl_context,
        ping_interval=20,
        ping_timeout=10,
        close_timeout=5,
        max_size=10_000_000,
    ) as ws:
        print("✅ Connected successfully.")
        # Optionally send a no-op style event to validate basic messaging
        # Many servers accept a session.update, but it's optional for connectivity
        # Here we simply close immediately.
        await ws.close()


async def main():
    try:
        validate_required_settings()
    except Exception as e:
        print(f"❌ Settings validation failed: {e}")
        sys.exit(1)

    # Primary attempt: Azure uses 'api-key' header
    primary_headers = [("api-key", settings.AZURE_OPENAI_API_KEY or "")]

    # Fallback attempts
    fallback_headers = primary_headers + [("OpenAI-Beta", "realtime=v1")]

    print("Attempt 1: Using Azure 'api-key' header only...")
    try:
        await try_connect(primary_headers)
        print("🎉 Realtime connectivity OK (primary headers).")
        return
    except Exception as e:
        print(f"Attempt 1 failed: {e}")
        if os.getenv("DEBUG", "").lower() == "true":
            traceback.print_exc()

    print("\nAttempt 2: Retrying with 'api-key' + 'OpenAI-Beta: realtime=v1' header and 'realtime' subprotocol...")
    try:
        await try_connect(fallback_headers, subprotocols=["realtime"])
        print("🎉 Realtime connectivity OK (fallback headers + subprotocol).")
        return
    except Exception as e:
        print(f"Attempt 2 failed: {e}")
        if os.getenv("DEBUG", "").lower() == "true":
            traceback.print_exc()

    print("\nAttempt 3: Retrying with 'openai-realtime-v1' subprotocol...")
    try:
        await try_connect(primary_headers, subprotocols=["openai-realtime-v1"]) 
        print("🎉 Realtime connectivity OK (openai-realtime-v1 subprotocol).")
        return
    except Exception as e:
        print(f"Attempt 3 failed: {e}")
        if os.getenv("DEBUG", "").lower() == "true":
            traceback.print_exc()

    print("\n❌ Realtime connectivity test failed. Common checks:")
    print("- Verify AZURE_OPENAI_ENDPOINT (e.g., https://<resource>.openai.azure.com)")
    print("- Verify AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME exists and is a Realtime-capable model")
    print("- Verify AZURE_OPENAI_REALTIME_API_VERSION matches the service (e.g., 2024-10-01-preview)")
    print("  Note: 404 often indicates the version is not supported by your resource or the deployment name is wrong.")
    print("- Ensure the API key has access and is not restricted by networking (firewall/VNet)")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted by user")

