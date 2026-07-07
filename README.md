# AI Email Suggested-Response System

Given an incoming support email, this system generates a suggested reply grounded in a
dataset of past emails and their responses, and then measures how good each generated
reply actually is, and why.

The generator is deliberately simple and sensible. The bulk of the effort went into the
**accuracy / evaluation system** and into **validating that the accuracy score reflects
real quality, not just a number**, since that is what the challenge weights most heavily.

The results committed in this repo come from a real live NVIDIA NIM run
(`meta/llama-3.1-8b-instruct`): **overall 4.09 / 5, 100% pass rate, mean similarity
0.82**, with the full metric-validation suite passing (details in section 3).

**Live demo: https://email-reply-suggester-kfga.vercel.app/** - paste an email and see
the suggested reply and its per-dimension quality scores in the browser (a web page plus
a serverless API on Vercel). See [Deployment](#deployment) to run your own.

---

## Contents

- [Quick start](#quick-start)
- [1. The dataset](#1-the-dataset)
- [2. The response generator (Gen AI)](#2-the-response-generator-gen-ai)
- [3. Measuring accuracy (the core)](#3-measuring-accuracy-the-core)
- [Deployment](#deployment)
- [Repository layout](#repository-layout)
- [Configuration](#configuration)
- [Limitations](#limitations-honest)
- [How AI tools were used](#how-ai-tools-were-used)

---

## Quick start

```bash
pip install -r requirements.txt
python data/build_dataset.py            # (re)generate the dataset

# Option A - real results with NVIDIA NIM (what the committed results/ come from):
cp .env.example .env                    # then put your key in NVIDIA_API_KEY
python run.py --meta                    # generate + evaluate + validate the metric

# Option B - run end-to-end with NO key (deterministic mock backend):
USE_MOCK=1 python run.py --meta         # verifies the plumbing without credentials

# View the committed live results without running anything:
python run.py --offline
```

Outputs are written to `results/`:

| File | What it holds |
|------|---------------|
| `report.md` | Overall system score, per-response leaderboard, and the judge's reason for every dimension |
| `scores.csv` | One row per response: five dimension scores, overall, pass, similarity |
| `responses.json` | Full records: incoming email, gold, generated reply, retrieval, scores, reasons |
| `meta_eval.md` | The metric-validation suite (does the score reflect real quality?) |

---

## 1. The dataset

**Where it comes from.** Hand-authored synthetic data, produced by
`data/build_dataset.py`, modelled on a real B2B SaaS customer-support shared inbox (the
domain Hiver operates in). Every email/reply pair was written by a human to be
realistic: real intents, real tone, real edge cases. There is no scraped data and no
PII, so it is safe to publish and to reason about openly.

**What is in it.**

- `data/emails.jsonl` - 30 past `(email -> reply)` pairs. This is the reference pool the
  generator retrieves from.
- `data/test_set.jsonl` - 12 held-out incoming emails, each with a gold reply and a
  `human_note` describing what a good reply must do in that case. These are the cases we
  generate for and score against; the notes anchor the evaluation to human judgement.

**Why it is representative.** A support queue is dominated by a handful of recurring
intents. The dataset spans the ones that make up the long tail of a SaaS inbox:
billing, refunds, cancellations, bugs, how-to, account access, sales / pricing, feature
requests, integrations, onboarding, complaints / escalations, outages, and security.
Each intent appears multiple times with different phrasings and difficulty, so the
retriever has something meaningful to match on, and the evaluator is exercised on easy,
medium, and genuinely hard cases (angry customers, factual traps, ambiguous asks).

**Honesty about the data.** It is synthetic, so it is cleaner and more balanced than a
real inbox: no typos, no multi-language threads, no 50-message chains. That is a known
limitation (see [Limitations](#limitations-honest)). The upside is full transparency:
every fact a good reply should contain (proration rules, refund windows, SSO steps) is
visible in the data, which is exactly what lets the evaluator check factual grounding.

---

## 2. The response generator (Gen AI)

**Approach: retrieval-augmented few-shot prompting** over an LLM served by NVIDIA NIM.

For each new email the system (1) retrieves the `k` most similar past emails using
TF-IDF cosine similarity (deterministic, offline, free), and (2) shows them to the LLM as
worked `email -> reply` examples, then asks it to write the reply for the new email
(`src/generator.py`). The retrieved replies carry the house tone, structure, and domain
facts, so the model grounds its answer in our inbox rather than in generic knowledge.

**Model choice.** The default is `meta/llama-3.1-8b-instruct`. It was chosen for a
practical reason: on NIM's serverless tier it stays warm and responds in about 1 to 2
seconds, so the full pipeline runs reliably end-to-end. A larger model such as
`meta/llama-3.3-70b-instruct` produces better replies in spot checks, but on the free
tier it cold-started past several minutes and would stall a run, so 8B is the honest
default. Set `GEN_MODEL` / `JUDGE_MODEL` to a larger model if your tier keeps it warm.

**Why this approach and not the alternatives (trade-offs):**

| Approach | Verdict | Why |
|----------|---------|-----|
| **RAG few-shot (chosen)** | Yes | Grounds the LLM in our tone and facts with zero training cost, updates the instant the dataset changes, and is fully transparent: you can read exactly which past emails grounded each reply (the `retrieved` field). Cost is a few extra prompt tokens. |
| Fine-tuning | No | Would shrink prompts and bake in style, but it needs far more than 30 examples, must be re-trained on every change, and hides its reasoning. Not worth it at this scale. |
| Zero-shot prompting | No | Cheapest, but it loses house tone and domain specifics (exact proration wording, SSO steps, refund windows) that the examples supply. |

Retrieval uses TF-IDF rather than embeddings on purpose: for short support emails it is
strong enough, and keeping it deterministic and offline makes runs reproducible and
free. The LLM does the heavy lifting on the actual writing.

---

## 3. Measuring accuracy (the core)

### What "accurate" even means here

Exact match is the wrong target. For any support email there are many equally-good
replies (different words, same substance) and many subtly-bad ones (right words, wrong
facts). So instead of asking "does it match the gold string", we ask "does the reply do
its job", decomposed into five dimensions a support leader actually cares about:

| Dimension | Question | Weight |
|-----------|----------|--------|
| `intent_addressed` | Does it answer the specific question or handle the request? | 0.30 |
| `factual_grounding` | Are claims consistent with our data, with no invented prices, policies, timelines, or commitments? | 0.25 |
| `completeness` | Are all of the sender's asks covered, with nothing dropped? | 0.20 |
| `actionability` | Are there clear next steps the customer can act on? | 0.15 |
| `tone` | Is the register appropriate, empathetic, and professional? | 0.10 |

The weights are deliberate: substance (answering correctly and truthfully) outweighs
style. A polite reply that invents a refund policy is worse than a slightly stiff reply
that is correct, and the weights encode that. The `overall` score is the weighted mean,
on a 1 to 5 scale.

### The metric: two independent signals

**A) LLM-as-judge rubric (primary).** An LLM judge (`src/evaluator.py`) is shown the
incoming email, the retrieved context, and the gold reply as a reference (one example of
a good answer, explicitly not the only correct one), and scores each dimension from 1 to
5 with a one-sentence reason. This is why the system can tell you why a reply is good or
bad, not just a number. The judge is calibrated (5 = send as-is, 3 = usable after light
edits, 1 = wrong or unsendable) and runs at temperature 0 for stability.

**B) Embedding semantic similarity to the gold (secondary).** Cosine similarity between
the generated reply and the gold reply, using NIM embeddings
(`nvidia/nv-embedqa-e5-v5`), with a TF-IDF fallback. This is cheap and deterministic,
but on its own it over-penalises valid alternative phrasings, so it is a supporting
sanity signal, never the verdict.

**Why an LLM judge is the right primary metric here.** Reference-overlap metrics such as
BLEU, ROUGE, and exact match reward surface wording and punish valid paraphrases, which
is fatal when many good replies exist. Embedding similarity fixes paraphrase-blindness
but still measures closeness to one reference rather than quality, and it cannot see a
hallucinated policy. Only a rubric-based judge can weigh intent, factual grounding, and
completeness the way a human QA reviewer would, while staying cheap and consistent. We
keep the similarity signal alongside it precisely so the primary metric can be
cross-checked (see the next section).

### Reporting

- **Per-response** (`results/report.md`, `scores.csv`, `responses.json`): the five
  dimension scores, the weighted `overall`, a `pass` flag (`overall >= 3.5`), the
  secondary similarity, and the judge's reason for every dimension.
- **Overall system score** (`results/report.md`): the mean `overall` across the test
  set, the pass rate, per-dimension means, and the mean similarity.

### Validating the metric: does the score reflect real quality?

A number is worthless if we cannot trust it. `src/meta_eval.py` (run with
`python run.py --meta`) runs three checks a skeptic would demand, reported in
`results/meta_eval.md`.

1. **Discriminative validity (negative controls).** We feed the evaluator replies of
   known quality and check that it ranks them correctly: `gold` (the reference),
   `truncated` (first sentence only), `generic` ("we'll get back to you"), and
   `offtopic` (a good reply to a different email). A metric that measures quality must
   score gold highest and the wrong or empty replies lowest. We assert the defensible
   ordering `gold > truncated > {generic, offtopic}` and report each tier's mean. We
   deliberately do not rank generic against offtopic, because both are bad and the order
   is genuinely ambiguous. This ordering is exactly what the `human_note`s in the test
   set imply, so it is a direct metric-versus-human agreement check.
2. **Convergent validity.** The two independent signals (LLM judge and embedding
   similarity) should positively correlate across cases, reported as Spearman rho. A
   positive-but-imperfect correlation is the healthy result: they agree on direction
   while the judge captures quality that the similarity metric misses.
3. **Reliability (self-consistency).** We re-run the judge at temperature 0 and report
   the mean absolute change in `overall`. A value near zero means the metric is stable,
   not noise.

**Results from the committed live run** (`results/meta_eval.md`):

- Discrimination holds: `gold 4.30 > truncated 4.13 > {generic 3.00, offtopic 3.03}`.
- Convergent validity: Spearman rho = 0.62 (healthy positive-but-imperfect).
- Reliability: 0.03 mean change on re-run (stable).

This is the honest core of the submission: the accuracy system is not just "ask an LLM
for a score". It is a score whose validity is measured (it separates good from bad),
cross-checked (two signals agree), and stable (low variance).

---

## Deployment

**Live: https://email-reply-suggester-kfga.vercel.app/**

A lightweight live demo ships with the repo and is designed for **Vercel**:

- `api/suggest.py` - a single Python serverless entrypoint (declared in
  `pyproject.toml` as `api.suggest:handler`) that serves both the UI and the API:
  - `GET /` returns the self-contained web UI (`index.html`): paste an email, get the
    suggested reply plus the five per-dimension scores and reasons.
  - `POST /api/suggest` with `{"subject": "...", "email": "..."}` returns the reply,
    what it was grounded on, and the evaluation. For a live email there is no human gold
    reply, so the judge scores it against the most similar past reply as the reference
    (flagged in `reference_note`).
- `vercel.json` bundles `src/`, `data/`, and `index.html` into the function and allows
  up to 60s per request (LLM calls can be slow on a cold start).

The function has no heavy dependencies (the retriever and similarity fallback are
pure-Python; only the `openai` SDK is required), so the bundle stays small and cold
starts are quick. The reference pool is also embedded as an importable module
(`src/_pool_data.py`, generated by `build_dataset.py`), so retrieval works even if the
data files are not bundled.

**Deploy steps:**

1. On [vercel.com](https://vercel.com), "Add New Project" and import the GitHub repo
   `rogerdemello/email-reply-suggester`.
2. In the project's **Settings -> Environment Variables**, add `NVIDIA_API_KEY` (and
   optionally `GEN_MODEL`, `JUDGE_MODEL`, `EMBED_MODEL`). The key is never in the repo.
3. Deploy. The UI is served at `/` and the API at `/api/suggest`.

Or from the CLI: `npm i -g vercel`, then `vercel` (preview) / `vercel --prod`, setting
the env var with `vercel env add NVIDIA_API_KEY`.

Locally you can serve the same UI against a live key with any static server plus the
function, but the simplest local check is the pipeline (`python run.py`) or
`vercel dev`.

---

## Repository layout

```
data/build_dataset.py   generates emails.jsonl + test_set.jsonl (provenance in-file)
data/emails.jsonl       30 reference (email -> reply) pairs
data/test_set.jsonl     12 held-out emails + gold reply + human quality note
src/config.py           env-driven config (models, keys, weights, thresholds)
src/llm.py              NVIDIA NIM (OpenAI-compatible) client + mock switch
src/textsim.py          pure-Python TF-IDF + cosine (no heavy deps)
src/retriever.py        TF-IDF retrieval over the past-email pool
src/generator.py        retrieval-augmented few-shot reply generation
src/evaluator.py        five-dimension LLM-judge rubric + semantic similarity  (core)
src/meta_eval.py        validates the metric (controls, convergence, reliability)
src/mock_backend.py     deterministic no-key stand-in for smoke tests
run.py                  end-to-end: generate -> evaluate -> report [-> meta-eval]
api/suggest.py          Vercel serverless function: POST /api/suggest
index.html              self-contained web UI for the live demo
vercel.json             Vercel build/runtime config (bundles src + data)
results/                committed outputs from a real live NIM run (banner-stamped)
```

---

## Configuration

All configuration is via environment variables or a `.env` file (see `.env.example`):
`NVIDIA_API_KEY`, `GEN_MODEL`, `JUDGE_MODEL`, `EMBED_MODEL`, `RETRIEVAL_K`,
`GEN_TEMPERATURE`, `JUDGE_TEMPERATURE`, `PASS_THRESHOLD`, and `REQUEST_TIMEOUT`. The
defaults are sensible; only the key is required for a live run. The `.env` file is
gitignored, so your key is never committed.

---

## Limitations (honest)

- **Synthetic data** is cleaner than a real inbox: no typos, threads, attachments, or
  multiple languages. The retriever and evaluator would meet messier inputs in
  production.
- **The LLM judge shares a model family with the generator**, which risks
  self-preference bias. The mitigations in place are: the rubric is grounded on a
  human-authored gold reply plus human notes, the judge runs at temperature 0, and it is
  cross-checked against an independent similarity signal. A stronger setup would use a
  different model as the judge and a small batch of real human ratings to calibrate,
  which is a natural next step.
- **Small test set (12 cases).** Enough to demonstrate the method and its validation; a
  production rollout would scale this and track score drift over time.
- **Model choice was constrained by the NIM tier.** The default 8B model keeps the run
  fast and reproducible; the 70B gave better replies in spot checks but cold-started past
  practical timeouts on this key, so 8B is the honest default. The committed `results/`
  reflect the 8B run.

---

## How AI tools were used

This project was built with Claude (Anthropic) in Claude Code. AI assistance was used to
scaffold the pipeline, hand-author the synthetic dataset, and draft the evaluation and
meta-evaluation logic and this README. All design decisions were reviewed and directed
by a human: choosing RAG few-shot over fine-tuning, the five rubric dimensions and their
weights, and especially the three-part metric-validation strategy. The runtime models
are served by NVIDIA NIM; the mock backend is deterministic code, not a model.
