#!/usr/bin/env python3
"""
Quick test to verify Cerebras API key works.
Run: python test_api_key.py
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

async def test_api():
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        print("❌ ERROR: CEREBRAS_API_KEY not found in .env")
        sys.exit(1)

    print(f"✓ API Key loaded: {api_key[:20]}...")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.cerebras.ai/v1",
    )

    print("Testing Cerebras API with simple prompt...")
    try:
        resp = await client.chat.completions.create(
            model="gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, API works!' and nothing else."},
            ],
            temperature=0.3,
        )
        result = resp.choices[0].message.content.strip()
        print(f"✓ API Response: {result}")
        print("✓✓✓ API Key is VALID and working!")
    except Exception as e:
        print(f"❌ API Error: {type(e).__name__}: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_api())
