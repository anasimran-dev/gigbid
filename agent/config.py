"""Load agent/config.yaml once. A few values can be overridden from the environment."""
import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"


@lru_cache(maxsize=1)
def cfg() -> dict:
    c = yaml.safe_load((ROOT / "agent" / "config.yaml").read_text(encoding="utf-8"))
    c["profile"] = os.getenv("MODEL_PROFILE", c["profile"])
    c["marketplace"]["mode"] = os.getenv("MARKETPLACE_MODE", c["marketplace"]["mode"])
    c["rag"]["variant"] = os.getenv("RAG_VARIANT", c["rag"]["variant"])
    c["mcp"]["transport"] = os.getenv("MCP_TRANSPORT", c["mcp"]["transport"])
    return c


def reload() -> dict:
    cfg.cache_clear()
    return cfg()
