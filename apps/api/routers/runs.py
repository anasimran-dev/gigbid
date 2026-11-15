"""Agent run viewer: node-by-node progress streamed over SSE, plus the full trace."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from agent import tracing
from apps.api import db
from apps.api.deps import current_user
from apps.api.schemas.models import RunInfo
from apps.api.streaming import sse_events

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=list[RunInfo])
def runs(user: str = Depends(current_user)):
    return db.list_(user, "run")[:50]


@router.get("/{run_id}", response_model=RunInfo)
def run(run_id: str, user: str = Depends(current_user)):
    doc = db.get(user, "run", run_id)
    if not doc:
        raise HTTPException(404, "run not found")
    return doc


@router.get("/{run_id}/stream")
def stream(run_id: str, user: str = Depends(current_user)):
    if not db.get(user, "run", run_id):
        raise HTTPException(404, "run not found")
    return StreamingResponse(sse_events(user, run_id), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/{run_id}/trace")
def trace(run_id: str, user: str = Depends(current_user)) -> dict:
    """Full execution trace (tool names, arguments, results; PII masked) and per-node tokens and cost."""
    doc = db.get(user, "run", run_id)
    if not doc:
        raise HTTPException(404, "run not found")
    return {"summary": tracing.summarise(doc["trace_id"]), "events": tracing.read_trace(doc["trace_id"])}
