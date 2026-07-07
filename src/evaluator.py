"""
Accuracy / quality evaluation for a suggested reply  -- the heart of the project.

WHAT "ACCURATE" MEANS FOR A SUGGESTED REPLY
-------------------------------------------
Exact string match is the wrong target: for any support email there are many
equally-good replies (different wording, same substance), and many subtly-bad ones
(right words, wrong facts). So we score whether the reply does its *job*, along five
dimensions a support leader actually cares about:

  1. intent_addressed  - does it answer the specific question / handle the request?
  2. factual_grounding  - are claims consistent with the retrieved context & gold,
                          with no invented prices, policies, or commitments?
  3. completeness       - are all of the sender's asks covered (nothing dropped)?
  4. tone               - appropriate register: empathetic, professional, not curt?
  5. actionability      - clear next steps / resolution the customer can act on?

Each is scored 1-5 by an LLM judge that is shown the incoming email, the retrieved
context, and the GOLD reply as a *reference* (an example of a good answer, NOT the
only correct one). The judge returns a rationale per dimension, so every score is
explainable ("why"), not just a number.

WE COMBINE TWO INDEPENDENT SIGNALS
----------------------------------
  A) LLM-as-judge rubric (primary)  - captures meaning & quality; correlates with
     human judgement; gives the "why".
  B) Embedding semantic similarity to the gold reply (secondary, reference-based) -
     cheap, deterministic sanity signal. On its own it over-penalises valid
     alternative phrasings, so it is a *supporting* metric, not the verdict.

Reporting both, and their agreement, is what lets us trust the number
(see meta_eval.py for the validation of the metric itself).
"""
import json
from typing import Optional

from . import config
from . import llm

DIMENSIONS = ["intent_addressed", "factual_grounding", "completeness",
              "tone", "actionability"]

# Weights: substance (does it answer, is it true, is it complete) matters more than
# style. These are deliberate and documented in the README.
WEIGHTS = {
    "intent_addressed": 0.30,
    "factual_grounding": 0.25,
    "completeness": 0.20,
    "tone": 0.10,
    "actionability": 0.15,
}

JUDGE_SYSTEM = (
    "You are a meticulous, skeptical QA reviewer for a customer-support team. "
    "You grade a SUGGESTED reply against the incoming email. You are shown a GOLD "
    "reply as ONE example of a good answer - a different reply can score just as "
    "high if it does the job. Reward correctness and helpfulness; punish invented "
    "facts, dropped questions, wrong steps, and bad tone. Be calibrated: 5 = ready "
    "to send as-is, 3 = usable after light edits, 1 = wrong or unsendable. "
    "Return STRICT JSON only."
)

JUDGE_TEMPLATE = """Grade the SUGGESTED REPLY on five dimensions, each an integer 1-5.

INCOMING EMAIL
Subject: {subject}
{email}

RETRIEVED CONTEXT (facts our best agents used for similar emails):
{context}

GOLD REPLY (one example of a strong answer - not the only correct one):
{gold}

SUGGESTED REPLY (the one you must grade):
{candidate}

Score these dimensions (integers 1-5) and give a one-sentence reason for each:
- intent_addressed: does it answer the specific question / handle the request?
- factual_grounding: are claims consistent with the context/gold, with NO invented
  prices, policies, timelines, or commitments?
- completeness: are ALL of the sender's asks covered (nothing important dropped)?
- tone: appropriate, empathetic, professional register for this situation?
- actionability: clear next steps / resolution the customer can act on?

Also give an overall one-line verdict.

Return STRICT JSON exactly like:
{{"intent_addressed": {{"score": 4, "reason": "..."}},
 "factual_grounding": {{"score": 5, "reason": "..."}},
 "completeness": {{"score": 3, "reason": "..."}},
 "tone": {{"score": 5, "reason": "..."}},
 "actionability": {{"score": 4, "reason": "..."}},
 "verdict": "..."}}"""


# ---------------------------------------------------------------------------
# Semantic similarity (secondary, reference-based)
# ---------------------------------------------------------------------------
def _cosine(a, b):
    import math
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def semantic_similarity(candidate: str, gold: str) -> dict:
    """Cosine similarity of candidate vs gold. NIM embeddings, TF-IDF fallback."""
    embs = llm.embed([candidate, gold], input_type="passage")
    if embs is not None:
        return {"similarity": round(_cosine(embs[0], embs[1]), 4), "method": "nim-embed"}
    # Fallback: TF-IDF cosine (offline, deterministic)
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    m = TfidfVectorizer(stop_words="english").fit_transform([candidate, gold])
    return {"similarity": round(float(cosine_similarity(m[0], m[1])[0][0]), 4),
            "method": "tfidf-fallback"}


# ---------------------------------------------------------------------------
# LLM-as-judge rubric (primary)
# ---------------------------------------------------------------------------
def judge(subject: str, email: str, candidate: str, gold: str,
          context: str = "") -> dict:
    prompt = JUDGE_TEMPLATE.format(
        subject=subject, email=email, context=context or "(none)",
        gold=gold, candidate=candidate)
    result = llm.chat_json(
        [{"role": "system", "content": JUDGE_SYSTEM},
         {"role": "user", "content": prompt}],
        model=config.JUDGE_MODEL,
        temperature=config.JUDGE_TEMPERATURE,
    )
    return result


def _weighted_overall(dim_scores: dict) -> float:
    total = sum(WEIGHTS[d] * dim_scores[d] for d in DIMENSIONS)
    return round(total, 3)


def evaluate(subject: str, email: str, candidate: str, gold: str,
             context: str = "") -> dict:
    """
    Full evaluation of one suggested reply.
    Returns per-dimension scores + reasons, a weighted overall (1-5), a pass flag,
    and the secondary semantic-similarity signal.
    """
    j = judge(subject, email, candidate, gold, context)
    dim_scores = {d: int(j[d]["score"]) for d in DIMENSIONS}
    dim_reasons = {d: j[d].get("reason", "") for d in DIMENSIONS}
    overall = _weighted_overall(dim_scores)
    sim = semantic_similarity(candidate, gold)
    return {
        "dimensions": dim_scores,
        "reasons": dim_reasons,
        "verdict": j.get("verdict", ""),
        "overall": overall,                       # weighted mean of dimensions, 1-5
        "pass": overall >= config.PASS_THRESHOLD,
        "semantic_similarity": sim["similarity"],  # secondary signal, 0-1
        "similarity_method": sim["method"],
        "weights": WEIGHTS,
    }
