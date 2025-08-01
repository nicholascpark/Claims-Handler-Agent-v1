#!/usr/bin/env python3
"""
Simple test script to verify Azure OpenAI configuration and connectivity.
This will help diagnose the 404 error and verify your deployment settings.
"""

import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv(override=True)

def test_azure_openai_config():
    """Loads config, connects to Azure OpenAI, and sends a test message."""
    print("=== Azure OpenAI Configuration Test ===")

    # --- FOR DEBUGGING: Hardcode known-good values to isolate the issue ---
    endpoint = "https://maeaioai01.openai.azure.com"
    deployment_name = "gpt-4o-quick"
    api_version = "2025-01-01-preview"

    try:
        # API key is the only value read from the environment for this test
        api_key = os.environ["AZURE_OPENAI_API_KEY"]
    except KeyError as e:
        print(f"❌ ERROR: Missing required environment variable: {e}")
        return False

    print("\n--- Configuration (using hardcoded values) ---")
    print(f"Endpoint: {endpoint}")
    print(f"Deployment: {deployment_name}")
    print(f"API Version: {api_version}")
    print("-----------------------\n")

    try:
        print("Attempting to create AzureChatOpenAI client...")
        llm = AzureChatOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            azure_deployment=deployment_name,
            api_version=api_version
        )
        print("✅ Successfully created AzureChatOpenAI client.")

        # Simple test message
        test_message = [
            ("system", "You are a helpful assistant that translates English to French."),
            ("human", "I love programming."),
        ]
        print("\nSending test message...")
        response = llm.invoke(test_message)

        print(f"\n✅ SUCCESS: Model responded.")
        print(f"Response: {response.content}")
        return True

    except Exception as e:
        print(f"❌ ERROR: An exception occurred during the API call.")
        print(f"   Details: {str(e)}")
        return False

if __name__ == "__main__":
    test_azure_openai_config()
