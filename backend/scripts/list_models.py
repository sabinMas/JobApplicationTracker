#!/usr/bin/env python3
"""
List available Cerebras models.
"""
import asyncio
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

async def list_models():
    api_key = os.getenv("CEREBRAS_API_KEY")
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.cerebras.ai/v1",
    )

    print("Fetching available models from Cerebras...")
    try:
        models = await client.models.list()
        print("\n✓ Available models:")
        for model in models.data:
            print(f"  - {model.id}")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    asyncio.run(list_models())
