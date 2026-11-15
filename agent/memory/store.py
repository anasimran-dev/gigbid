"""Long-term memory store (R7). Namespaces, per user:

  ("style", user)        promoted writing rules learned from the user's edits
  ("outcomes", user)     promoted win/reply statistics per job category
  ("candidates", user)   observations that are NOT memory yet (counted until a rule promotes them)

With Postgres (DATABASE_URL) this is LangGraph's PostgresStore, the same object the graphs are
compiled with. Without Postgres (local dev, tests) it is a small JSON-file store with the same
put / get / search / delete interface, so memory still survives a restart.
"""
import json
import os
from types import SimpleNamespace

from agent.config import DATA


class FileStore:
    def __init__(self, path=None):
        self.path = path or DATA / "memory_store.json"

    def _load(self) -> dict:
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def _save(self, data: dict):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=1))

    def put(self, namespace: tuple, key: str, value: dict):
        data = self._load()
        data.setdefault("/".join(namespace), {})[key] = value
        self._save(data)

    def get(self, namespace: tuple, key: str):
        value = self._load().get("/".join(namespace), {}).get(key)
        return SimpleNamespace(key=key, value=value, namespace=namespace) if value is not None else None

    def search(self, namespace: tuple, **_):
        return [SimpleNamespace(key=k, value=v, namespace=namespace)
                for k, v in self._load().get("/".join(namespace), {}).items()]

    def delete(self, namespace: tuple, key: str):
        data = self._load()
        data.get("/".join(namespace), {}).pop(key, None)
        self._save(data)


_store = None


def get_store():
    global _store
    if _store is None:
        url = os.getenv("DATABASE_URL", "")
        if url.startswith("postgres"):
            import psycopg
            from langgraph.store.postgres import PostgresStore
            from psycopg.rows import dict_row
            _store = PostgresStore(psycopg.connect(url, autocommit=True, row_factory=dict_row))
            _store.setup()
        else:
            _store = FileStore()
    return _store


def set_store(store):
    global _store
    _store = store
