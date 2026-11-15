"""Conversation graph (C1): one thread per client conversation.

  read -> classify -> draft_reply -> reply_compliance -> preview -> approval (interrupt) -> send

Client messages are untrusted data. A scam signal still gets a safe, on-platform reply drafted,
but it is flagged and nothing is sent without approval.
"""
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from agent.config import cfg
from agent.mcp_client import call_tool
from agent.memory import promotion_rules as rules
from agent.nodes.base import halted, node, over_budget
from agent.nodes.liaison import classify, draft_reply, read, reply_compliance, send
from agent.state import ConversationState


def then(next_node: str):
    def route(state):
        if halted(state):
            return END
        return "attention" if over_budget(state, cfg()["budgets"]) else next_node
    return route


@node("attention")
def attention(state):
    return {"status": "needs_attention", "status_reason": over_budget(state, cfg()["budgets"])}


@node("preview")
def preview(state):
    r = call_tool("liaison", "send_message", {"user_id": state["user_id"], "thread_id": state["thread_id"], "text": state["reply"]["text"],
                                              "idempotency_key": f"{state['user_id']}:{state['thread_id']}:preview", "dry_run": True})
    return {"preview": {"would_send": r["preview"], "interview_hold": state["reply"].get("slots", [])[:1]}, "status": "awaiting_approval"}


def approval(state):
    decision = interrupt({"kind": "message", "thread_id": state["thread_id"], "client_message": state["last_client_message"],
                          "intent": state["intent"], "reply": state["reply"], "preview": state["preview"],
                          "compliance": state["compliance"]})
    action = decision.get("action")
    out = {"approval": decision, "steps": 1, "log": [f"approval:{action}"]}
    if action == "edit":
        before, after = state["reply"]["text"], decision.get("text", "")
        out.update(reply={**state["reply"], "text": after}, edits=[{"before": before, "after": after, "diff": rules.diff_text(before, after)}])
    if action == "reject":
        out.update(status="rejected", status_reason=decision.get("reason", "rejected by user"))
    return out


def after_approval(state):
    action = state["approval"].get("action")
    if action == "approve" and state["compliance"]["allowed"]:
        return "send"
    if action == "edit":
        return "reply_compliance"
    return END if action == "reject" else "approval"


def build_conversation_graph(checkpointer=None, store=None):
    g = StateGraph(ConversationState)
    for name, fn in [("read", read), ("classify", classify), ("draft_reply", draft_reply), ("reply_compliance", reply_compliance),
                     ("preview", preview), ("approval", approval), ("send", send), ("attention", attention)]:
        g.add_node(name, fn)
    g.add_edge(START, "read")
    g.add_conditional_edges("read", then("classify"), ["classify", "attention", END])
    g.add_conditional_edges("classify", then("draft_reply"), ["draft_reply", "attention", END])
    g.add_conditional_edges("draft_reply", then("reply_compliance"), ["reply_compliance", "attention", END])
    g.add_conditional_edges("reply_compliance", then("preview"), ["preview", "attention", END])
    g.add_conditional_edges("preview", then("approval"), ["approval", "attention", END])
    g.add_conditional_edges("approval", after_approval, ["send", "reply_compliance", "approval", END])
    g.add_edge("send", END)
    g.add_edge("attention", END)
    # only a real LangGraph store is handed to compile(); the dev file store is used via get_store()
    return g.compile(checkpointer=checkpointer, store=store if hasattr(store, "batch") else None)
