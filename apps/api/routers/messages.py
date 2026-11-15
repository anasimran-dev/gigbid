"""Client threads with suggested replies and interview slots."""
from fastapi import APIRouter, Depends

from apps.api import db, service
from apps.api.deps import current_user

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("")
def threads(user: str = Depends(current_user)) -> list[dict]:
    out = []
    for t in db.list_(user, "thread"):
        out.append({**t, "approval": db.get(user, "approval", service.conv_thread(user, t["id"]))})
    return out


@router.post("/sync")
def sync(user: str = Depends(current_user)) -> dict:
    """Pull marketplace events and new client messages now (the worker also does this on a schedule)."""
    return service.sync_marketplace(user)
