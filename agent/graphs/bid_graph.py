"""Bid graph (C1): one thread per job. Hand-written StateGraph.

  scout -> [analyst | risk | matcher]  (parallel, via Send)  -> decide
        -> pricing -> writer -> verifier -> critic --(issues, max 2)--> revise -> writer
        -> compliance -> preview -> approval (interrupt) -> submit -> learn

Stops early at: skipped, watching, blocked, rejected, needs_attention, dead_letter.
Nothing reaches the marketplace before the human approves (R4).
"""
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

from agent.config import cfg
from agent.mcp_client import call_tool
from agent.memory import promotion_rules as rules
from agent.memory.store import get_store
from agent.nodes.analyst import analyst
from agent.nodes.base import halted, node, over_budget
from agent.nodes.compliance import compliance
from agent.nodes.critic import critic, revise
from agent.nodes.matcher import matcher
from agent.nodes.pricing import decide, pricing
from agent.nodes.risk import risk
from agent.nodes.scout import scout
from agent.nodes.verifier import verifier
from agent.nodes.writer import writer
from agent.state import BidState


# ---- routers ----------------------------------------------------------------
def fan_out(state):
    """Run the three analyses in parallel. A known duplicate skips straight to the decision."""
    if halted(state):
        return END
    if state.get("duplicate_of"):
        return "decide"
    return [Send("analyst", state), Send("risk", state), Send("matcher", state)]


def then(next_node: str):
    """Go to next_node unless the thread has stopped or blown its step/token budget (C4)."""
    def route(state):
        if halted(state):
            return END
        return "attention" if over_budget(state, cfg()["budgets"]) else next_node
    return route


def after_critic(state):
    if halted(state):
        return END
    if over_budget(state, cfg()["budgets"]):
        return "attention"
    last = state["critiques"][-1]
    if not last["approved"] and state.get("revisions", 0) < cfg()["budgets"]["max_revisions"]:
        return "revise"   # back to the Writer, at most max_revisions times
    return "compliance"


def after_approval(state):
    action = state["approval"].get("action")
    if action == "approve" and state["compliance"]["allowed"]:
        return "submit"
    if action == "edit":
        return "verifier"     # edited text is re-verified, then re-checked by Compliance
    if action == "reject":
        return "learn"
    return "approval"         # e.g. "approve" while Compliance still blocks: ask again


# ---- nodes that belong to the graph itself ------------------------------------
@node("attention")
def attention(state):
    return {"status": "needs_attention", "status_reason": over_budget(state, cfg()["budgets"])}


@node("preview")
def preview(state):
    """dry_run of both writes: exactly what would be sent and what it costs. No side effects."""
    user, job, price = state["user_id"], state["job"], state["price_quote"]
    answers = [a["answer"] for a in state["draft"].get("screening_answers", [])]
    draft = call_tool("submit", "create_proposal_draft", {"user_id": user, "job_id": job["id"], "cover_letter": state["cover_letter"],
                                                          "bid_usd": price["amount_usd"], "screening_answers": answers,
                                                          "idempotency_key": f"{user}:{job['id']}:draft", "dry_run": True})
    spend = call_tool("submit", "submit_proposal", {"user_id": user, "draft_id": "preview", "connects_cost": price["connects_cost"],
                                                    "idempotency_key": f"{user}:{job['id']}:submit", "dry_run": True})
    return {"preview": {"would_send": draft["preview"], "connects_cost": price["connects_cost"], "balance_after": spend["balance_after"]},
            "status": "awaiting_approval"}


