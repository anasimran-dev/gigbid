"""Sign-in, sign-up and connecting a marketplace account (Upwork OAuth 2.1 with PKCE)."""
import base64
import hashlib
import json
import os
import secrets
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException

from agent.config import cfg
from apps.api import db
from apps.api.auth import tokens, users
from apps.api.deps import current_user
from apps.api.schemas.models import Credentials, Token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token)
def register(body: Credentials):
    try:
        uid = users.register(body.email, body.password, body.persona)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return Token(access_token=users.login(body.email, body.password), user_id=uid)


@router.post("/login", response_model=Token)
def login(body: Credentials):
    token = users.login(body.email, body.password)
    if not token:
        raise HTTPException(401, "wrong email or password")
    return Token(access_token=token, user_id=users.user_id_for(body.email))


@router.get("/me")
def me(user: str = Depends(current_user)) -> dict:
    return {"user_id": user, "upwork_connected": db.get(user, "oauth", "upwork") is not None}


def _metadata() -> dict:
    """OAuth endpoints are discovered from the server, never hard-coded."""
    base = urllib.parse.urlsplit(cfg()["upwork"]["url"])
    with urllib.request.urlopen(f"{base.scheme}://{base.netloc}/.well-known/oauth-authorization-server", timeout=15) as res:
        return json.loads(res.read())


@router.get("/upwork/start")
def upwork_start(user: str = Depends(current_user)) -> dict:
    """Step 1: return the authorisation URL. The PKCE verifier is kept server-side for the callback."""
    verifier, state = secrets.token_urlsafe(48), secrets.token_urlsafe(16)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    db.put(user, "oauth_pending", state, {"verifier": verifier})
    query = urllib.parse.urlencode({"response_type": "code", "client_id": os.getenv("UPWORK_CLIENT_ID", ""),
                                    "redirect_uri": os.getenv("UPWORK_REDIRECT_URI", ""), "state": state,
                                    "code_challenge": challenge, "code_challenge_method": "S256"})
    return {"authorize_url": f"{_metadata()['authorization_endpoint']}?{query}"}


@router.get("/upwork/callback")
def upwork_callback(code: str, state: str, user: str = Depends(current_user)) -> dict:
    """Step 2: exchange the code for tokens and store them encrypted for this user."""
    pending = db.get(user, "oauth_pending", state)
    if not pending:
        raise HTTPException(400, "unknown OAuth state")
    body = urllib.parse.urlencode({"grant_type": "authorization_code", "code": code, "code_verifier": pending["verifier"],
                                   "client_id": os.getenv("UPWORK_CLIENT_ID", ""),
                                   "redirect_uri": os.getenv("UPWORK_REDIRECT_URI", "")}).encode()
    with urllib.request.urlopen(urllib.request.Request(_metadata()["token_endpoint"], body), timeout=15) as res:
        tokens.save_token(user, "upwork", json.loads(res.read()))
    db.delete(user, "oauth_pending", state)
    return {"connected": True}


@router.delete("/upwork")
def upwork_disconnect(user: str = Depends(current_user)) -> dict:
    tokens.delete_token(user, "upwork")
    return {"connected": False}
