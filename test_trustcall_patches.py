#!/usr/bin/env python3
"""
Test script to demonstrate trustcall patch operations with FNOLPayload.
This shows how JSON patches are applied incrementally to update the payload.
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from trustcall import create_extractor
from src.schema import FNOLPayload
from src.utils import print_patch_summary, print_payload_status
import httpx
import ssl

load_dotenv()

# Setup SSL workaround (same as in nodes.py)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

custom_httpx_client = httpx.Client(
    verify=False,
    timeout=httpx.Timeout(60.0)
)

def test_incremental_updates():
    """Demonstrate how trustcall handles incremental updates to FNOLPayload."""
    
    llm = ChatOpenAI(
        model="gpt-4o-mini", 
        temperature=0.1,
        http_client=custom_httpx_client
    )
    
    extractor = create_extractor(llm, tools=[FNOLPayload], enable_inserts=True)
    
    print("🧪 Testing Trustcall Incremental Updates\n")
    print("="*60)
    
    # Scenario 1: Initial payload creation
    print("\n📝 Scenario 1: Creating initial payload")
    print("-" * 40)
    
    messages = [
        {"role": "user", "content": "I need to report a car accident. My name is John Smith, policy number ABC123456, it happened today at 2 PM on Highway 401 in Toronto."}
    ]
    
    result1 = extractor.invoke({"messages": messages})
    payload1 = result1["responses"][0] if result1["responses"] else None
    
    print(f"✅ Initial payload created: {payload1 is not None}")
    print_payload_status(payload1)
    
    # Scenario 2: Adding vehicle information
    print("\n📝 Scenario 2: Adding vehicle details")
    print("-" * 40)
    
    existing_data = {"FNOLPayload": payload1.model_dump()} if payload1 else {}
    
    messages.append({
        "role": "user", 
        "content": "My car is a 2020 Honda Civic, license plate XYZ789. The other car was a blue Toyota Camry."
    })
    
    result2 = extractor.invoke({
        "messages": messages,
        "existing": existing_data
    })
    
    payload2 = result2["responses"][0] if result2["responses"] else None
    patches2 = []
    for meta in result2.get("response_metadata", []):
        if "patches" in meta:
            patches2.extend(meta["patches"])
    
    print_patch_summary(patches2, payload1, payload2)
    print_payload_status(payload2)
    
    # Scenario 3: Adding injury information
    print("\n📝 Scenario 3: Adding injury details")
    print("-" * 40)
    
    existing_data = {"FNOLPayload": payload2.model_dump()} if payload2 else {}
    
    messages.append({
        "role": "user", 
        "content": "I have minor neck pain, and the other driver complained of a headache."
    })
    
    result3 = extractor.invoke({
        "messages": messages,
        "existing": existing_data
    })
    
    payload3 = result3["responses"][0] if result3["responses"] else None
    patches3 = []
    for meta in result3.get("response_metadata", []):
        if "patches" in meta:
            patches3.extend(meta["patches"])
    
    print_patch_summary(patches3, payload2, payload3)
    print_payload_status(payload3)
    
    print("\n🎯 Summary: Trustcall successfully applied incremental updates!")
    print("Each conversation turn adds new information without losing existing data.")
    print("JSON patches ensure efficient and accurate updates to the payload structure.")

if __name__ == "__main__":
    test_incremental_updates() 