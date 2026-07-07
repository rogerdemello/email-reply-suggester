"""
Thin client over NVIDIA NIM's OpenAI-compatible API.

NIM exposes chat + embeddings at https://integrate.api.nvidia.com/v1 and speaks
the OpenAI wire format, so we use the `openai` SDK pointed at that base URL.

If USE_MOCK=1 (env), a deterministic local backend is used instead so the whole
pipeline runs end-to-end with no key and no network. The mock is a heuristic
stand-in for smoke-testing the plumbing -- it is NOT representative of real model
quality. See src/mock_backend.py.
"""
import json
import os
from typing import List, Optional

from . import config

_client = None
USE_MOCK = os.getenv("USE_MOCK", "0").strip() in ("1", "true", "True")


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        if not config.have_key():
            raise RuntimeError(
                "NVIDIA_API_KEY is not set. Add it to .env (see .env.example) "
                "to run live, or use the cached/offline path (run.py --offline)."
            )
        _client = OpenAI(api_key=config.NVIDIA_API_KEY, base_url=config.NVIDIA_BASE_URL)
    return _client


def chat(messages: List[dict], model: str, temperature: float = 0.3,
         max_tokens: int = 900) -> str:
    """One chat completion -> assistant text."""
    if USE_MOCK:
        from . import mock_backend
        return mock_backend.chat(messages)
    resp = _get_client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


def chat_json(messages: List[dict], model: str, temperature: float = 0.0,
              max_tokens: int = 900) -> dict:
    """Chat completion that must return JSON. Robust to code-fenced output."""
    raw = chat(messages, model=model, temperature=temperature, max_tokens=max_tokens)
    return _parse_json(raw)


def _parse_json(raw: str) -> dict:
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        # drop a leading language tag like "json\n"
        nl = s.find("\n")
        if nl != -1:
            s = s[nl + 1:]
    # grab the outermost {...} if there's surrounding prose
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1:
        s = s[start:end + 1]
    return json.loads(s)


def embed(texts: List[str], input_type: str = "query") -> Optional[List[List[float]]]:
    """
    Embed texts with NIM. Returns None if embeddings are unavailable so callers
    can fall back to TF-IDF. `input_type` is 'query' or 'passage' (NIM requires it).
    """
    if USE_MOCK:
        return None  # force TF-IDF fallback in the evaluator
    try:
        resp = _get_client().embeddings.create(
            model=config.EMBED_MODEL,
            input=texts,
            extra_body={"input_type": input_type, "truncate": "END"},
        )
        return [d.embedding for d in resp.data]
    except Exception:
        return None
