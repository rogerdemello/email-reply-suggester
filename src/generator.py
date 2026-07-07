"""
Suggested-reply generator: retrieval-augmented few-shot prompting over NIM.

Why this approach (trade-offs):
  - Prompting + RAG few-shot  (chosen): grounds the LLM in *our* inbox's tone and
    facts with zero training cost, updates instantly when the dataset changes, and
    is fully transparent (you can read exactly what grounded each reply). Cost is a
    few extra prompt tokens per call.
  - Fine-tuning: would bake the style in and shrink prompts, but needs far more data
    than we have, must be re-trained on every change, and hides its reasoning. Not
    worth it at this scale.
  - Zero-shot prompting: cheapest, but loses house tone and domain specifics
    (proration wording, SSO steps, refund windows) that the examples supply.
Retrieval few-shot is the sweet spot for a small, evolving support inbox.
"""
from typing import List, Tuple

from . import config
from . import llm
from .retriever import Retriever

SYSTEM_PROMPT = (
    "You are an experienced customer-support agent for a B2B SaaS product. "
    "You write suggested email replies that a human agent can send with little or no "
    "editing. Your replies are warm but concise, acknowledge the customer's situation, "
    "give concrete next steps, and never invent facts, prices, or commitments you're "
    "unsure of. Match the tone and structure of the example replies provided. "
    "Output ONLY the reply body text - no subject line, no preamble, no explanation."
)


def _build_user_prompt(subject: str, email: str,
                       examples: List[Tuple[dict, float]]) -> str:
    parts = [
        "Here are past emails from our inbox and the replies our best agents sent. "
        "Use them to match tone, structure, and domain facts:\n"
    ]
    for i, (ex, score) in enumerate(examples, 1):
        parts.append(
            f"--- EXAMPLE {i} (similarity {score:.2f}) ---\n"
            f"INCOMING EMAIL:\nSubject: {ex['subject']}\n{ex['email']}\n\n"
            f"REPLY THAT WAS SENT:\n{ex['reply']}\n"
        )
    parts.append(
        "--- NOW WRITE THE REPLY FOR THIS NEW EMAIL ---\n"
        f"Subject: {subject}\n{email}\n\n"
        "Write only the reply body:"
    )
    return "\n".join(parts)


def generate_reply(subject: str, email: str, retriever: Retriever = None,
                   k: int = None) -> dict:
    """Return {'reply', 'retrieved': [{id, category, similarity}], 'model'}."""
    retriever = retriever or Retriever()
    k = k or config.RETRIEVAL_K
    examples = retriever.retrieve(subject, email, k=k)
    user_prompt = _build_user_prompt(subject, email, examples)
    reply = llm.chat(
        [{"role": "system", "content": SYSTEM_PROMPT},
         {"role": "user", "content": user_prompt}],
        model=config.GEN_MODEL,
        temperature=config.GEN_TEMPERATURE,
    )
    return {
        "reply": reply,
        "retrieved": [
            {"id": ex["id"], "category": ex["category"], "similarity": round(s, 3)}
            for ex, s in examples
        ],
        "model": config.GEN_MODEL,
    }
