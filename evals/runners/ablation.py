"""R&D question B: ablate the combined pipeline one component at a time.

  python -m evals.runners.ablation      -> evals/results/ablation.json
"""
from dataclasses import replace

from evals.common import PERSONAS, load_dev, load_jobs, save
from evals.runners.rag_eval import agg, evaluate
from rag.retriever import get_retriever


def main() -> dict:
    full, jobs = get_retriever("v10_combined"), load_jobs()
    configs = {"full": full}
    for switch in ("decompose", "hybrid", "rerank", "outcome", "collapse"):
        configs[f"without_{switch}"] = replace(full, **{switch: False})
    out = {}
    for name, pipeline in configs.items():
        rows = [r for p in PERSONAS for r in evaluate(pipeline, p, load_dev(p), jobs)]
        out[name] = agg(rows)
        print(f"{name:20s} recall@5={out[name]['recall@5']:.3f} ndcg@10={out[name]['ndcg@10']:.3f}")
    base = out["full"]["recall@5"]
    for name in out:
        out[name]["recall@5_delta_vs_full"] = round(out[name]["recall@5"] - base, 4)
    return out


if __name__ == "__main__":
    save("ablation", {"ablation": main()})
