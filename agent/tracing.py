"""R8 / E3 observability. One trace id flows UI -> API -> graph -> MCP servers -> audit log.

Two sinks:
  * LangSmith, automatically, when LANGSMITH_TRACING=true and LANGSMITH_API_KEY are set
    (LangGraph traces itself; we add the trace id as run metadata in the graph config).
  * A local JSONL file per trace (data/processed/traces/<trace_id>.jsonl), always on,
    PII-masked. The Agent Run viewer and the cost/latency reports read these files.

This is the EXECUTION TRACE: every node, tool name, argument and result. It is separate
from graph state and from long-term memory (see docs/ARCHITECTURE.md).
"""
import contextvars
import json
import time
import uuid

from agent.config import DATA, cfg
from agent.guardrails import mask_obj

_trace_id = contextvars.ContextVar("trace_id", default="")
TRACE_DIR = DATA / "traces"


def new_trace_id() -> str:
    return uuid.uuid4().hex[:16]


def set_trace(trace_id: str):
    _trace_id.set(trace_id)


def current_trace() -> str:
    return _trace_id.get()


def event(kind: str, name: str, **data):
    """Append one masked event to the current trace file."""
    tid = current_trace()
    if not tid:
        return
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    with open(TRACE_DIR / f"{tid}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": round(time.time(), 3), "trace_id": tid, "kind": kind, "name": name, **mask_obj(data)}) + "\n")


def cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    price_in, price_out = cfg()["prices_usd_per_mtok"].get(model, [0.0, 0.0])
    return (tokens_in * price_in + tokens_out * price_out) / 1_000_000


def read_trace(trace_id: str) -> list[dict]:
    path = TRACE_DIR / f"{trace_id}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def summarise(trace_id: str) -> dict:
    """Tokens, cost and seconds per node for one trace."""
    nodes: dict[str, dict] = {}
    for e in read_trace(trace_id):
        if e["kind"] in ("node", "llm"):
            n = nodes.setdefault(e.get("node", e["name"]), {"seconds": 0.0, "tokens": 0, "usd": 0.0})
            n["seconds"] += e.get("seconds", 0.0) if e["kind"] == "node" else 0.0
            n["tokens"] += e.get("tokens_in", 0) + e.get("tokens_out", 0)
            n["usd"] += e.get("usd", 0.0)
    return {"trace_id": trace_id, "nodes": nodes,
            "total_seconds": round(sum(n["seconds"] for n in nodes.values()), 3),
            "total_tokens": sum(n["tokens"] for n in nodes.values()),
            "total_usd": round(sum(n["usd"] for n in nodes.values()), 6)}
