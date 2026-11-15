"""Multi-user auth: PBKDF2 password hashes, JWT sessions. The user id is the tenant id."""
import hashlib
import os
import re
import secrets
import time

import jwt

from apps.api import db

USERS = "_users"  # tenant that holds the user records themselves


def _secret() -> str:
    return os.getenv("APP_SECRET_KEY", "dev-secret-change-me-before-deploying-0123456789")


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()


def user_id_for(email: str) -> str:
    return "u_" + re.sub(r"[^a-z0-9]", "_", email.lower())[:40]


def register(email: str, password: str, persona: str = "ai_ml_engineer") -> str:
    uid = user_id_for(email)
    if db.get(USERS, "user", uid):
        raise ValueError("an account with this email already exists")
    salt = secrets.token_hex(8)
    db.put(USERS, "user", uid, {"id": uid, "email": email.lower(), "salt": salt, "hash": _hash(password, salt)})
    db.put(uid, "settings", "settings", default_settings(persona))
    return uid


def login(email: str, password: str) -> str | None:
    user = db.get(USERS, "user", user_id_for(email))
    if user and secrets.compare_digest(user["hash"], _hash(password, user["salt"])):
        return jwt.encode({"sub": user["id"], "exp": int(time.time()) + 7 * 86400}, _secret(), algorithm="HS256")
    return None


def verify(token: str) -> str | None:
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])["sub"]
    except jwt.PyJWTError:
        return None


def default_settings(persona: str) -> dict:
    rates = {"ai_ml_engineer": (45, 300), "fullstack_dev": (40, 250), "data_analyst": (30, 150)}.get(persona, (30, 150))
    return {"persona": persona, "onboarded": False, "marketplace": "gigsim", "hourly_rate_usd": rates[0],
            "min_project_usd": rates[1], "weekly_connects_budget": 60, "autonomy": "manual",
            "saved_searches": [""], "strategy": "", "categories": []}


def ensure_reviewer():
    """Reviewer login preloaded with a persona (E6). Credentials come from the environment only."""
    email, password = os.getenv("REVIEWER_EMAIL"), os.getenv("REVIEWER_PASSWORD")
    if email and password and not db.get(USERS, "user", user_id_for(email)):
        uid = register(email, password, os.getenv("REVIEWER_PERSONA", "ai_ml_engineer"))
        db.update(uid, "settings", "settings", onboarded=True)
