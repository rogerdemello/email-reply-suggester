# AI Email Suggested-Response System

Given an incoming support email, this system **generates a suggested reply** grounded
in a dataset of past emails and their responses, and — the part that matters most —
**measures how good each generated reply actually is, and why.**

The generator is deliberately simple and sensible. The bulk of the thinking here went
into the **accuracy/evaluation system** and into **validating that the accuracy score
reflects real quality, not just a number.**

---

## TL;DR — how to run

```bash
pip install -r requirements.txt
python data/build_dataset.py           # (re)generate the dataset

# Option A — real results with NVIDIA NIM (what the committed results/ come from):
cp .env.example .env                    # then put your key in NVIDIA_API_KEY
python run.py --meta                    # live generation + evaluation + metric validation

# Option B — run end-to-end with NO key (deterministic mock backend):
USE_MOCK=1 python run.py --meta         # verifies the plumbing without credentials

# View the committed live results without running anything:
python run.py --offline
```

Outputs land in `results/`: `report.md` (leaderboard + per-response "why"),
`scores.csv`, `responses.json`, and `meta_eval.md` (the metric-validation suite).

> The results committed in this repo (`results/`) are from a **real live NVIDIA NIM
> run** (`meta/llama-3.1-8b-instruct`): **overall 4.13/5, 100% pass rate, mean
> similarity 0.81**, and the metric-validation suite passes (see below). If you don't
> have a key, `USE_MOCK=1` still runs the whole pipeline via a deterministic stand-in.

---

## 1. The dataset

**Where it comes from.** Hand-authored synthetic data (`data/build_dataset.py`),
modelled on a real B2B SaaS **customer-support shared inbox** — the domain Hiver
operates in. Every email/reply pair was written by a human to be realistic: real
intents, real tone, real edge cases. No scraped data and no PII, so it is safe to
publish and to reason about openly.

**What's in it.**
- `data/emails.jsonl` — **30** past `(email → reply)` pairs. This is the reference
  pool the generator retrieves from.
- `data/test_set.jsonl` — **12** held-out incoming emails, each with a **gold reply**
  *and* a **`human_note`** describing what a good reply must do here. These are the
  cases we generate for and score against; the notes anchor the evaluation to human
  judgement.

**Why it's representative.** A support queue is dominated by a handful of recurring
*intents*. The dataset spans the ones that make up the long tail of a SaaS inbox —
billing, refunds, cancellations, bugs, how-to, account access, sales/pricing, feature
requests, integrations, onboarding, complaints/escalations, outages, security — each
appearing multiple times with **different phrasings and difficulty**. That gives the
retriever something meaningful to match on, and exercises the evaluator on easy,
medium and genuinely hard cases (angry customers, factual traps, ambiguous asks).

**Honesty about the data.** It's synthetic, so it's clean and balanced in a way a real
inbox isn't — no typos, no multi-language threads, no 50-message chains. That's a known
limitation (see *Limitations*). The upside is full transparency: every "fact" a good
reply should contain (proration rules, refund windows, SSO steps) is visible in the
data, which is exactly what lets the evaluator check factual grounding.

---

## 2. The response generator (Gen AI)

**Approach: retrieval-augmented few-shot prompting** over an LLM served by NVIDIA NIM
(`meta/llama-3.1-8b-instruct` by default, OpenAI-compatible endpoint — chosen because
it stays warm on NIM's serverless tier and responds in ~1-2s, so the full pipeline runs
reliably end-to-end; a larger model like `meta/llama-3.3-70b-instruct` raises quality
but can cold-start for minutes on the free tier — set `GEN_MODEL`/`JUDGE_MODEL` to use
one if your tier keeps it warm).

For each new email we (1) retrieve the `k` most similar past emails (TF-IDF cosine —
deterministic, offline, free), and (2) show them to the LLM as worked
`email → reply` examples, then ask it to write the reply for the new email
(`src/generator.py`). The retrieved replies carry the house **tone**, **structure**,
and **domain facts**, so the model grounds its answer in *our* inbox rather than
generic knowledge.

**Why this and not the alternatives (trade-offs):**

