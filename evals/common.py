"""Shared helpers for the evaluation runners. Every runner writes JSON to evals/results/."""
import json
import math
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evals" / "results"
PERSONAS = ["ai_ml_engineer", "fullstack_dev", "data_analyst"]
FLOORS = {"ai_ml_engineer": 300, "fullstack_dev": 250, "data_analyst": 150}


def load_jobs() -> dict:
    return {j["id"]: j for j in json.loads((ROOT / "gigsim" / "seed" / "jobs.json").read_text())}


def load_dev(persona: str, limit: int | None = None) -> list[dict]:
    rows = json.loads((ROOT / "evals" / "datasets" / f"dev_{persona}.json").read_text())
    return rows[:limit] if limit else rows


def save(name: str, data: dict) -> Path:
    from agent.config import cfg
    RESULTS.mkdir(parents=True, exist_ok=True)
    meta = {"profile": cfg()["profile"], "embeddings": cfg()["embeddings"]["backend"], "reranker": cfg()["reranker"]["backend"],
            "data": "synthetic (scripts/generate_data.py, seed 4016)", "generated_at": time.strftime("%Y-%m-%d %H:%M")}
    path = RESULTS / f"{name}.json"
    path.write_text(json.dumps({"meta": meta, **data}, indent=1))
    print(f"wrote {path.relative_to(ROOT)}")
    return path


def recall_at(ranked: list[str], gold: set[str], k: int) -> float:
    return len(set(ranked[:k]) & gold) / len(gold)


def mrr(ranked: list[str], gold: set[str]) -> float:
    return next((1 / (i + 1) for i, r in enumerate(ranked) if r in gold), 0.0)


def ndcg_at(ranked: list[str], gold: set[str], k: int) -> float:
    dcg = sum(1 / math.log2(i + 2) for i, r in enumerate(ranked[:k]) if r in gold)
    ideal = sum(1 / math.log2(i + 2) for i in range(min(k, len(gold))))
    return dcg / ideal if ideal else 0.0


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0}


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return round(s[min(len(s) - 1, int(q * len(s)))], 4)


def mean(values) -> float:
    values = list(values)
    return round(sum(values) / len(values), 4) if values else 0.0


def quiet_marketplace():
    """Evaluations are not rate-limited and get a fresh simulator with no random errors."""
    import mcp_servers.marketplace.server as server
    from gigsim.core import reset_default
    server.limiter.per_minute = 10 ** 9
    return reset_default(rate_limit_per_min=10 ** 9, error_rate=0.0)


def run_job(graph, persona: str, job_id: str, user: str, extra_settings: dict | None = None) -> tuple[dict, float]:
    """Run the bid graph for one job until it stops or waits for approval. Returns (state, seconds)."""
    from agent import tracing
    from agent.graphs.runtime import thread_config
    trace = tracing.new_trace_id()
    start = time.time()
    graph.invoke({"user_id": user, "persona": persona, "trace_id": trace, "job": {"id": job_id},
                  "settings": {"min_project_usd": FLOORS[persona], **(extra_settings or {})}}, thread_config(f"{user}:{job_id}", trace))
    return graph.get_state(thread_config(f"{user}:{job_id}")).values, time.time() - start
