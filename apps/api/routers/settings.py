"""Settings: autonomy, budgets, saved searches, portfolio upload, and the memory viewer."""
from fastapi import APIRouter, Depends, HTTPException

from apps.api import db, service
from apps.api.deps import current_user
from apps.api.schemas.models import PortfolioUpload, Settings
from rag.ingest.loaders import add_upload
from rag.retriever import reindex

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=Settings)
def read(user: str = Depends(current_user)):
    return service.get_settings(user)


@router.put("/settings", response_model=Settings)
def write(body: Settings, user: str = Depends(current_user)):
    db.put(user, "settings", "settings", body.model_dump())
    return body


@router.post("/portfolio")
def upload(body: PortfolioUpload, user: str = Depends(current_user)) -> dict:
    """Add work to the portfolio; the index for that persona is rebuilt (incremental re-indexing)."""
    persona = service.get_settings(user)["persona"]
    item = add_upload(persona, body.title, body.text, body.type)
    reindex(persona)
    return {"id": item["id"], "skills": item["skills"]}


@router.get("/memory")
def memory(user: str = Depends(current_user)) -> dict:
    """Everything GigBid has learned about this user (style rules and outcome statistics)."""
    return service.memory_view(user)


@router.delete("/memory/{namespace}/{key}")
def forget(namespace: str, key: str, user: str = Depends(current_user)) -> dict:
    try:
        service.memory_delete(user, namespace, key)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"deleted": key}
