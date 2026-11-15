"""Application storage: one tenant-scoped document table.

Every read and write takes the tenant (user id) first, and every SQL statement filters on it,
so one user's data can never be returned to another (E4: scope each user's data by tenant).

DATABASE_URL=postgres...  -> Postgres (Docker, deployment)
otherwise                 -> SQLite file in data/processed (local dev, tests)
"""
import json
import os
import sqlite3
import time

from agent.config import DATA

SCHEMA = """CREATE TABLE IF NOT EXISTS docs (
  tenant TEXT NOT NULL, kind TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL, updated REAL NOT NULL,
  PRIMARY KEY (tenant, kind, id))"""


def _pg() -> bool:
    return os.getenv("DATABASE_URL", "").startswith("postgres")


def _run(sql: str, params: tuple = (), fetch: bool = False):
    if _pg():
        import psycopg
        with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
            cur = conn.execute(sql.replace("?", "%s"), params)
            return cur.fetchall() if fetch else None
    DATA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(os.getenv("APP_DB", str(DATA / "app.db")), timeout=30)
    try:
        cur = conn.execute(sql, params)
        rows = cur.fetchall() if fetch else None
        conn.commit()
        return rows
    finally:
        conn.close()


def init():
    _run(SCHEMA)


def put(tenant: str, kind: str, id: str, data: dict):
    _run("INSERT INTO docs (tenant, kind, id, data, updated) VALUES (?, ?, ?, ?, ?) "
         "ON CONFLICT (tenant, kind, id) DO UPDATE SET data = excluded.data, updated = excluded.updated",
         (tenant, kind, id, json.dumps(data, default=str), time.time()))


def get(tenant: str, kind: str, id: str) -> dict | None:
    rows = _run("SELECT data FROM docs WHERE tenant = ? AND kind = ? AND id = ?", (tenant, kind, id), fetch=True)
    return json.loads(rows[0][0]) if rows else None


def list_(tenant: str, kind: str) -> list[dict]:
    rows = _run("SELECT data FROM docs WHERE tenant = ? AND kind = ? ORDER BY updated DESC", (tenant, kind), fetch=True)
    return [json.loads(r[0]) for r in rows]


def delete(tenant: str, kind: str, id: str):
    _run("DELETE FROM docs WHERE tenant = ? AND kind = ? AND id = ?", (tenant, kind, id))


def update(tenant: str, kind: str, doc_id: str, /, **changes) -> dict:
    doc = {**(get(tenant, kind, doc_id) or {}), **changes}
    put(tenant, kind, doc_id, doc)
    return doc


def tenants() -> list[str]:
    return [r[0] for r in _run("SELECT DISTINCT tenant FROM docs WHERE kind = 'settings'", fetch=True)]
