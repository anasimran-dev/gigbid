"""Regenerate the B5 results table from evals/results/*.json, and gate CI on thresholds.

  python -m evals.runners.results_table            -> evals/results/results_table.md
  python -m evals.runners.results_table --check    -> exit 1 if the smoke eval breaks a threshold
"""
import json
import sys

from evals.common import RESULTS, mean

THRESHOLDS = {"min_bid_or_skip_f1": 0.80, "max_unsupported_claims_per_proposal": 0.10}


def load(name: str) -> dict:
    path = RESULTS / f"{name}.json"
    return json.loads(path.read_text()) if path.exists() else {}


def table() -> str:
    rag, out = load("rag_eval").get("variants", {}), load("gigsim_outcomes").get("variants", {})
    judge = load("judge_calibration")
    lines = ["| Variant | Evidence Recall@5 | nDCG@10 | Unsupported claims per proposal | Judge score | GigSim reply rate | p95 latency (s) | Cost per proposal (USD) |",
             "|---|---|---|---|---|---|---|---|"]
    for v in rag:
        o = out.get(v, {})
        lines.append(f"| {v} | {rag[v]['overall']['recall@5']:.3f} | {rag[v]['overall']['ndcg@10']:.3f} | "
                     f"{o.get('unsupported_claims_per_proposal', 'n/a')} | {'see judge_calibration.json' if judge else 'not run (needs LLM)'} | "
                     f"{o.get('reply_rate', 'n/a')} | {o.get('p95_latency_s', 'n/a')} | {o.get('usd_per_proposal', 'n/a')} |")
    meta = load("rag_eval").get("meta", {})
    return "\n".join(lines) + f"\n\nProfile: {meta.get('profile')}; embeddings: {meta.get('embeddings')}; reranker: {meta.get('reranker')}; data: {meta.get('data')}.\n"


def check() -> int:
    d = load("decision_eval_smoke").get("personas", {})
    if not d:
        print("no smoke results found")
        return 1
    f1 = mean(p["bid_or_skip"]["f1"] for p in d.values())
    unsupported = mean(p["unsupported_claims_per_proposal_after"] for p in d.values())
    print(f"bid-or-skip F1 {f1} (min {THRESHOLDS['min_bid_or_skip_f1']}), unsupported claims {unsupported} (max {THRESHOLDS['max_unsupported_claims_per_proposal']})")
    return int(f1 < THRESHOLDS["min_bid_or_skip_f1"] or unsupported > THRESHOLDS["max_unsupported_claims_per_proposal"])


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check())
    (RESULTS / "results_table.md").write_text(table())
    print(table())
