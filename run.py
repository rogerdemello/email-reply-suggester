"""
End-to-end runner.

    python run.py                # live: generate replies for the held-out set,
                                 # evaluate each, write per-response + overall scores
    python run.py --meta         # also run the metric-validation (meta-eval) suite
    python run.py --offline      # reprint the report from committed cached results
                                 # (no API key needed - for graders)
    python run.py --limit N      # only process the first N test cases

Outputs (in results/):
    responses.json   full per-response records (reply, retrieval, scores, reasons)
    scores.csv       one row per response, per-dimension + overall + similarity
    report.md        human-readable leaderboard + overall system score
    meta_eval.md     (with --meta) validation that the metric reflects real quality
"""
import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from src import config
from src import llm
from src.generator import generate_reply
from src.retriever import Retriever, load_pool
from src import evaluator
from src import meta_eval

BACKEND = "mock (USE_MOCK=1, heuristic - NOT a real model)" if llm.USE_MOCK \
    else f"NVIDIA NIM ({config.GEN_MODEL})"

RESULTS = os.path.join(HERE, "results")
DATA = os.path.join(HERE, "data")
os.makedirs(RESULTS, exist_ok=True)


def load_test():
    rows = []
    with open(os.path.join(DATA, "test_set.jsonl"), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def build_context(retrieved_ids, pool):
    by_id = {r["id"]: r for r in pool}
    chunks = []
    for rid in retrieved_ids:
        r = by_id.get(rid)
        if r:
            chunks.append(f"[{r['category']}] {r['reply']}")
    return "\n\n".join(chunks)


def run_live(limit=None):
    test = load_test()
    if limit:
        test = test[:limit]
    pool = load_pool()
    retriever = Retriever(pool)
    records = []
    for t in test:
        print(f"-> {t['id']} ({t['category']}): generating...")
        gen = generate_reply(t["subject"], t["email"], retriever=retriever)
        context = build_context([r["id"] for r in gen["retrieved"]], pool)
        print(f"   evaluating...")
        ev = evaluator.evaluate(t["subject"], t["email"], gen["reply"],
                                t["gold_reply"], context=context)
        records.append({
            "id": t["id"], "category": t["category"], "subject": t["subject"],
            "email": t["email"], "gold_reply": t["gold_reply"],
            "generated_reply": gen["reply"], "retrieved": gen["retrieved"],
            "evaluation": ev, "human_note": t.get("human_note", ""),
            "backend": BACKEND,
        })
    return records


def write_outputs(records):
    with open(os.path.join(RESULTS, "responses.json"), "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    with open(os.path.join(RESULTS, "scores.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        dims = evaluator.DIMENSIONS
        w.writerow(["id", "category"] + dims + ["overall", "pass", "semantic_similarity"])
        for r in records:
            ev = r["evaluation"]
            w.writerow([r["id"], r["category"]]
                       + [ev["dimensions"][d] for d in dims]
                       + [ev["overall"], ev["pass"], ev["semantic_similarity"]])

    write_report(records)


def write_report(records):
    n = len(records)
    overall = sum(r["evaluation"]["overall"] for r in records) / n
    passes = sum(1 for r in records if r["evaluation"]["pass"])
    avg_sim = sum(r["evaluation"]["semantic_similarity"] for r in records) / n
    dims = evaluator.DIMENSIONS
    dim_means = {d: round(sum(r["evaluation"]["dimensions"][d] for r in records) / n, 2)
                 for d in dims}

    backend = records[0].get("backend", "unknown") if records else "unknown"
    lines = ["# Suggested-reply accuracy report\n"]
    lines.append(f"> **Backend used:** {backend}")
    if "mock" in backend:
        lines.append("> These numbers come from the deterministic **mock** smoke-test "
                     "backend (heuristic, not a language model). They verify the "
                     "pipeline runs end-to-end; they are **not** representative of real "
                     "reply quality. Set `NVIDIA_API_KEY` and unset `USE_MOCK` for real "
                     "results.\n")
    lines.append("## Overall system score\n")
    lines.append(f"- **Mean overall quality: {overall:.2f} / 5** (weighted rubric)")
    lines.append(f"- **Pass rate (overall >= {config.PASS_THRESHOLD}): "
                 f"{passes}/{n} = {100*passes/n:.0f}%**")
    lines.append(f"- Mean semantic similarity to gold: {avg_sim:.2f}")
    lines.append(f"- Per-dimension means: " +
                 ", ".join(f"{d}={dim_means[d]}" for d in dims) + "\n")

    lines.append("## Per-response scores\n")
    lines.append("| id | category | overall | pass | sim | intent | fact | complete | tone | action |")
    lines.append("|----|----------|---------|------|-----|--------|------|----------|------|--------|")
    for r in records:
        ev = r["evaluation"]; ds = ev["dimensions"]
        lines.append(
            f"| {r['id']} | {r['category']} | {ev['overall']} | "
            f"{'Y' if ev['pass'] else 'N'} | {ev['semantic_similarity']} | "
            f"{ds['intent_addressed']} | {ds['factual_grounding']} | "
            f"{ds['completeness']} | {ds['tone']} | {ds['actionability']} |")

    lines.append("\n## Detail (why each score)\n")
    for r in records:
        ev = r["evaluation"]
        lines.append(f"### {r['id']} - {r['subject']}  (overall {ev['overall']}/5)")
        lines.append(f"*Verdict:* {ev['verdict']}")
        for d in dims:
            lines.append(f"- **{d}** = {ev['dimensions'][d]}: {ev['reasons'][d]}")
        lines.append("")

    with open(os.path.join(RESULTS, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n" + "=" * 60)
    print(f"OVERALL SYSTEM SCORE: {overall:.2f}/5   |   "
          f"pass rate {passes}/{n} ({100*passes/n:.0f}%)   |   "
          f"mean similarity {avg_sim:.2f}")
    print("=" * 60)
    print(f"Reports written to {RESULTS}/")


def run_offline():
    path = os.path.join(RESULTS, "responses.json")
    if not os.path.exists(path):
        print("No cached results found at results/responses.json. Run live once "
              "(set NVIDIA_API_KEY) to generate them.")
        return
    with open(path, encoding="utf-8") as f:
        records = json.load(f)
    write_report(records)
    print("(reprinted from cached results/responses.json)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="reprint report from cached results (no API key)")
    ap.add_argument("--meta", action="store_true",
                    help="also run metric-validation (meta-eval)")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    if args.offline:
        run_offline()
        return

    if not config.have_key():
        print("NVIDIA_API_KEY not set. Copy .env.example to .env and add your key, "
              "or use `python run.py --offline` to view cached results.")
        sys.exit(1)

    records = run_live(limit=args.limit)
    write_outputs(records)

    if args.meta:
        print("\nRunning meta-evaluation (validating the metric)...")
        summary = meta_eval.run(sample=args.limit)
        md = meta_eval.to_markdown(summary)
        with open(os.path.join(RESULTS, "meta_eval.md"), "w", encoding="utf-8") as f:
            f.write(md)
        with open(os.path.join(RESULTS, "meta_eval.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(md)


if __name__ == "__main__":
    main()
