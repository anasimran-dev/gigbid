"""Shared plumbing for the three MCP servers: SDK import, audit log, rate limiter,
idempotency store, bearer-token HTTP serving and an in-memory client for tests."""
import json
import os
import time
from pathlib import Path

try:  # MCP Python SDK 2.x
    from mcp.server.mcpserver import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:  # MCP Python SDK 1.x (same decorators, older name)
    from mcp.server.fastmcp import FastMCP as MCPServer  # noqa: F401
    from mcp.server.fastmcp.exceptions import ToolError  # noqa: F401
from mcp.types import ToolAnnotations  # noqa: F401

from agent.config import DATA
from agent.guardrails import mask_obj

READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
WRITE_DRAFT = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True)
WRITE_SPEND = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True)


def audit(server: str, user: str, tool: str, arguments: dict, result, trace_id: str):
    """Append-only audit log: user, tool, arguments, result, trace id. PII is masked."""
    DATA.mkdir(parents=True, exist_ok=True)
    line = {"ts": round(time.time(), 3), "server": server, "user": user, "tool": tool,
            "arguments": mask_obj(arguments), "result": mask_obj(result if isinstance(result, dict) else {"value": str(result)[:300]}),
            "trace_id": trace_id}
    with open(DATA / "audit.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(line, default=str)[:4000] + "\n")


class RateLimiter:
    """Sliding one-minute window per user. Keeps us under the marketplace's own limit."""

    def __init__(self, per_minute: int):
        self.per_minute, self.calls = per_minute, {}

    def check(self, user: str):
        now = time.time()
        window = [t for t in self.calls.get(user, []) if now - t < 60]
        if len(window) >= self.per_minute:
            raise ToolError("rate_limited: too many marketplace calls this minute, retry later")
        self.calls[user] = window + [now]


class IdempotencyStore:
    """key -> stored result, on disk, so a retried write returns the first result and never runs twice."""

    def __init__(self, name: str):
        self.path = DATA / f"idempotency_{name}.json"

    def _load(self) -> dict:
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def get(self, key: str):
        return self._load().get(key)

    def put(self, key: str, result: dict):
        data = self._load()
        data[key] = result
        DATA.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data))


def serve(mcp, port: int):
    """Streamable HTTP with bearer-token auth (MCP_BEARER_TOKEN)."""
    import uvicorn
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    token = os.getenv("MCP_BEARER_TOKEN", "dev-mcp-token")

    class Bearer(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.url.path != "/health" and request.headers.get("authorization") != f"Bearer {token}":
                return JSONResponse({"error": "unauthorized"}, status_code=401)
            return await call_next(request)

    try:  # inside Docker the Host header is the service name, so relax DNS-rebinding checks
        from mcp.server.transport_security import TransportSecuritySettings
        app = mcp.streamable_http_app(transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))
    except Exception:
        app = mcp.streamable_http_app()
    app.add_middleware(Bearer)
    uvicorn.run(app, host="0.0.0.0", port=port)


async def call_in_memory(mcp, tool: str, arguments: dict) -> dict:
    """Call a tool through a real in-memory MCP client session (used by tests and inprocess mode).
    Returns the structured result, or raises RuntimeError with the tool's error text."""
    try:
        from mcp.client import Client
        async with Client(mcp) as client:
            res = await client.call_tool(tool, arguments)
    except ImportError:
        from mcp.shared.memory import create_connected_server_and_client_session as connect
        async with connect(mcp._mcp_server) as session:
            res = await session.call_tool(tool, arguments)
    is_error = getattr(res, "is_error", None) if hasattr(res, "is_error") else getattr(res, "isError", False)
    structured = getattr(res, "structured_content", None) or getattr(res, "structuredContent", None)
    if is_error:
        raise RuntimeError(res.content[0].text if res.content else "tool error")
    if structured is None and res.content:
        structured = json.loads(res.content[0].text)
    return structured if not (isinstance(structured, dict) and set(structured) == {"result"}) else structured["result"]


def main_entry(mcp, port_env: str, default_port: int):
    """`python -m mcp_servers.<name>.server` -> stdio (Claude Desktop, Cursor); `--http` -> HTTP."""
    import sys
    if "--http" in sys.argv:
        serve(mcp, int(os.getenv(port_env, default_port)))
    else:
        mcp.run()


ROOT = Path(__file__).resolve().parents[1]
