# Suggested-reply accuracy report

> **Backend used:** mock (USE_MOCK=1, heuristic - NOT a real model)
> These numbers come from the deterministic **mock** smoke-test backend (heuristic, not a language model). They verify the pipeline runs end-to-end; they are **not** representative of real reply quality. Set `NVIDIA_API_KEY` and unset `USE_MOCK` for real results.

## Overall system score

- **Mean overall quality: 2.05 / 5** (weighted rubric)
- **Pass rate (overall >= 3.5): 0/12 = 0%**
- Mean semantic similarity to gold: 0.12
- Per-dimension means: intent_addressed=1.08, factual_grounding=1.08, completeness=1.08, tone=4.83, actionability=5.0

## Per-response scores

| id | category | overall | pass | sim | intent | fact | complete | tone | action |
|----|----------|---------|------|-----|--------|------|----------|------|--------|
| test-001 | billing | 2.0 | N | 0.1728 | 1 | 1 | 1 | 5 | 5 |
| test-002 | bug | 1.9 | N | 0.0785 | 1 | 1 | 1 | 4 | 5 |
| test-003 | refund | 2.0 | N | 0.1332 | 1 | 1 | 1 | 5 | 5 |
| test-004 | access | 2.0 | N | 0.0935 | 1 | 1 | 1 | 5 | 5 |
| test-005 | sales | 2.0 | N | 0.1569 | 1 | 1 | 1 | 5 | 5 |
| test-006 | feature_request | 2.0 | N | 0.0798 | 1 | 1 | 1 | 5 | 5 |
| test-007 | complaint | 2.0 | N | 0.0802 | 1 | 1 | 1 | 5 | 5 |
| test-008 | howto | 1.9 | N | 0.0756 | 1 | 1 | 1 | 4 | 5 |
| test-009 | outage | 2.75 | N | 0.2046 | 2 | 2 | 2 | 5 | 5 |
| test-010 | integration | 2.0 | N | 0.0751 | 1 | 1 | 1 | 5 | 5 |
| test-011 | cancellation | 2.0 | N | 0.1498 | 1 | 1 | 1 | 5 | 5 |
| test-012 | security | 2.0 | N | 0.0861 | 1 | 1 | 1 | 5 | 5 |

## Detail (why each score)

### test-001 - Charged twice this month  (overall 2.0/5)
*Verdict:* mock heuristic score based on overlap with the gold reply
- **intent_addressed** = 1: lexical overlap with gold 0.11 (mock)
- **factual_grounding** = 1: claims track the gold (mock heuristic)
- **completeness** = 1: coverage approximated by overlap (mock)
- **tone** = 5: greeting/politeness heuristic (mock)
- **actionability** = 5: 3 action cues found (mock)

### test-002 - Dashboard shows wrong numbers  (overall 1.9/5)
*Verdict:* mock heuristic score based on overlap with the gold reply
- **intent_addressed** = 1: lexical overlap with gold 0.05 (mock)
- **factual_grounding** = 1: claims track the gold (mock heuristic)
- **completeness** = 1: coverage approximated by overlap (mock)
- **tone** = 4: greeting/politeness heuristic (mock)
- **actionability** = 5: 3 action cues found (mock)

### test-003 - Refund after price increase  (overall 2.0/5)
*Verdict:* mock heuristic score based on overlap with the gold reply
- **intent_addressed** = 1: lexical overlap with gold 0.09 (mock)
- **factual_grounding** = 1: claims track the gold (mock heuristic)
- **completeness** = 1: coverage approximated by overlap (mock)
- **tone** = 5: greeting/politeness heuristic (mock)
- **actionability** = 5: 3 action cues found (mock)

### test-004 - Can't reset my password  (overall 2.0/5)
*Verdict:* mock heuristic score based on overlap with the gold reply
- **intent_addressed** = 1: lexical overlap with gold 0.07 (mock)
- **factual_grounding** = 1: claims track the gold (mock heuristic)
- **completeness** = 1: coverage approximated by overlap (mock)
- **tone** = 5: greeting/politeness heuristic (mock)
- **actionability** = 5: 4 action cues found (mock)

