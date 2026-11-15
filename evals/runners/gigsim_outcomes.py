"""B4 outcome metric: GigSim simulated reply and hire rate on a FIXED job set, per RAG variant.

  python -m evals.runners.gigsim_outcomes [--limit N]   -> evals/results/gigsim_outcomes.json

Fixed set: the first N gold-bid jobs of each persona (default 40). For each variant the graph
drafts a proposal, an automatic "approve" stands in for the human, and the simulated client decides.
Also records unsupported claims, latency and cost per proposal for the results table.
"""
import sys

from langgraph.types import Command

from agent.config import cfg
from agent.graphs.bid_graph import build_bid_graph
from agent.graphs.runtime import get_checkpointer, thread_config
from evals.common import PERSONAS, load_dev, mean, percentile, quiet_marketplace, run_job, save
from rag.retriever import VARIANTS


def run_variant(variant: str, n: int, strategy: str = "") -> dict:
    cfg()["rag"]["variant"] = variant
    sim = quiet_marketplace()
    graph = build_bid_graph(get_checkpointer())
    stages, seconds, unsupported, usd, per_persona = [], [], [], [], {}
    for p in PERSONAS:
        mine = []
        for r in [r for r in load_dev(p) if r["gold"]["bid"]][:n]:
            user = f"out-{variant}-{strategy}-{p}"
            sim.s["connects"][user] = 10 ** 6  # the outcome run is not limited by Connects
            state, secs = run_job(graph, p, r["job_id"], user, {"weekly_connects_remaining": 10 ** 6, "strategy": strategy})
            if state.get("status") != "awaiting_approval":
                mine.append("not_bid")
                continue
            final = graph.invoke(Command(resume={"action": "approve"}), thread_config(f"{user}:{r['job_id']}"))
            stage = sim.s["proposals"][final["submission"]["id"]]["outcome"]["stage"]
            mine.append(stage)
            seconds.append(secs)
            unsupported.append(state["claim_stats"]["unsupported_after"])
            usd.append(final.get("usd", 0.0))
        per_persona[p] = rates(mine)
        stages += mine
    return {**rates(stages), "by_persona": per_persona, "unsupported_claims_per_proposal": mean(unsupported),
            "p95_latency_s": percentile(seconds, 0.95), "usd_per_proposal": mean(usd)}


def rates(stages: list[str]) -> dict:
    n = len(stages)
    replied = sum(s in ("replied", "interview", "hired") for s in stages)
    return {"n_jobs": n, "proposals_sent": sum(s != "not_bid" for s in stages), "replied": replied,
            "reply_rate": round(replied / n, 3) if n else 0.0, "hire_rate": round(sum(s == "hired" for s in stages) / n, 3) if n else 0.0}


def main(n: int = 40) -> dict:
    shipped, out = cfg()["rag"]["variant"], {}
    for v in VARIANTS:
        out[v] = run_variant(v, n)
        print(f"{v:16s} reply_rate={out[v]['reply_rate']:.3f} hire_rate={out[v]['hire_rate']:.3f} sent={out[v]['proposals_sent']}")
    cfg()["rag"]["variant"] = shipped
    return out


if __name__ == "__main__":
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 40
    save("gigsim_outcomes_smoke" if lim < 40 else "gigsim_outcomes", {"fixed_jobs_per_persona": lim, "variants": main(lim)})
