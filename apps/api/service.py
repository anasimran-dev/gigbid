"""Application service: everything the routers and the worker do, with no web framework in it.

It drives the two LangGraph graphs, mirrors their state into tenant-scoped documents the UI
reads, stores pending approvals, and resumes interrupted threads.
"""
import collections
import os
import threading
import time
import uuid

from langgraph.types import Command

from agent import mcp_client, tracing
from agent.config import cfg
from agent.graphs.bid_graph import build_bid_graph
from agent.graphs.conversation_graph import build_conversation_graph
from agent.graphs.runtime import get_checkpointer, thread_config
from agent.mcp_client import ToolUnavailable, call_tool
from agent.memory import promotion_rules as rules
from agent.memory.store import get_store
from agent.nodes.scout import fingerprint, run_saved_searches
from apps.api import db
from apps.api.auth.users import default_settings

_graphs: dict = {}
STAGES = ["drafted", "submitted", "viewed", "replied", "interview", "hired", "lost"]


def graphs() -> dict:
    if not _graphs:
        saver, store = get_checkpointer(), get_store()
        _graphs["bid"] = build_bid_graph(saver, store)
        _graphs["conversation"] = build_conversation_graph(saver, store)
    return _graphs


def bid_thread(user: str, job_id: str) -> str:
    return f"{user}:{job_id}"


def conv_thread(user: str, thread_id: str) -> str:
    return f"{user}:conv:{thread_id}"


# ---- settings -----------------------------------------------------------------
def get_settings(user: str) -> dict:
    return {**default_settings("ai_ml_engineer"), **(db.get(user, "settings", "settings") or {})}


def runtime_settings(user: str) -> dict:
    """Settings plus facts the graph needs: reposts seen so far and Connects left this week."""
    s = get_settings(user)
    week_ago = time.time() - 7 * 86400
    spent = sum(p.get("connects", 0) for p in db.list_(user, "pipeline") if p.get("submitted_at", 0) > week_ago)
    known = {j["fingerprint"]: j["id"] for j in db.list_(user, "job") if j.get("fingerprint")}
    return {**s, "weekly_connects_remaining": max(0, s["weekly_connects_budget"] - spent), "known_fingerprints": known}


# ---- runs and streaming events --------------------------------------------------
def new_run(user: str, kind: str, thread_id: str, subject: str) -> dict:
    run = {"id": uuid.uuid4().hex[:12], "kind": kind, "thread_id": thread_id, "subject": subject,
           "trace_id": tracing.new_trace_id(), "status": "running", "started": time.time(), "events": []}
    db.put(user, "run", run["id"], run)
    return run


def publish(user: str, run_id: str, node: str, data: dict, status: str | None = None):
    """Append one event to the run. The SSE endpoint (apps/api/streaming.py) tails these."""
    run = db.get(user, "run", run_id)
    run["events"].append({"ts": round(time.time(), 3), "node": node, **data})
    if status:
        run["status"] = status
    db.put(user, "run", run_id, run)


def summarise(update: dict) -> dict:
    """Small, UI-friendly view of a node's state update (full detail is in the trace)."""
    out = {"status": update.get("status", ""), "reason": update.get("status_reason", "")}
    if "decision" in update:
        out["detail"] = f"decision: {update['decision']['action']}"
    elif "fit_report" in update:
        out["detail"] = f"fit {update['fit_report']['score']:.2f}, {len(update.get('evidence', []))} evidence items"
    elif "risk_report" in update:
        out["detail"] = f"risk {update['risk_report']['score']:.2f} {update['risk_report']['flags']}"
    elif "job_spec" in update:
        out["detail"] = f"skills: {', '.join(update['job_spec']['required_skills'][:6])}"
    elif "price_quote" in update:
        out["detail"] = f"bid ${update['price_quote']['amount_usd']:.0f}, {update['price_quote']['connects_cost']} Connects"
    elif "claim_stats" in update:
        out["detail"] = f"{update['claim_stats']['claims']} claims, {update['claim_stats']['unsupported_before']} unsupported removed"
    elif "critiques" in update:
        c = update["critiques"][-1]
        out["detail"] = "approved by critic" if c["approved"] else "sent back: " + "; ".join(c["issues"])
    elif "compliance" in update:
        out["detail"] = "allowed" if update["compliance"]["allowed"] else "blocked: " + "; ".join(update["compliance"]["violations"])
    elif "intent" in update:
        out["detail"] = f"intent: {update['intent']['intent']}"
    elif "submission" in update or "sent" in update:
        out["detail"] = (update.get("submission") or update.get("sent")).get("status", "")
    return out