def approval(state):
    """Human in the loop (C5). Not wrapped by @node: interrupt() must propagate.
    Code before interrupt() re-runs on resume, so it only reads state."""
    decision = interrupt({
        "kind": "proposal", "job_id": state["job"]["id"], "job_title": state["job"]["title"],
        "cover_letter": state["cover_letter"], "screening_answers": state["draft"].get("screening_answers", []),
        "claims": state.get("claim_checks", []), "evidence": state.get("evidence", []),
        "risk_report": state["risk_report"], "price_quote": state["price_quote"], "preview": state["preview"],
        "critiques": state.get("critiques", []), "compliance": state["compliance"],
    })
    action = decision.get("action")
    out = {"approval": decision, "steps": 1, "log": [f"approval:{action}"]}
    if action == "edit":
        before, after = state["cover_letter"], decision.get("text", "")
        out["cover_letter"] = after
        if not decision.get("regenerated"):  # only the human's own edits feed style memory
            out["edits"] = [{"before": before, "after": after, "diff": rules.diff_text(before, after)}]
    if action == "reject":
        out.update(status="rejected", status_reason=decision.get("reason", "rejected by user"))
    return out


@node("submit")
def submit(state):
    """Create the draft, then submit it. Idempotency keys are derived from user + job, so a crash
    and restart between or after these calls can never submit or spend Connects twice (C6)."""
    user, job, price = state["user_id"], state["job"], state["price_quote"]
    answers = [a["answer"] for a in state["draft"].get("screening_answers", [])]
    draft = call_tool("submit", "create_proposal_draft", {"user_id": user, "job_id": job["id"], "cover_letter": state["cover_letter"],
                                                          "bid_usd": price["amount_usd"], "screening_answers": answers,
                                                          "idempotency_key": f"{user}:{job['id']}:draft"})
    result = call_tool("submit", "submit_proposal", {"user_id": user, "draft_id": draft["id"], "connects_cost": price["connects_cost"],
                                                     "idempotency_key": f"{user}:{job['id']}:submit"})
    if result["status"] == "rejected":
        return {"submission": result, "status": "needs_attention", "status_reason": result.get("detail") or "marketplace rejected the proposal"}
    return {"submission": result, "status": "submitted"}


@node("learn")
def learn(state):
    """Promotion step: user edits become style-memory candidates (see agent/memory/promotion_rules.py)."""
    promoted = []
    for e in state.get("edits", []):
        promoted += rules.learn_from_edit(get_store(), state["user_id"], e["before"], e["after"])
    return {"log": [f"promoted:{p}" for p in promoted]}


def build_bid_graph(checkpointer=None, store=None):
    g = StateGraph(BidState)
    for name, fn in [("scout", scout), ("analyst", analyst), ("risk", risk), ("matcher", matcher), ("decide", decide),
                     ("pricing", pricing), ("writer", writer), ("verifier", verifier), ("critic", critic), ("revise", revise),
                     ("compliance", compliance), ("preview", preview), ("approval", approval), ("submit", submit),
                     ("learn", learn), ("attention", attention)]:
        g.add_node(name, fn)
    g.add_edge(START, "scout")
    g.add_conditional_edges("scout", fan_out, ["analyst", "risk", "matcher", "decide", END])
    for branch in ("analyst", "risk", "matcher"):
        g.add_edge(branch, "decide")           # decide waits for all three branches
    g.add_conditional_edges("decide", lambda s: "pricing" if s.get("status") == "drafting" else END, ["pricing", END])
    g.add_conditional_edges("pricing", then("writer"), ["writer", "attention", END])
    g.add_conditional_edges("writer", then("verifier"), ["verifier", "attention", END])
    g.add_conditional_edges("verifier", then("critic"), ["critic", "attention", END])
    g.add_conditional_edges("critic", after_critic, ["revise", "compliance", "attention", END])
    g.add_edge("revise", "writer")
    g.add_conditional_edges("compliance", then("preview"), ["preview", "attention", END])
    g.add_conditional_edges("preview", then("approval"), ["approval", "attention", END])
    g.add_conditional_edges("approval", after_approval, ["submit", "verifier", "learn", "approval"])
    g.add_edge("submit", "learn")
    g.add_edge("learn", END)
    g.add_edge("attention", END)
    # only a real LangGraph store is handed to compile(); the dev file store is used via get_store()
    return g.compile(checkpointer=checkpointer, store=store if hasattr(store, "batch") else None)
