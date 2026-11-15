"""MCP client for the agents (A6: client discipline).

  call_tool("pricing", "get_market_stats", {...})

* Per-agent allowlist: an agent can only call tools listed for it in config.yaml.
* Timeouts and bounded retries with backoff; rate-limit errors are retried, validation errors are not.
* Degraded mode: when the marketplace server is unreachable, ToolUnavailable is raised, the
  status is remembered (status()), the UI shows a banner and the worker re-queues the job.

Transports (mcp.transport in config.yaml):
  inprocess : a real MCP client session over in-memory streams to the server object (dev, tests, evals)
  http      : MultiServerMCPClient (langchain-mcp-adapters) over Streamable HTTP with bearer auth (Docker)
"""
import asyncio
import importlib
import os
import time

from agent import tracing
from agent.config import cfg

SERVER_OF = {
    "search_evidence": "portfolio", "get_case_study": "portfolio", "list_skills": "portfolio",
    "free_slots": "workspace", "create_interview_hold": "workspace", "create_email_draft": "workspace",
    "get_file_contents": "github",
}  # everything else lives on the marketplace server
_status = {"marketplace": {"ok": True, "error": "", "since": 0.0}}
_killed: set[str] = set()  # servers switched off for the degraded-mode demo and tests


class ToolNotAllowed(Exception):
    pass


class ToolUnavailable(Exception):
    """The server could not be reached after retries (degraded mode)."""


def status() -> dict:
    return _status["marketplace"]


def kill(server: str, dead: bool = True):
    """Simulate a dead server (viva question 1). The next successful call clears the status."""
    (_killed.add if dead else _killed.discard)(server)


def _inprocess(server: str, tool: str, args: dict):
    from mcp_servers.common import call_in_memory
    if server in _killed:
        raise ConnectionError(f"{server} MCP server is not reachable")
    module = importlib.import_module(f"mcp_servers.{server}.server")
    return asyncio.run(call_in_memory(module.mcp, tool, args))


def _http(server: str, tool: str, args: dict):
    from langchain_mcp_adapters.client import MultiServerMCPClient
    token = os.getenv("GITHUB_TOKEN", "") if server == "github" else os.getenv("MCP_BEARER_TOKEN", "dev-mcp-token")

    async def run():
        client = MultiServerMCPClient({server: {"url": cfg()["mcp"]["servers"][server], "transport": "streamable_http",
                                                "headers": {"Authorization": f"Bearer {token}"}}})
        tools = [t for t in await client.get_tools() if t.name == tool]  # filtered by name
        if not tools:
            raise ConnectionError(f"tool {tool} not offered by {server}")
        return await asyncio.wait_for(tools[0].ainvoke(args), cfg()["marketplace"]["timeout_seconds"])
    out = asyncio.run(run())
    if isinstance(out, str):
        import json
        try:
            return json.loads(out)
        except ValueError:
            return out
    return out


def call_tool(agent: str, tool: str, args: dict, server: str | None = None):
    if tool not in cfg()["tool_allowlists"].get(agent, []):
        raise ToolNotAllowed(f"agent '{agent}' may not call '{tool}'")
    server = server or SERVER_OF.get(tool, "marketplace")
    m = cfg()["marketplace"]
    args = {**args, "trace_id": tracing.current_trace()} if server != "github" else args
    run = _inprocess if cfg()["mcp"]["transport"] == "inprocess" else _http
    last = None
    for attempt in range(m["retries"] + 1):
        start = time.time()
        try:
            result = run(server, tool, args)
            tracing.event("tool", tool, agent=agent, server=server, arguments=args,
                          result=result if isinstance(result, dict) else str(result)[:300], seconds=round(time.time() - start, 3))
            if server == "marketplace":
                _status["marketplace"] = {"ok": True, "error": "", "since": 0.0}
            return result
        except Exception as e:
            last = e
            text = str(e)
            retryable = isinstance(e, (ConnectionError, TimeoutError, OSError)) or "rate_limited" in text or "marketplace_unavailable" in text
            tracing.event("tool_error", tool, agent=agent, server=server, error=text[:300], attempt=attempt)
            if not retryable:
                raise
            time.sleep(m["backoff_seconds"] * (2 ** attempt))
    if server == "marketplace":
        _status["marketplace"] = {"ok": False, "error": str(last)[:200], "since": time.time()}
    raise ToolUnavailable(f"{server}.{tool} unavailable: {last}")