def drive(user: str, kind: str, thread_id: str, run_id: str, payload):
    """Run or resume one graph thread, publishing every node update, then mirror the state."""
    graph, run = graphs()[kind], db.get(user, "run", run_id)
    tracing.set_trace(run["trace_id"])
    config, interrupted = thread_config(thread_id, run["trace_id"]), None
    try:
        for chunk in graph.stream(payload, config, stream_mode="updates"):
            for node, update in chunk.items():
                if node == "__interrupt__":
                    interrupted = update[0].value
                    publish(user, run_id, "approval", {"detail": "waiting for your approval", "status": "awaiting_approval"})
                else:
                    publish(user, run_id, node, summarise(update or {}))
    except Exception as e:  # noqa: BLE001
        publish(user, run_id, "error", {"detail": str(e)[:300]}, status="error")
        return
    values = graph.get_state(config).values
    (_mirror_bid if kind == "bid" else _mirror_conversation)(user, thread_id, run, values, interrupted)
    publish(user, run_id, "end", {"detail": values.get("status", ""), "status": values.get("status", "")},
            status="waiting_approval" if interrupted else "done")


def _mirror_bid(user: str, thread_id: str, run: dict, v: dict, interrupted):
    job = v.get("job", {})
    status = v.get("status", "")
    if status == "needs_attention" and "unavailable" in v.get("status_reason", "").lower():
        status = "queued"  # marketplace down: the worker retries when it is back
    db.update(user, "job", job["id"], **{k: v.get(k) for k in ("job_spec", "risk_report", "fit_report", "evidence", "decision",
              "price_quote", "cover_letter", "claim_checks", "claim_stats", "critiques", "compliance", "submission", "draft")},
              status=status, status_reason=v.get("status_reason", ""), fingerprint=job.get("fingerprint"), duplicate_of=v.get("duplicate_of"),
              run_id=run["id"], trace_id=run["trace_id"], tokens=v.get("tokens", 0), usd=v.get("usd", 0.0), revisions=v.get("revisions", 0))
    if interrupted:
        db.put(user, "approval", thread_id, {"id": thread_id, "kind": "proposal", "job_id": job["id"], "run_id": run["id"],
                                             "payload": interrupted, "created": time.time()})
    else:
        db.delete(user, "approval", thread_id)
    base = {"job_id": job["id"], "title": job.get("title", ""), "category": job.get("category", ""),
            "bid_usd": (v.get("price_quote") or {}).get("amount_usd"), "strategy": (v.get("draft") or {}).get("strategy", "")}
    if status == "awaiting_approval":
        db.update(user, "pipeline", job["id"], **base, stage="drafted")
    if status == "submitted":
        sub = v["submission"]
        db.update(user, "pipeline", job["id"], **base, stage="submitted", proposal_id=sub["id"], connects=sub["connects_cost"],
                  submitted_at=time.time())
    if status == "rejected":
        db.delete(user, "pipeline", job["id"])
        db.update(user, "job", job["id"], rejection_reason=v.get("status_reason", ""))


def _mirror_conversation(user: str, thread_id: str, run: dict, v: dict, interrupted):
    tid = v.get("thread_id", "")
    db.update(user, "thread", tid, id=tid, thread=v.get("thread"), intent=v.get("intent"), reply=v.get("reply"),
              status=v.get("status", ""), status_reason=v.get("status_reason", ""), run_id=run["id"], trace_id=run["trace_id"],
              handled=len((v.get("thread") or {}).get("messages", [])))
    if interrupted:
        db.put(user, "approval", thread_id, {"id": thread_id, "kind": "message", "thread_id": tid, "run_id": run["id"],
                                             "payload": interrupted, "created": time.time()})
    else:
        db.delete(user, "approval", thread_id)


# ---- background execution -------------------------------------------------------
def launch(task: str, *args):
    """Long runs never execute inside a web request (E1).
    REDIS_URL set -> queued for the Arq worker; otherwise a background thread (local dev);
    GIGBID_SYNC=1 -> inline (tests)."""
    if os.getenv("GIGBID_SYNC") == "1":
        TASKS[task](*args)
    elif os.getenv("REDIS_URL"):
        import asyncio

        from worker.main import enqueue
        asyncio.run(enqueue(task, *args))
    else:
        threading.Thread(target=TASKS[task], args=args, daemon=True).start()


