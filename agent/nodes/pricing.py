"""Decision + Pricing Strategist.

decide : skip / watch / bid from the three parallel reports (pure rules, thresholds in config).
pricing: propose a bid from market statistics, the client's budget and the user's floor, and
         decide whether the Connects cost is worth it. MCP: marketplace (read).
"""
from agent.config import cfg
from agent.handoffs import BidDecision, PriceQuote
from agent.mcp_client import call_tool
from agent.nodes.base import node


def decide_action(spec: dict, risk: dict, fit: dict, settings: dict, duplicate_of: str = "") -> BidDecision:
    t = cfg()["thresholds"]
    floor = settings.get("min_project_usd", 0)
    if duplicate_of:
        return BidDecision(action="skip", reasons=[f"Duplicate of {duplicate_of}"])
    if risk["scam"] or risk["score"] >= t["max_risk"]:
        return BidDecision(action="skip", reasons=["Risk too high: " + ", ".join(risk["flags"])])
    if 0 < spec.get("budget_max", 0) < floor:
        return BidDecision(action="skip", reasons=[f"Budget ${spec['budget_max']:.0f} is below your floor ${floor:.0f}"])
    if fit["score"] >= t["bid_fit"]:
        return BidDecision(action="bid", reasons=fit["reasons"] + [f"Fit {fit['score']:.2f} >= {t['bid_fit']}"])
    if fit["score"] >= t["watch_fit"]:
        return BidDecision(action="watch", reasons=fit["reasons"] + [f"Fit {fit['score']:.2f} is borderline; missing: {', '.join(fit['missing']) or 'unclear'}"])
    return BidDecision(action="skip", reasons=fit["reasons"] + [f"Fit {fit['score']:.2f} < {t['watch_fit']}"])


@node("decide")
def decide(state):
    if state.get("status") in ("needs_attention", "dead_letter"):
        return {}
    spec = state.get("job_spec") or {"budget_max": state["job"].get("budget", {}).get("max", 0)}
    risk = state.get("risk_report") or {"scam": False, "score": 0.0, "flags": []}
    fit = state.get("fit_report") or {"score": 0.0, "reasons": [], "missing": []}
    d = decide_action(spec, risk, fit, state.get("settings", {}), state.get("duplicate_of", ""))
    status = {"skip": "skipped", "watch": "watching", "bid": "drafting"}[d.action]
    return {"decision": d.model_dump(), "status": status, "status_reason": "; ".join(d.reasons)}


def quote(job: dict, spec: dict, stats: dict, balance: int, settings: dict, fit: float, client_quality: float) -> PriceQuote:
    policy = cfg()["policy"]
    floor = settings.get("min_project_usd", 0)
    budget_max = spec.get("budget_max") or 0
    base = stats.get("median") or budget_max or floor or 100
    amount = max(floor, min(base, budget_max * 1.05) if budget_max else base)
    amount = max(10.0, round(amount, -1))
    cost = job.get("connects_cost", 0) + policy["extra_connects_fee"]
    remaining = settings.get("weekly_connects_remaining", policy["weekly_connects_budget"])
    expected_usd = amount * 0.15 * fit * client_quality          # rough chance of winning x value
    worth = cost <= policy["max_connects_per_job"] and cost <= min(balance, remaining) and expected_usd >= cost * policy["connect_usd"]
    why = (f"Market median for similar jobs is ${stats.get('median', 0):.0f} (n={stats.get('n', 0)}, matched on {stats.get('matched_on', 'n/a')}); "
           f"client budget up to ${budget_max:.0f}; your floor ${floor:.0f}. "
           f"Connects: {cost} (weekly remaining {remaining}, balance {balance}); expected value ${expected_usd:.0f}.")
    return PriceQuote(amount_usd=amount, low_usd=stats.get("p25", amount), high_usd=stats.get("p75", amount),
                      connects_cost=cost, connects_worth_it=worth, rationale=why)


@node("pricing")
def pricing(state):
    job, spec = state["job"], state["job_spec"]
    stats = call_tool("pricing", "get_market_stats", {"user_id": state["user_id"], "category": spec.get("category") or "other",
                                                      "skills": spec.get("required_skills", [])[:20]})
    balance = call_tool("pricing", "get_connects_balance", {"user_id": state["user_id"]})["balance"]
    q = quote(job, spec, stats, balance, state.get("settings", {}), state["fit_report"]["score"], state["risk_report"]["client_quality"])
    out = {"price_quote": q.model_dump()}
    if not q.connects_worth_it:
        out.update(status="watching", status_reason=f"Connects cost {q.connects_cost} is not worth it or exceeds your budget")
    return out
