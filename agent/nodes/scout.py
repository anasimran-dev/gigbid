"""Scout: run saved searches on a schedule, de-duplicate, queue new jobs. MCP: marketplace (read)."""
import hashlib
import re

from agent.mcp_client import call_tool
from agent.nodes.base import node


def fingerprint(job: dict) -> str:
    """Same title + description + client = same job, even when it is reposted under a new id."""
    text = re.sub(r"\W+", " ", f"{job.get('title', '')} {job.get('description', '')} {job.get('client_id', '')}".lower()).strip()
    return hashlib.sha1(text.encode()).hexdigest()[:16]


def run_saved_searches(user_id: str, searches: list[str], seen_ids: set[str], limit: int = 20) -> list[dict]:
    """Used by the worker. Returns jobs not seen before (by id), newest first."""
    new, ids = [], set(seen_ids)
    for query in searches or [""]:
        for job in call_tool("scout", "search_jobs", {"user_id": user_id, "query": query, "limit": limit})["jobs"]:
            if job["id"] not in ids:
                ids.add(job["id"])
                new.append(job)
    return new


@node("scout")
def scout(state):
    """Graph entry: load the job if only an id was handed in, then check for reposts."""
    job = state["job"]
    if "description" not in job:
        job = call_tool("scout", "get_job", {"user_id": state["user_id"], "job_id": job["id"]})
    known = state.get("settings", {}).get("known_fingerprints", {})
    fp = fingerprint(job)
    out = {"job": {**job, "fingerprint": fp}, "status": "analysing"}
    if known.get(fp) not in (None, job["id"]):
        out["duplicate_of"] = known[fp]
    return out
