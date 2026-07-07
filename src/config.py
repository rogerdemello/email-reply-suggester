"""Central configuration. Reads from environment / .env (see .env.example)."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass  # dotenv is optional; env vars still work

# --- NVIDIA NIM (OpenAI-compatible endpoint) ---
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

# Generation + judge model (a strong instruct model on NIM).
# Default is llama-3.1-8b-instruct: on NIM's serverless tier it stays warm and
# responds in ~1-2s, so the full pipeline runs reliably end-to-end. Larger models
# (e.g. meta/llama-3.3-70b-instruct) give higher quality but can cold-start for
# minutes on the free tier; point GEN_MODEL/JUDGE_MODEL at one if your tier keeps
# it warm.
GEN_MODEL = os.getenv("GEN_MODEL", "meta/llama-3.1-8b-instruct")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "meta/llama-3.1-8b-instruct")

# Embedding model on NIM (used for the semantic-similarity metric).
# Falls back to TF-IDF automatically if embeddings are unavailable / no key.
EMBED_MODEL = os.getenv("EMBED_MODEL", "nvidia/nv-embedqa-e5-v5")

# Retrieval: how many past emails to show the generator as few-shot examples.
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "3"))

# Sampling
GEN_TEMPERATURE = float(os.getenv("GEN_TEMPERATURE", "0.4"))
JUDGE_TEMPERATURE = float(os.getenv("JUDGE_TEMPERATURE", "0.0"))

# Pass threshold: a response with overall >= this (out of 5) counts as "good".
PASS_THRESHOLD = float(os.getenv("PASS_THRESHOLD", "3.5"))

# Per-request network timeout (seconds) for NIM calls. Generous so NIM serverless
# cold-starts (first hit on a model can take a while to load) don't spuriously fail.
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "120"))


def have_key() -> bool:
    return bool(NVIDIA_API_KEY)