def task_bid(user: str, job_id: str, run_id: str):
    """Idempotent: a job already past analysis is not analysed again after a worker restart."""
    state = graphs()["bid"].get_state(thread_config(bid_thread(user, job_id)))
    if "approval" in state.next:
        return  # already drafted and waiting for the human
    if state.next:  # a checkpoint exists mid-run: continue from it instead of starting over
        return drive(user, "bid", bid_thread(user, job_id), run_id, None)
    job = db.get(user, "job", job_id) or {"id": job_id}
    s = get_settings(user)
    drive(user, "bid", bid_thread(user, job_id), run_id,
          {"user_id": user, "persona": s["persona"], "trace_id": db.get(user, "run", run_id)["trace_id"],
           "settings": runtime_settings(user), "job": job.get("job") or {"id": job_id}})


def task_conversation(user: str, thread_id: str, run_id: str):
    s = get_settings(user)
    drive(user, "conversation", conv_thread(user, thread_id), run_id,
          {"user_id": user, "persona": s["persona"], "trace_id": db.get(user, "run", run_id)["trace_id"], "thread_id": thread_id,
           "settings": runtime_settings(user), "steps": None, "tokens": None})


def task_resume(user: str, kind: str, thread_id: str, run_id: str, decision: dict):
    """Resume after an approval. Safe to run twice: if the interrupt was already answered, the thread
    just continues from its last checkpoint, and marketplace writes are idempotent."""
    state = graphs()[kind].get_state(thread_config(thread_id))
    if "approval" in state.next:
        drive(user, kind, thread_id, run_id, Command(resume=decision))
    elif state.next:
        drive(user, kind, thread_id, run_id, None)


TASKS = {"bid": task_bid, "conversation": task_conversation, "resume": task_resume}


# ---- use cases ------------------------------------------------------------------
def scout(user: str, limit: int = 10) -> dict:
    """Pull new jobs from saved searches and start a bid run for each (or queue them if degraded)."""
    seen = {j["id"] for j in db.list_(user, "job")}
    try:
        jobs = run_saved_searches(user, get_settings(user)["saved_searches"], seen)[:limit]
    except ToolUnavailable as e:
        return {"new": 0, "degraded": True, "error": str(e)}
    for job in jobs:
        db.put(user, "job", job["id"], {"id": job["id"], "job": job, "status": "new", "fingerprint": fingerprint(job), "found_at": time.time()})
        start_bid(user, job["id"])
    return {"new": len(jobs), "degraded": False}


def start_bid(user: str, job_id: str) -> dict:
    run = new_run(user, "bid", bid_thread(user, job_id), job_id)
    db.update(user, "job", job_id, id=job_id, status="analysing", run_id=run["id"])
    launch("bid", user, job_id, run["id"])
    return run


def retry_queued(user: str) -> int:
    """Recover from degraded mode: re-run jobs that were queued while the marketplace was down."""
    queued = [j for j in db.list_(user, "job") if j.get("status") == "queued"]
    for j in queued:
        start_bid(user, j["id"])
    return len(queued)


def resolve_approval(user: str, thread_id: str, decision: dict) -> dict:
    approval = db.get(user, "approval", thread_id)
    if not approval:
        raise KeyError("no pending approval for this thread")
    kind = "bid" if approval["kind"] == "proposal" else "conversation"
    launch("resume", user, kind, thread_id, approval["run_id"], decision)
    return {"run_id": approval["run_id"], "kind": kind}


def regenerate_paragraph(user: str, job_id: str, index: int) -> dict:
    """Rewrite one paragraph from the next-best unused evidence item, then re-check it like an edit."""
    from agent.nodes.writer import article, result_sentence
    job = db.get(user, "job", job_id)
    paragraphs = job["cover_letter"].split("\n\n")
    used = job["cover_letter"]
    spare = [e for e in job.get("evidence", []) if e.get("project") and e["title"] not in used and result_sentence(e)]
    if not spare or not 0 <= index < len(paragraphs):
        raise ValueError("no unused evidence to rewrite this paragraph from")
    e = spare[0]
    ind = e.get("industry") or "past"
    paragraphs[index] = f"On {e['title']} for {article(ind)} {ind} client I used {', '.join(e['skills'][:3])} and {result_sentence(e)}."
    return resolve_approval(user, bid_thread(user, job_id), {"action": "edit", "text": "\n\n".join(paragraphs), "regenerated": True})