| Approach | Verdict | Why |
|---|---|---|
| **RAG few-shot (chosen)** | ✅ | Grounds the LLM in our tone & facts with **zero training cost**, updates the instant the dataset changes, and is **fully transparent** — you can read exactly which past emails grounded each reply (`retrieved` field). Cost: a few extra prompt tokens. |
| Fine-tuning | ❌ | Would shrink prompts and bake in style, but needs far more than 30 examples, must be re-trained on every change, and hides its reasoning. Not worth it at this scale. |
| Zero-shot prompting | ❌ | Cheapest, but loses house tone and domain specifics (exact proration wording, SSO steps, refund windows) that the examples supply. |

Retrieval uses TF-IDF rather than embeddings on purpose: for short support emails it's
strong enough, and keeping it deterministic/offline makes runs reproducible and free.
The LLM does the heavy lifting on the actual writing.

---

## 3. Measuring accuracy — the core

### What "accurate" even means here

Exact match is the wrong target. For any support email there are **many equally-good
replies** (different words, same substance) and **many subtly-bad ones** (right words,
wrong facts). So instead of "does it match the gold string," we ask **"does the reply
do its job?"** — decomposed into five dimensions a support leader actually cares about:

| Dimension | Question | Weight |
|---|---|---|
| `intent_addressed` | Does it answer the specific question / handle the request? | **0.30** |
| `factual_grounding` | Are claims consistent with our data — no invented prices, policies, timelines, or commitments? | **0.25** |
| `completeness` | Are **all** the sender's asks covered (nothing dropped)? | **0.20** |
| `actionability` | Clear next steps the customer can act on? | **0.15** |
| `tone` | Appropriate, empathetic, professional register? | **0.10** |

Weights are deliberate: **substance (answering correctly and truthfully) outweighs
style.** A polite reply that invents a refund policy is worse than a slightly stiff
reply that's correct — the weights encode that. `overall` is the weighted mean (1–5).

### The metric: two independent signals

**A) LLM-as-judge rubric (primary).** An LLM judge (`src/evaluator.py`) is shown the
incoming email, the retrieved context, and the **gold reply as a *reference* — one
example of a good answer, explicitly *not* the only correct one** — and scores each
dimension 1–5 **with a one-sentence reason**. This is why the system can tell you
*why* a reply is good or bad, not just a number. The judge is calibrated
(5 = send as-is, 3 = usable after light edits, 1 = wrong/unsendable) and run at
temperature 0 for stability.

**B) Embedding semantic similarity to the gold (secondary).** Cosine similarity
between the generated reply and the gold (NIM embeddings, TF-IDF fallback). Cheap and
deterministic, but on its own it **over-penalises valid alternative phrasings** — so
it's a *supporting sanity signal*, never the verdict.

**Why an LLM judge is the right primary metric here.** Reference-overlap metrics
(BLEU/ROUGE/exact match) reward surface wording and punish valid paraphrases — fatal
when many good replies exist. Embedding similarity fixes paraphrase-blindness but still
measures *closeness to one reference*, not *quality*, and can't see a hallucinated
policy. Only a rubric-based judge can weigh intent, factual grounding, and completeness
the way a human QA reviewer would — and it stays cheap and consistent. We keep the
similarity signal alongside it precisely so the primary metric can be cross-checked
(next section).

### Reporting

- **Per-response** (`results/report.md`, `scores.csv`, `responses.json`): five
  dimension scores, the weighted `overall`, a `pass` flag (`overall ≥ 3.5`), the
  secondary similarity, and the judge's **reason for every dimension**.
- **Overall system score** (`results/report.md`): mean `overall` across the test set,
  **pass rate**, per-dimension means, and mean similarity.

### Validating the metric — *does the score reflect real quality?*

A number is worthless if we can't trust it. `src/meta_eval.py` (`python run.py --meta`)
runs three checks a skeptic would demand, reported in `results/meta_eval.md`:

