"""Human approval (R4). Approving here resumes the interrupted LangGraph thread.
Pending approvals are stored, so a page refresh or an API restart never loses one."""
from fastapi import APIRouter, Depends, HTTPException

from apps.api import db, service
from apps.api.deps import current_user
from apps.api.schemas.models import ApprovalDecision, Started

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("")
def pending(user: str = Depends(current_user)) -> list[dict]:
    return db.list_(user, "approval")


@router.post("/{thread_id:path}", response_model=Started)
def decide(thread_id: str, body: ApprovalDecision, user: str = Depends(current_user)):
    if not thread_id.startswith(user + ":"):
        raise HTTPException(403, "not your thread")
    try:
        return Started(**service.resolve_approval(user, thread_id, body.model_dump()))
    except KeyError as e:
        raise HTTPException(404, str(e))
