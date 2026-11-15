"""B4 judge calibration: Cohen's kappa between the LLM judge and YOUR labels on 30 proposals.

Step 1  python -m evals.runners.judge_calibration --export   -> evals/datasets/judge_items.json (30 proposals)
Step 2  label them yourself: add "human": 1..5 to each item (do this before looking at the judge)
Step 3  python -m evals.runners.judge_calibration            -> evals/results/judge_calibration.json
Needs an LLM profile (MODEL_PROFILE=open). Scores are binned to low (1-2), mid (3), high (4-5) for kappa.
"""
import json
import sys

from pydantic import BaseModel

from agent import llm
from evals.common import PERSONAS, ROOT, load_dev, load_jobs, quiet_marketplace, run_job, save

ITEMS = ROOT / "evals" / "datasets" / "judge_items.json"


class JudgeScore(BaseModel):
    relevance: int
    evidence: int
    clarity: int
    professionalism: int
    overall: float


def judge(job: dict, proposal: str) -> float | None:
    s = llm.structured("judge", JudgeScore, job=f"{job['title']}: {job['description'][:600]}", proposal=proposal)
    return s.overall if s else None


def export():
    from agent.graphs.bid_graph import build_bid_graph
    from agent.graphs.runtime import get_checkpointer
    quiet_marketplace()
    graph, jobs, items = build_bid_graph(get_checkpointer()), load_jobs(), []
    for p in PERSONAS:
        for r in [r for r in load_dev(p) if r["gold"]["bid"]][:12]:
            state, _ = run_job(graph, p, r["job_id"], f"judge-{p}")
            if state.get("cover_letter"):
                items.append({"job_id": r["job_id"], "persona": p, "job": jobs[r["job_id"]]["title"], "proposal": state["cover_letter"], "human": None})
    items = items[:30]
    ITEMS.write_text(json.dumps(items, indent=1))
    print(f"wrote {len(items)} items to {ITEMS}; add your own 1-5 score in 'human'")


def kappa(a: list[int], b: list[int]) -> float:
    n, cats = len(a), sorted(set(a) | set(b))
    if n == 0:
        raise SystemExit('no judge scores returned; check the LLM profile and rate limits')
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def main():
    items, jobs = json.loads(ITEMS.read_text()), load_jobs()
    if any(i["human"] is None for i in items) or not llm.enabled():
        sys.exit("Label every item's 'human' score and set an LLM profile first.")
    bin_ = lambda x: 0 if x < 2.5 else 1 if x < 3.5 else 2  # noqa: E731
    rows = [{**i, "judge": judge(jobs[i["job_id"]], i["proposal"])} for i in items]
    rows = [r for r in rows if r["judge"] is not None]
    save("judge_calibration", {"n": len(rows), "cohens_kappa": kappa([bin_(r["human"]) for r in rows], [bin_(r["judge"]) for r in rows]),
                               "disagreements": [r for r in rows if bin_(r["human"]) != bin_(r["judge"])]})


if __name__ == "__main__":
    export() if "--export" in sys.argv else main()
