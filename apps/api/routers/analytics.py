"""Analytics: reply and hire rate by category, Connects versus outcomes, cost and latency."""
from fastapi import APIRouter, Depends

from apps.api import service
from apps.api.deps import current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("")
def analytics(user: str = Depends(current_user)) -> dict:
    return service.analytics(user)
