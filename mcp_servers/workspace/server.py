"""Workspace MCP server (A3): calendar slots, tentative interview holds, email drafts.

Backed by a LOCAL MOCK (a JSON file), which the brief allows. Agents only ever see MCP tools,
so swapping in Google Calendar / Gmail later changes this file only.
"""
import json
from datetime import date, datetime, timedelta
from typing import Annotated, Any

from pydantic import BaseModel, Field

from agent.config import DATA
from mcp_servers.common import READ, WRITE_DRAFT, IdempotencyStore, MCPServer, audit, main_entry

mcp = MCPServer("gigbid-workspace", instructions="Calendar and email drafts for the freelancer. "
                "Holds are tentative and emails are drafts; nothing is sent to anyone.")
idem = IdempotencyStore("workspace")
STATE = DATA / "workspace.json"
HOURS = [10, 14, 16]  # local working slots, Asia/Karachi

User = Annotated[str, Field(min_length=1, max_length=64)]
Key = Annotated[str, Field(min_length=8, max_length=128)]


class WorkspaceResult(BaseModel):
    status: str
    dry_run: bool = False
    id: str = ""
    preview: dict[str, Any] = Field(default_factory=dict)
    idempotent_replay: bool = False


def _load() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {"holds": [], "drafts": []}


def _save(state: dict):
    DATA.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1))


@mcp.tool(annotations=READ)
def free_slots(user_id: User, start_date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD")],
               days: Annotated[int, Field(ge=1, le=14)] = 5, trace_id: str = "") -> dict[str, Any]:
    """List free 30-minute interview slots on weekdays, excluding existing holds."""
    taken = {h["slot"] for h in _load()["holds"] if h["user"] == user_id}
    day, slots = date.fromisoformat(start_date), []
    for _ in range(days):
        if day.weekday() < 5:
            slots += [s for s in (datetime(day.year, day.month, day.day, h).isoformat() for h in HOURS) if s not in taken]
        day += timedelta(days=1)
    audit("workspace", user_id, "free_slots", {"start_date": start_date, "days": days}, {"n": len(slots)}, trace_id)
    return {"timezone": "Asia/Karachi", "slots": slots}


def _write(tool: str, user: str, key: str, trace_id: str, dry_run: bool, preview: dict, apply) -> WorkspaceResult:
    if dry_run:
        return WorkspaceResult(status="dry_run", dry_run=True, preview=preview)
    stored = idem.get(f"{user}:{tool}:{key}")
    if stored:
        return WorkspaceResult(**{**stored, "idempotent_replay": True})
    state = _load()
    result = WorkspaceResult(status="created", id=apply(state), preview=preview)
    _save(state)
    idem.put(f"{user}:{tool}:{key}", result.model_dump())
    audit("workspace", user, tool, preview, result.model_dump(), trace_id)
    return result


@mcp.tool(annotations=WRITE_DRAFT)
def create_interview_hold(user_id: User, slot: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")],
                          title: Annotated[str, Field(min_length=3, max_length=120)], idempotency_key: Key,
                          dry_run: bool = False, trace_id: str = "") -> WorkspaceResult:
    """Place a TENTATIVE hold on the calendar for an interview. Idempotent per key."""
    def apply(state):
        hold_id = f"hold-{len(state['holds']) + 1:03d}"
        state["holds"].append({"id": hold_id, "user": user_id, "slot": slot, "title": title, "status": "tentative"})
        return hold_id
    return _write("create_interview_hold", user_id, idempotency_key, trace_id, dry_run, {"slot": slot, "title": title}, apply)


@mcp.tool(annotations=WRITE_DRAFT)
def create_email_draft(user_id: User, subject: Annotated[str, Field(min_length=1, max_length=200)],
                       body: Annotated[str, Field(min_length=1, max_length=5000)], idempotency_key: Key,
                       to: Annotated[str, Field(max_length=200)] = "", dry_run: bool = False, trace_id: str = "") -> WorkspaceResult:
    """Create an email DRAFT (never sends). Idempotent per key."""
    def apply(state):
        draft_id = f"email-{len(state['drafts']) + 1:03d}"
        state["drafts"].append({"id": draft_id, "user": user_id, "to": to, "subject": subject, "body": body})
        return draft_id
    return _write("create_email_draft", user_id, idempotency_key, trace_id, dry_run, {"to": to, "subject": subject, "body": body}, apply)


def main():
    main_entry(mcp, "WORKSPACE_MCP_PORT", 9003)


if __name__ == "__main__":
    main()