def sync_marketplace(user: str) -> dict:
    """Pipeline board + conversations. Marketplace events move cards; final outcomes feed outcome
    memory through the promotion rule; new client messages start a conversation run."""
    try:
        events = call_tool("board", "list_events", {"user_id": user})["events"]
        threads = call_tool("liaison", "list_messages", {"user_id": user})["threads"]
    except ToolUnavailable as e:
        return {"degraded": True, "error": str(e)}
    best: dict[str, str] = {}
    for e in events:
        if STAGES.index(e["stage"]) > STAGES.index(best.get(e["job_id"], "drafted")):
            best[e["job_id"]] = e["stage"]
    for job_id, stage in best.items():
        card = db.get(user, "pipeline", job_id)
        if card:
            if not card.get("outcome_recorded"):
                rules.record_outcome(get_store(), user, card.get("category", ""), card.get("strategy", ""), stage)
            db.update(user, "pipeline", job_id, stage=stage, outcome_recorded=True)
    started = 0
    for t in threads:
        doc = db.get(user, "thread", t["id"]) or {}
        if t["messages"][-1]["from"] == "client" and doc.get("handled", 0) < len(t["messages"]) \
                and not db.get(user, "approval", conv_thread(user, t["id"])):
            db.update(user, "thread", t["id"], id=t["id"], thread=t, handled=len(t["messages"]), status="drafting")
            run = new_run(user, "conversation", conv_thread(user, t["id"]), t["id"])
            launch("conversation", user, t["id"], run["id"])
            started += 1
        else:
            db.update(user, "thread", t["id"], id=t["id"], thread=t)
    return {"degraded": False, "cards": len(best), "conversations_started": started}


def analytics(user: str) -> dict:
    cards, jobs = db.list_(user, "pipeline"), db.list_(user, "job")
    by_cat: dict[str, dict] = {}
    for c in cards:
        if c.get("stage") == "drafted":
            continue
        row = by_cat.setdefault(c.get("category") or "other", {"sent": 0, "replied": 0, "hired": 0, "connects": 0})
        row["sent"] += 1
        row["replied"] += c["stage"] in ("replied", "interview", "hired")
        row["hired"] += c["stage"] == "hired"
        row["connects"] += c.get("connects", 0)
    for row in by_cat.values():
        row["reply_rate"] = round(row["replied"] / row["sent"], 2)
        row["hire_rate"] = round(row["hired"] / row["sent"], 2)
    proposals = [tracing.summarise(j["trace_id"]) for j in jobs if j.get("submission") and j.get("trace_id")]
    seconds = sorted(p["total_seconds"] for p in proposals)
    reasons = collections.Counter(j["rejection_reason"] for j in jobs if j.get("rejection_reason"))
    skips = collections.Counter((j.get("decision") or {}).get("action", "pending") for j in jobs)
    return {"by_category": by_cat, "connects_spent": sum(c.get("connects", 0) for c in cards),
            "proposals_sent": sum(r["sent"] for r in by_cat.values()), "decisions": dict(skips),
            "cost_per_proposal_usd": round(sum(p["total_usd"] for p in proposals) / len(proposals), 5) if proposals else 0,
            "latency_p50_s": seconds[len(seconds) // 2] if seconds else 0,
            "latency_p95_s": seconds[min(len(seconds) - 1, int(len(seconds) * 0.95))] if seconds else 0,
            "top_rejection_reasons": reasons.most_common(5), "declared_budgets": cfg()["budgets"]}


def memory_view(user: str) -> dict:
    store = get_store()
    return {"style": [{"key": i.key, **i.value} for i in store.search(("style", user))],
            "outcomes": [{"key": i.key, **i.value} for i in store.search(("outcomes", user))]}


def memory_delete(user: str, namespace: str, key: str):
    if namespace not in ("style", "outcomes"):
        raise ValueError("unknown memory namespace")
    get_store().delete((namespace, user), key)
    get_store().delete(("candidates", user), key if namespace == "style" else f"outcome:{key}")


def health() -> dict:
    return {"marketplace": mcp_client.status(), "mode": cfg()["marketplace"]["mode"], "profile": cfg()["profile"]}
