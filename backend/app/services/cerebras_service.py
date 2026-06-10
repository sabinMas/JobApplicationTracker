"""
Cerebras provider (OpenAI-compatible endpoint) — fallback AI provider.

High-level AI functions live in `ai_service`; this module only exposes the
low-level chat call used by the provider router there.
"""
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

_client = None
MODEL = os.getenv("CEREBRAS_MODEL", "llama-3.3-70b")


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("CEREBRAS_API_KEY", "")
        if not api_key:
            raise RuntimeError("CEREBRAS_API_KEY not set")
        _client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.cerebras.ai/v1",
        )
    return _client


async def _chat(system: str, user: str, temperature: float = 0.3) -> str:
    resp = await _get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()
