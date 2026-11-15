"""Node wrapper: sets the trace id, times the node, counts steps/tokens/cost, retries once,
and turns failures into a visible state instead of a crash (C7).

  marketplace down      -> status "needs_attention" (the worker re-queues the job)
  any other exception   -> one retry, then status "dead_letter"
"""
import functools
import time

from agent import llm, tracing
from agent.mcp_client import ToolUnavailable

HALT = {"needs_attention", "dead_letter", "blocked", "rejected", "skipped", "watching", "submitted", "sent"}


def node(name: str, retries: int = 1):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(state):
            tracing.set_trace(state.get("trace_id", ""))
            start, out = time.time(), None
            for attempt in range(retries + 1):
                try:
                    out = fn(state) or {}
                    break
                except ToolUnavailable as e:
                    out = {"status": "needs_attention", "status_reason": f"Marketplace unavailable: {e}", "errors": [f"{name}: {e}"]}
                    break
                except Exception as e:  # noqa: BLE001 - last line of defence for one node
                    tracing.event("node_error", name, node=name, error=str(e)[:300], attempt=attempt)
                    out = {"status": "dead_letter", "status_reason": f"{name} failed: {e}", "errors": [f"{name}: {e}"]}
            tokens, usd = llm.take_usage()
            tracing.event("node", name, node=name, seconds=round(time.time() - start, 4), wrote=sorted(out))
            return {**out, "steps": 1, "tokens": tokens, "usd": usd, "log": [name]}
        return wrapper
    return deco


def halted(state) -> bool:
    return state.get("status") in HALT


def over_budget(state, budgets: dict) -> str:
    if state.get("steps", 0) > budgets["max_graph_steps"]:
        return f"step budget exceeded ({state['steps']} > {budgets['max_graph_steps']})"
    if state.get("tokens", 0) > budgets["max_tokens_per_thread"]:
        return f"token budget exceeded ({state['tokens']} > {budgets['max_tokens_per_thread']})"
    return ""
