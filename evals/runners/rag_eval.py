"""B4 retrieval metrics for every RAG variant, per persona and per job type.

  python -m evals.runners.rag_eval [--limit N]

Gold = the projects that prove the job's requirements. Retrieved items are collapsed to projects
(the same project is described by a case study, a README, reviews and proposals).
Metrics: Recall@5, MRR, nDCG@10. Writes evals/results/rag_eval.json.
"""
import sys

from agent.config import cfg
from agent.nodes.analyst import heuristic_spec
from evals.common import PERSONAS, load_dev, load_jobs, mean, mrr, ndcg_at, recall_at, save
from rag.retriever import VARIANTS, get_retriever, to_projects


def evaluate(pipeline, persona: str, rows: list[dict], jobs: dict) -> list[dict]:
    out = []
    for r in rows:
        gold = set(r["gold"]["relevant_projects"])
        if not gold:
            continue  # jobs this persona has no evidence for are scored by decision_eval (skip accuracy)
        job = jobs[r["job_id"]]
        spec = heuristic_spec(job).model_dump()
        ranked = to_projects(pipeline.retrieve(persona, job, spec, k=20, cfg=cfg()))
        out.append({"kind": r["kind"], "many_reqs": r["n_requirements"] >= 4, "recall@5": recall_at(ranked, gold, 5),
                    "mrr": mrr(ranked, gold), "ndcg@10": ndcg_at(ranked, gold, 10)})
    return out


def agg(rows: list[dict]) -> dict:
    return {"n": len(rows), **{m: mean(r[m] for r in rows) for m in ("recall@5", "mrr", "ndcg@10")}}


def main(limit: int | None = None, variants: list[str] | None = None) -> dict:
    jobs, results = load_jobs(), {}
    for v in variants or VARIANTS:
        per_persona, everything = {}, []
        for p in PERSONAS:
            rows = evaluate(get_retriever(v), p, load_dev(p, limit), jobs)
            per_persona[p] = agg(rows)
            everything += rows
        results[v] = {"overall": agg(everything), "by_persona": per_persona,
                      "by_job_type": {k: agg([r for r in everything if r["kind"] == k]) for k in ("normal", "multi", "vague", "injection")},
                      "four_plus_requirements": agg([r for r in everything if r["many_reqs"]])}
        print(f"{v:16s} recall@5={results[v]['overall']['recall@5']:.3f} mrr={results[v]['overall']['mrr']:.3f} "
              f"ndcg@10={results[v]['overall']['ndcg@10']:.3f}")
    return results


if __name__ == "__main__":
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    save("rag_eval_smoke" if lim else "rag_eval", {"variants": main(lim)})
