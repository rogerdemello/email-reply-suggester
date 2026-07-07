"""
Tiny, dependency-free text similarity (TF-IDF + cosine).

Replaces scikit-learn for this project so the serverless deployment stays small and
cold-starts fast. Over a pool of ~30 short support emails this is more than accurate
enough for retrieval and for the evaluator's offline similarity fallback.
"""
import math
import re
from collections import Counter
from typing import List

_TOKEN = re.compile(r"[a-z0-9']+")
_STOP = set(
    "a an the and or but to of for in on at is are was were be been being with your "
    "you we our i it this that will can could would should have has had get got as if "
    "so from by not no do does did me my us they them their he she his her".split()
)


def tokenize(text: str) -> List[str]:
    return [w for w in _TOKEN.findall(text.lower()) if w not in _STOP and len(w) > 1]


def _tf(tokens: List[str]) -> Counter:
    return Counter(tokens)


def _cosine(a: dict, b: dict) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


class TfidfIndex:
    """TF-IDF index over a fixed set of documents, with cosine query scoring."""

    def __init__(self, docs: List[str]):
        self.docs = docs
        tokenized = [tokenize(d) for d in docs]
        n = len(docs)
        df = Counter()
        for toks in tokenized:
            for t in set(toks):
                df[t] += 1
        # smoothed idf
        self.idf = {t: math.log((1 + n) / (1 + df_t)) + 1 for t, df_t in df.items()}
        self.doc_vecs = [self._vectorize(toks) for toks in tokenized]

    def _vectorize(self, tokens: List[str]) -> dict:
        tf = _tf(tokens)
        total = sum(tf.values()) or 1
        return {t: (c / total) * self.idf.get(t, math.log(len(self.docs) + 1) + 1)
                for t, c in tf.items()}

    def query(self, text: str, k: int = 3):
        """Return [(doc_index, score), ...] for the top-k most similar docs."""
        qv = self._vectorize(tokenize(text))
        scored = [(i, _cosine(qv, dv)) for i, dv in enumerate(self.doc_vecs)]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]


def pairwise_cosine(a: str, b: str) -> float:
    """Standalone TF-IDF cosine between two texts (fits idf on just the pair)."""
    idx = TfidfIndex([a, b])
    return _cosine(idx.doc_vecs[0], idx.doc_vecs[1])
