"""B4 decision metrics + cost and speed, by running the real bid graph on the dev set.

  python -m evals.runners.decision_eval [--limit N]   -> evals/results/decision_eval.json

Reports per persona: bid-or-skip F1, scam precision/recall, injection flag recall, price inside
the fair band, unsupported claims per proposal (before and after verification), p50/p95 latency,
tokens and USD per job analysed and per proposal.
"""
import sys

from agent.graphs.bid_graph import build_bid_graph
from agent.graphs.runtime import get_checkpointer
from evals.common import PERSONAS, load_dev, mean, percentile, prf, quiet_marketplace, run_job, save


def main(limit: int | None = None) -> dict:
    quiet_marketplace()
    graph, out, failures = build_bid_graph(get_checkpointer()), {}, []
    for p in PERSONAS:
        bid = scam = {"tp": 0, "fp": 0, "fn": 0}
        bid, scam = dict(bid), dict(scam)
        in_band = priced = inj_seen = inj_flagged = 0
        job_s, prop_s, tokens, usd, before, after = [], [], [], [], [], []
        for r in load_dev(p, limit):
            state, seconds = run_job(graph, p, r["job_id"], f"eval-{p}")
            gold, said_bid = r["gold"], state.get("status") == "awaiting_approval"
            risk = state.get("risk_report") or {}
            for name, pred, truth in (("bid", said_bid, gold["bid"]), ("scam", risk.get("scam", False), gold["scam"])):
                tally = bid if name == "bid" else scam
                tally["tp"] += pred and truth
                tally["fp"] += pred and not truth
                tally["fn"] += (not pred) and truth
            if gold["injection"]:
                inj_seen += 1
                inj_flagged += risk.get("injection", False)
            job_s.append(seconds)
            tokens.append(state.get("tokens", 0))
            usd.append(state.get("usd", 0.0))
            if said_bid:
                prop_s.append(seconds)
                before.append(state["claim_stats"]["unsupported_before"])
                after.append(state["claim_stats"]["unsupported_after"])
                if gold["bid"]:
                    priced += 1
                    lo, hi = gold["fair_price_band"]
                    in_band += lo <= state["price_quote"]["amount_usd"] <= hi
            if said_bid != gold["bid"] or risk.get("scam", False) != gold["scam"]:
                failures.append({"persona": p, "job_id": r["job_id"], "kind": r["kind"], "gold_bid": gold["bid"], "said_bid": said_bid,
                                 "gold_scam": gold["scam"], "said_scam": risk.get("scam", False), "status": state.get("status"),
                                 "reason": state.get("status_reason", "")[:200]})
        out[p] = {"n_jobs": len(job_s), "bid_or_skip": prf(**bid), "scam_detection": prf(**scam),
                  "injection_flag_recall": round(inj_flagged / inj_seen, 3) if inj_seen else None,
                  "price_in_fair_band": round(in_band / priced, 3) if priced else None, "n_proposals": len(prop_s),
                  "unsupported_claims_per_proposal_before": mean(before), "unsupported_claims_per_proposal_after": mean(after),
                  "latency_s_per_job": {"p50": percentile(job_s, 0.5), "p95": percentile(job_s, 0.95)},
                  "latency_s_per_proposal": {"p50": percentile(prop_s, 0.5), "p95": percentile(prop_s, 0.95)},
                  "tokens_per_job": mean(tokens), "usd_per_job": mean(usd)}
        print(p, out[p]["bid_or_skip"], out[p]["scam_detection"], "price_in_band", out[p]["price_in_fair_band"])
    return {"personas": out, "failures": failures}


if __name__ == "__main__":
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    save("decision_eval_smoke" if lim else "decision_eval", main(lim))
