"""Proposal studio data and the pipeline board."""
from fastapi import APIRouter, Depends, HTTPException

from apps.api import db, service
from apps.api.deps import current_user
from apps.api.schemas.models import Started

router = APIRouter(tags=["proposals"])


@router.get("/proposals/{job_id}")
def studio(job_id: str, user: str = Depends(current_user)) -> dict:
    """Draft, claims with evidence, critic and compliance comments, and the pending dry-run preview."""
    job = db.get(user, "job", job_id)
    if not job:
        raise HTTPException(404, "job not found")
    approval = db.get(user, "approval", service.bid_thread(user, job_id))
    return {"job": job, "approval": approval}


@router.post("/proposals/{job_id}/regenerate/{index}", response_model=Started)
def regenerate(job_id: str, index: int, user: str = Depends(current_user)):
    try:
        return Started(**service.regenerate_paragraph(user, job_id, index))
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))


@router.get("/pipeline")
def pipeline(user: str = Depends(current_user)) -> dict:
    """Kanban columns; cards move when marketplace events arrive (POST /messages/sync or the worker)."""
    cards = db.list_(user, "pipeline")
    return {"stages": service.STAGES, "cards": cards}
