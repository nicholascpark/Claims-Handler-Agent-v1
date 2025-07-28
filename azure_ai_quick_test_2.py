#!/usr/bin/env python3
"""
Quick test script for Azure OpenAI using the openai library.
"""
from openai import AzureOpenAI
from dotenv import load_dotenv
import os

def main() -> None:
    """Loads configuration, sends a request to Azure OpenAI, and prints the response."""
    # Load environment variables from .env file
    load_dotenv(override=True)

    # --- FOR DEBUGGING: Hardcoded values from the working curl command ---
    # This test removes environment variables as a source of error.
    azure_endpoint = "https://maeaioai01.openai.azure.com"
    deployment_name = "gpt-4o-quick"
    api_version = "2025-01-01-preview"  # Using the exact version from your successful curl

    try:
        api_key = os.environ["AZURE_OPENAI_API_KEY"]
    except KeyError as e:
        raise SystemExit(f"Error: Missing required environment variable {e}") from e

    print("--- Configuration (using hardcoded values) ---")
    print(f"Endpoint: {azure_endpoint}")
    print(f"Deployment: {deployment_name}")
    print(f"API Version: {api_version}")
    print("-----------------------\n")

    client = AzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=api_key,
        api_version=api_version,
    )

    # Use the message text from the working curl command
    message_text = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Does Azure OpenAI support customer managed keys?"},
        {"role": "assistant", "content": "Yes, customer managed keys are supported by Azure OpenAI."},
        {"role": "user", "content": "Do other Azure services support this too?"},
    ]

    print("--- Sending Request ---")
    completion = client.chat.completions.create(
        model=deployment_name,
        messages=message_text,
        temperature=0.1,
        max_tokens=100,
    )

    print("\n--- Response ---")
    print(completion.choices[0].message.content)


if __name__ == "__main__":
    main()