### test-005 - Comparing you vs a competitor  (overall 2.0/5)
*Verdict:* mock heuristic score based on overlap with the gold reply
- **intent_addressed** = 1: lexical overlap with gold 0.09 (mock)
- **factual_grounding** = 1: claims track the gold (mock heuristic)
- **completeness** = 1: coverage approximated by overlap (mock)
- **tone** = 5: greeting/politeness heuristic (mock)
- **actionability** = 5: 4 action cues found (mock)

### test-006 - Need Salesforce integration  (overall 2.0/5)
*Verdict:* mock heuristic score based on overlap with the gold reply
- **intent_addressed** = 1: lexical overlap with gold 0.06 (mock)
- **factual_grounding** = 1: claims track the gold (mock heuristic)
- **completeness** = 1: coverage approximated by overlap (mock)
- **tone** = 5: greeting/politeness heuristic (mock)
- **actionability** = 5: 5 action cues found (mock)

### test-007 - Your last reply didn't solve anything  (overall 2.0/5)
*Verdict:* mock heuristic score based on overlap with the gold reply
- **intent_addressed** = 1: lexical overlap with gold 0.06 (mock)
- **factual_grounding** = 1: claims track the gold (mock heuristic)
- **completeness** = 1: coverage approximated by overlap (mock)
- **tone** = 5: greeting/politeness heuristic (mock)
- **actionability** = 5: 4 action cues found (mock)

### test-008 - How to give a client view-only access  (overall 1.9/5)
*Verdict:* mock heuristic score based on overlap with the gold reply
- **intent_addressed** = 1: lexical overlap with gold 0.04 (mock)
- **factual_grounding** = 1: claims track the gold (mock heuristic)
- **completeness** = 1: coverage approximated by overlap (mock)
- **tone** = 4: greeting/politeness heuristic (mock)
- **actionability** = 5: 5 action cues found (mock)

### test-009 - Everything is broken right now  (overall 2.75/5)
*Verdict:* mock heuristic score based on overlap with the gold reply
- **intent_addressed** = 2: lexical overlap with gold 0.13 (mock)
- **factual_grounding** = 2: claims track the gold (mock heuristic)
- **completeness** = 2: coverage approximated by overlap (mock)
- **tone** = 5: greeting/politeness heuristic (mock)
- **actionability** = 5: 4 action cues found (mock)

### test-010 - Webhook payloads changed and broke our code  (overall 2.0/5)
*Verdict:* mock heuristic score based on overlap with the gold reply
- **intent_addressed** = 1: lexical overlap with gold 0.06 (mock)
- **factual_grounding** = 1: claims track the gold (mock heuristic)
- **completeness** = 1: coverage approximated by overlap (mock)
- **tone** = 5: greeting/politeness heuristic (mock)
- **actionability** = 5: 7 action cues found (mock)

### test-011 - Downgrade instead of cancel?  (overall 2.0/5)
*Verdict:* mock heuristic score based on overlap with the gold reply
- **intent_addressed** = 1: lexical overlap with gold 0.07 (mock)
- **factual_grounding** = 1: claims track the gold (mock heuristic)
- **completeness** = 1: coverage approximated by overlap (mock)
- **tone** = 5: greeting/politeness heuristic (mock)
- **actionability** = 5: 6 action cues found (mock)

### test-012 - Was our data part of the breach in the news?  (overall 2.0/5)
*Verdict:* mock heuristic score based on overlap with the gold reply
- **intent_addressed** = 1: lexical overlap with gold 0.06 (mock)
- **factual_grounding** = 1: claims track the gold (mock heuristic)
- **completeness** = 1: coverage approximated by overlap (mock)
- **tone** = 5: greeting/politeness heuristic (mock)
- **actionability** = 5: 6 action cues found (mock)
