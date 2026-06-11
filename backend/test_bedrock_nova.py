#!/usr/bin/env python3
"""
Test script to verify Bedrock Amazon Nova models are working.
Run this to diagnose any Bedrock configuration issues.

Usage:
    python test_bedrock_nova.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_bedrock_connection():
    """Test basic Bedrock connection and Nova model availability."""
    print("\n" + "="*60)
    print("BEDROCK + AMAZON NOVA DIAGNOSTIC TEST")
    print("="*60 + "\n")

    try:
        import aioboto3
        import logging
        logging.basicConfig(level=logging.DEBUG)
        print("✓ aioboto3 imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import aioboto3: {e}")
        print("  Install with: pip install aioboto3")
        return False

    # Test 1: Check environment
    print("\n[1/4] Checking AWS configuration...")
    import os
    region = os.getenv("AWS_REGION", "us-east-1")
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    if access_key and secret_key:
        print(f"  ✓ AWS credentials found (region: {region})")
    else:
        print(f"  ✗ AWS credentials missing")
        print("    Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        return False

    # Test 2: Test Bedrock connection with Nova Lite (simple text)
    print("\n[2/4] Testing Bedrock Converse API with Nova Lite...")
    session = aioboto3.Session()
    try:
        async with session.client("bedrock-runtime", region_name=region) as client:
            response = await client.converse(
                modelId="amazon.nova-lite-v1:0",
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": "Say 'Nova works!' and nothing else."}],
                    }
                ],
                inferenceConfig={"temperature": 0.1, "maxTokens": 100},
            )
            text = "".join(
                block.get("text", "") for block in response["output"]["message"]["content"]
            ).strip()
            print(f"  ✓ Nova Lite responded: {text}")
    except Exception as e:
        print(f"  ✗ Nova Lite failed: {type(e).__name__}: {str(e)[:150]}")
        return False

    # Test 3: Test structured output (tool-use) with Nova Lite
    print("\n[3/4] Testing structured output (tool-use) with Nova Lite...")
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
        "required": ["name"],
    }
    try:
        async with session.client("bedrock-runtime", region_name=region) as client:
            response = await client.converse(
                modelId="amazon.nova-lite-v1:0",
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": "Extract: person named Alice, age 30"}],
                    }
                ],
                inferenceConfig={"temperature": 0.1, "maxTokens": 200},
                toolConfig={
                    "tools": [
                        {
                            "toolSpec": {
                                "name": "person_extractor",
                                "description": "Extract person data",
                                "inputSchema": {"json": schema},
                            }
                        }
                    ],
                    "toolChoice": {"tool": {"name": "person_extractor"}},
                },
            )
            for block in response["output"]["message"]["content"]:
                if "toolUse" in block:
                    data = block["toolUse"]["input"]
                    print(f"  ✓ Structured output succeeded: {data}")
                    break
            else:
                print("  ✗ No toolUse block in response")
                return False
    except Exception as e:
        print(f"  ✗ Structured output failed: {type(e).__name__}: {str(e)[:150]}")
        return False

    # Test 4: Test Nova Pro (if available)
    print("\n[4/4] Testing Nova Pro (higher quality)...")
    try:
        async with session.client("bedrock-runtime", region_name=region) as client:
            response = await client.converse(
                modelId="amazon.nova-pro-v1:0",
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": "Write a haiku about code."}],
                    }
                ],
                inferenceConfig={"temperature": 0.3, "maxTokens": 100},
            )
            text = "".join(
                block.get("text", "") for block in response["output"]["message"]["content"]
            ).strip()
            print(f"  ✓ Nova Pro responded:\n     {text}")
    except Exception as e:
        print(f"  ✗ Nova Pro failed: {type(e).__name__}: {str(e)[:150]}")
        print("    Note: Nova Pro may not be available in all regions yet")
        return False

    print("\n" + "="*60)
    print("ALL TESTS PASSED ✓")
    print("="*60)
    print("\nYour Bedrock setup is ready for production!")
    print("Resume extraction will now work with Amazon Nova models.")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_bedrock_connection())
    sys.exit(0 if success else 1)
