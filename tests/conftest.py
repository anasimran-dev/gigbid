"""Test setup: offline profile, in-process MCP, a fresh simulator and an isolated data folder per test."""
import os

import pytest

os.environ.update(MODEL_PROFILE="offline", MCP_TRANSPORT="inprocess", GIGBID_SYNC="1", MARKETPLACE_MODE="gigsim")


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    import agent.config as config
    import agent.memory.store as store
    import agent.tracing as tracing
    import mcp_servers.common as common
    import mcp_servers.marketplace.server as marketplace
    import mcp_servers.workspace.server as workspace
    from agent import mcp_client
    from gigsim.core import reset_default
    for mod in (config, common):
        monkeypatch.setattr(mod, "DATA", tmp_path)
    monkeypatch.setattr(tracing, "TRACE_DIR", tmp_path / "traces")
    monkeypatch.setattr(workspace, "STATE", tmp_path / "workspace.json")
    monkeypatch.setattr(marketplace, "idem", common.IdempotencyStore("marketplace"))
    monkeypatch.setattr(workspace, "idem", common.IdempotencyStore("workspace"))
    monkeypatch.setenv("APP_DB", str(tmp_path / "app.db"))
    marketplace.limiter.per_minute, marketplace.limiter.calls = 10 ** 9, {}
    store.set_store(store.FileStore(tmp_path / "memory.json"))
    mcp_client.kill("marketplace", False)
    yield reset_default(rate_limit_per_min=10 ** 9)


def call(server, tool, args):
    """Call a tool through a real in-memory MCP client session."""
    import asyncio

    from mcp_servers.common import call_in_memory
    return asyncio.run(call_in_memory(server, tool, args))
