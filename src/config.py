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
GEN_MODEL = os.getenv("GEN_MODEL", "meta/llama-3.3-70b-instruct")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "meta/llama-3.3-70b-instruct")

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


def have_key() -> bool:
    return bool(NVIDIA_API_KEY)
