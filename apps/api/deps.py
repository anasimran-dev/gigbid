"""Shared FastAPI dependency: the signed-in user (tenant)."""
from fastapi import Header, HTTPException, Query

from apps.api.auth import users


def current_user(authorization: str = Header(""), token: str = Query("")) -> str:
    """Bearer token in the header; EventSource cannot set headers, so SSE passes ?token=."""
    uid = users.verify(authorization.removeprefix("Bearer ").strip() or token)
    if not uid:
        raise HTTPException(401, "not signed in")
    return uid
