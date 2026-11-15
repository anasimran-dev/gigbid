"""GigBid API.  Run: uvicorn apps.api.main:app --port 8000"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api import db, service
from apps.api.auth import users
from apps.api.routers import analytics, approvals, auth, jobs, messages, proposals, runs, settings
from apps.api.schemas.models import Health

app = FastAPI(title="GigBid API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("WEB_ORIGIN", "http://localhost:5173").split(","),
                   allow_methods=["*"], allow_headers=["*"])
for r in (auth, jobs, proposals, approvals, messages, runs, analytics, settings):
    app.include_router(r.router)


@app.on_event("startup")
def startup():
    db.init()
    users.ensure_reviewer()


@app.get("/health", response_model=Health, tags=["health"])
def health():
    """Also drives the UI's 'marketplace unavailable' banner."""
    return Health(**service.health())
