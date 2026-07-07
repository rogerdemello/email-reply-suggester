"""
Retrieval over the past-email pool.

The generator is grounded via *retrieval-augmented few-shot*: for a new incoming
email we fetch the k most similar past (email -> reply) pairs and show them to the
LLM as worked examples. This teaches tone, structure, and domain facts (proration,
SSO steps, refund windows) without fine-tuning.

Default similarity is TF-IDF cosine (pure-Python, see src/textsim.py):
deterministic, offline, no API key, no heavy dependencies, and plenty strong for
short support emails. This keeps retrieval reproducible and free while the LLM does
the heavy lifting on generation.
"""
import json
import os
from typing import List, Tuple

from .textsim import TfidfIndex

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def load_pool(path: str = None) -> List[dict]:
    path = path or os.path.join(DATA_DIR, "emails.jsonl")
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


class Retriever:
    def __init__(self, pool: List[dict] = None):
        self.pool = pool if pool is not None else load_pool()
        # Index on subject + email body (what the incoming email will look like).
        self._docs = [f"{r['subject']}\n{r['email']}" for r in self.pool]
        self._index = TfidfIndex(self._docs)

    def retrieve(self, subject: str, email: str, k: int = 3) -> List[Tuple[dict, float]]:
        hits = self._index.query(f"{subject}\n{email}", k=k)
        return [(self.pool[i], float(score)) for i, score in hits]
