"""
Deterministic local stand-in for the NIM LLM, used only when USE_MOCK=1.

Purpose: let the ENTIRE pipeline (generate -> evaluate -> report -> meta-eval) run
end-to-end with no API key and no network, so the plumbing can be smoke-tested and
example outputs produced. It is a heuristic, NOT a language model: replies are
assembled from the retrieved examples, and the "judge" scores by lexical overlap
with the gold reply. Real quality requires NVIDIA_API_KEY (unset USE_MOCK).

The heuristic judge is intentionally *discriminative* (overlap-based) so the
meta-evaluation's negative-control ordering genuinely holds under the mock, proving
the validation logic works. With a real LLM judge the scores reflect meaning, not
overlap.
"""
import json
import re

_STOP = set("a an the and or but to of for in on at is are be was were with your you "
            "we our i it this that will can could would should have has get got as "
            "if so from by not no do does me my us".split())


def _tokens(text):
    return [w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in _STOP]


def _overlap(a, b):
    sa, sb = set(_tokens(a)), set(_tokens(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)  # Jaccard


def _is_judge(messages):
    return any("SUGGESTED REPLY" in m.get("content", "") for m in messages)


def _extract(marker_start, marker_end, text):
    i = text.find(marker_start)
    if i == -1:
        return ""
    i += len(marker_start)
    j = text.find(marker_end, i) if marker_end else -1
    return text[i:j].strip() if j != -1 else text[i:].strip()


def _mock_generation(user_content):
    """Assemble a plausible reply from the first retrieved example."""
    ex_reply = _extract("REPLY THAT WAS SENT:\n", "\n---", user_content)
    if not ex_reply:
        ex_reply = _extract("REPLY THAT WAS SENT:\n", "\n--- NOW", user_content)
    body = ex_reply or ("Hi,\n\nThanks for reaching out - happy to help. I'll look "
                        "into this and get you a clear answer.\n\nBest,\nSupport Team")
    return ("Hi,\n\nThanks for getting in touch. " +
            re.sub(r"^Hi[^\n]*\n\n?", "", body).strip())


def _clamp(x):
    return max(1, min(5, int(round(x))))


def _mock_judge(user_content):
    gold = _extract("GOLD REPLY (one example of a strong answer - not the only "
                    "correct one):\n", "\n\nSUGGESTED REPLY", user_content)
    cand = _extract("SUGGESTED REPLY (the one you must grade):\n", None, user_content)
    o = _overlap(cand, gold)                    # 0..1 lexical overlap with gold
    has_greeting = bool(re.match(r"\s*(hi|hello|hey)\b", cand.lower()))
    action_words = sum(cand.lower().count(w) for w in
                       ["go to", "click", "settings", "i've", "you can", "reply",
                        "send", "let me", "i'll", "refund", "reconnect"])
    intent = _clamp(1 + 4 * o)
    fact = _clamp(1 + 4 * o)
    complete = _clamp(1 + 4 * o)
    tone = _clamp(4 + (1 if has_greeting else 0) - (1 if o < 0.05 else 0))
    action = _clamp(2 + min(3, action_words))
    return json.dumps({
        "intent_addressed": {"score": intent, "reason": f"lexical overlap with gold {o:.2f} (mock)"},
        "factual_grounding": {"score": fact, "reason": "claims track the gold (mock heuristic)"},
        "completeness": {"score": complete, "reason": "coverage approximated by overlap (mock)"},
        "tone": {"score": tone, "reason": "greeting/politeness heuristic (mock)"},
        "actionability": {"score": action, "reason": f"{action_words} action cues found (mock)"},
        "verdict": "mock heuristic score based on overlap with the gold reply",
    })


def chat(messages):
    user_content = "\n".join(m["content"] for m in messages if m.get("role") == "user")
    if _is_judge(messages):
        return _mock_judge(user_content)
    return _mock_generation(user_content)