1. **Discriminative validity (negative controls).** We feed the evaluator replies of
   *known* quality and check it ranks them correctly:
   `gold` (the reference) → `truncated` (first sentence only) → `generic`
   ("we'll get back to you") / `offtopic` (a good reply to a *different* email). A
   metric that measures quality **must** score gold highest and the wrong/empty
   replies lowest. We assert the defensible ordering `gold > truncated > {generic,
   offtopic}` and report each tier's mean. (We deliberately *don't* rank generic vs
   offtopic against each other — both are bad and the order is genuinely ambiguous.)
   This ordering is exactly what the `human_note`s in the test set imply, so it's a
   direct **metric-vs-human** agreement check.
2. **Convergent validity.** The two independent signals (LLM judge vs embedding
   similarity) should **positively correlate** across cases — reported as Spearman ρ.
   *Positive-but-imperfect* is the healthy result: they agree on direction while the
   judge captures quality the similarity metric misses.
3. **Reliability (self-consistency).** We re-run the judge at temperature 0 and report
   the mean absolute change in `overall`. Near-zero ⇒ the metric is stable, not noise.

This is the honest core of the submission: the accuracy system is not just "ask an LLM
for a score" — it's a score whose validity is **measured** (it separates good from bad),
**cross-checked** (two signals agree), and **stable** (low variance).

**On the committed live run** (`results/meta_eval.md`): discrimination holds —
`gold 4.35 > truncated 4.15 > {generic 3.00, offtopic 3.01}`; convergent validity
Spearman ρ = **0.60** (healthy positive-but-imperfect); reliability = **0.12** mean
change on re-run (stable). The metric behaves the way a trustworthy metric should.

---

## Repository layout

```
data/build_dataset.py   # generates emails.jsonl + test_set.jsonl (provenance in-file)
data/emails.jsonl       # 30 reference (email -> reply) pairs
data/test_set.jsonl     # 12 held-out emails + gold reply + human quality note
src/config.py           # env-driven config (models, keys, weights, thresholds)
src/llm.py              # NVIDIA NIM (OpenAI-compatible) client + mock switch
src/retriever.py        # TF-IDF retrieval over the past-email pool
src/generator.py        # retrieval-augmented few-shot reply generation
src/evaluator.py        # 5-dimension LLM-judge rubric + semantic similarity  <-- core
src/meta_eval.py        # validates the metric (controls, convergence, reliability)
src/mock_backend.py     # deterministic no-key stand-in for smoke tests
run.py                  # end-to-end: generate -> evaluate -> report [-> meta-eval]
results/                # committed outputs from a real live NIM run (banner-stamped)
```

## Configuration

All via env / `.env` (see `.env.example`): `NVIDIA_API_KEY`, `GEN_MODEL`,
`JUDGE_MODEL`, `EMBED_MODEL`, `RETRIEVAL_K`, `GEN_TEMPERATURE`, `JUDGE_TEMPERATURE`,
`PASS_THRESHOLD`. Defaults are sensible; only the key is required for a live run.

## Limitations (honest)

- **Synthetic data** is cleaner than a real inbox (no typos, threads, attachments, or
  multi-language). The retriever and evaluator would meet messier inputs in production.
- **LLM-as-judge shares a model family with the generator**, risking self-preference
  bias. Mitigations in place: the rubric is grounded on a human-authored gold + human
  notes, temperature 0, and cross-checked against an independent similarity signal.
  A stronger setup would use a *different* model as judge and a small batch of real
  human ratings to calibrate — a natural next step.
- **Small test set (12).** Enough to demonstrate the method and its validation; a
  production rollout would scale this and track score drift over time.
- **Model choice was constrained by the NIM tier.** The default 8B model keeps the run
  fast and reproducible; the 70B gave better replies in spot checks but cold-started
  past practical timeouts on this key, so 8B is the honest default. The committed
  `results/` reflect the 8B run.

## How AI tools were used

This project was built with **Claude (Anthropic) in Claude Code**. AI assistance was
used to scaffold the pipeline, hand-author the synthetic dataset, and draft the
evaluation/meta-evaluation logic and this README. All design decisions — choosing
RAG few-shot over fine-tuning, the five rubric dimensions and their weights, and
especially the three-part metric-validation strategy — were reviewed and directed by a
human. The runtime models are served by **NVIDIA NIM**; the mock backend is
deterministic code, not a model.
