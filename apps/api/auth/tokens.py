"""Encrypted OAuth token store (A4, E4). Tokens are encrypted with Fernet before they touch the
database, scoped per user, and never logged (agent/guardrails.mask_obj also redacts any key
containing 'token')."""
import json
import os

from cryptography.fernet import Fernet

from apps.api import db


def _fernet() -> Fernet:
    key = os.getenv("TOKEN_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is not set (generate one with: make fernet-key)")
    return Fernet(key.encode())


def save_token(user: str, provider: str, token: dict):
    db.put(user, "oauth", provider, {"ciphertext": _fernet().encrypt(json.dumps(token).encode()).decode()})


def load_token(user: str, provider: str) -> dict | None:
    doc = db.get(user, "oauth", provider)
    return json.loads(_fernet().decrypt(doc["ciphertext"].encode())) if doc else None


def delete_token(user: str, provider: str):
    db.delete(user, "oauth", provider)
