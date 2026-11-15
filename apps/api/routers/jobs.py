"""Job inbox and job detail."""
from fastapi import APIRouter, Depends, HTTPException

from apps.api import db, service
from apps.api.deps import current_user
from apps.api.schemas.models import JobCard, Started

router = APIRouter(prefix="/jobs", tags=["jobs"])


def card(j: dict) -> JobCard:
    job, price = j.get("job") or {}, j.get("price_quote") or {}
    return JobCard(id=j["id"], title=job.get("title", ""), category=job.get("category", ""), status=j.get("status", ""),
                   action=(j.get("decision") or {}).get("action", ""), fit=(j.get("fit_report") or {}).get("score"),
                   risk_flags=(j.get("risk_report") or {}).get("flags", []), price_usd=price.get("amount_usd"),
                   connects_cost=price.get("connects_cost") or job.get("connects_cost"), reason=j.get("status_reason", ""))


@router.get("", response_model=list[JobCard])
def inbox(status: str = "", user: str = Depends(current_user)):
    """New jobs ranked by fit. With autonomy=auto_skip, skipped jobs are hidden (never auto-sent)."""
    hide = service.get_settings(user)["autonomy"] == "auto_skip"
    jobs = [j for j in db.list_(user, "job") if (not status or j.get("status") == status)
            and not (hide and not status and j.get("status") == "skipped") and j.get("status") != "dismissed"]
    return sorted((card(j) for j in jobs), key=lambda c: -(c.fit or 0))


@router.post("/scout")
def scout(user: str = Depends(current_user)) -> dict:
    return service.scout(user)


@router.get("/{job_id}")
def detail(job_id: str, user: str = Depends(current_user)) -> dict:
    job = db.get(user, "job", job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job


@router.post("/{job_id}/analyse", response_model=Started)
def analyse(job_id: str, user: str = Depends(current_user)):
    return Started(run_id=service.start_bid(user, job_id)["id"])


@router.post("/{job_id}/skip")
def skip(job_id: str, user: str = Depends(current_user)) -> dict:
    db.update(user, "job", job_id, status="dismissed")
    return {"ok": True}
