"""Single-process deployment: the API under /api and the built web app (apps/web/dist) at /.

  uvicorn apps.api.serve:root --host 0.0.0.0 --port $PORT
"""
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

from apps.api import db
from apps.api.auth import users
from apps.api.main import app as api

DIST = Path(__file__).resolve().parents[1] / "web" / "dist"


class SPA(StaticFiles):
    """Serve index.html for client-side routes such as /inbox or /studio/123."""

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as e:
            if e.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


root = FastAPI(title="GigBid")


@root.on_event("startup")
def startup():
    db.init()
    users.ensure_reviewer()


root.mount("/api", api)
if DIST.exists():
    root.mount("/", SPA(directory=DIST, html=True), name="web")
