#!/usr/bin/env python3
"""
Quick sanity-check script for your Azure OpenAI deployment.

Usage:
    python azure_ai_quick_test.py [prompt]

If no prompt is provided, the default "Tell me a joke" will be used.

Required environment variables (place them in a .env file or export them):
    AZURE_OPENAI_API_KEY        Your Azure OpenAI key
    AZURE_OPENAI_ENDPOINT       Your resource endpoint, e.g. https://<resource>.openai.azure.com/

Optional environment variables:
    AZURE_OPENAI_DEPLOYMENT_NAME   Name of your model deployment (default: gpt-4o)
    AZURE_OPENAI_API_VERSION       API version to use (default: 2024-08-01-preview)
"""

import os
import sys
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI


def main() -> None:
    """Load environment, send a single prompt, and print the response."""

    # Load variables from .env if present
    load_dotenv(override=True)

    # --- FOR DEBUGGING: Hardcode known-good values to isolate the issue ---
    endpoint = "https://maeaioai01.openai.azure.com"
    deployment_name = "gpt-4o-quick"
    api_version = "2025-01-01-preview"

    try:
        # API key is the only value read from the environment for this test
        api_key = os.environ["AZURE_OPENAI_API_KEY"]
    except KeyError as missing:
        raise SystemExit(f"Missing required environment variable: {missing}") from None

    # Get prompt from command-line arguments or use a default
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Tell me a joke"

    print("--- LangChain Configuration (using hardcoded values) ---")
    print(f"Endpoint: {endpoint}")
    print(f"Deployment: {deployment_name}")
    print(f"API Version: {api_version}")
    print(f"Prompt: '{prompt}'")
    print("-----------------------------\n")

    # Instantiate the chat model wrapper
    llm = AzureChatOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        azure_deployment=deployment_name,
        api_version=api_version,
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )

    # Invoke the model and display the result
    print("--- Sending Request ---")
    response = llm.invoke(prompt)
    print("\n--- Assistant ---")
    print(response.content)


if __name__ == "__main__":
    main() 