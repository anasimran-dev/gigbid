"""Live Upwork adapter (A4). Same port as GigSim, backed by Upwork's official MCP server
(https://mcp.upwork.com/mcp, Streamable HTTP, OAuth 2.1) through MultiServerMCPClient.

STATUS: written from the assignment brief and NOT run against a real Upwork account.
Upwork's tool names are not hard-coded: they are mapped in agent/config.yaml (upwork.tool_map).
Before using live mode, list the server's tools once (make upwork-tools) and fix the map.

Rules enforced here:
  * no scraping, no browser automation, no session cookies: only the official MCP server
  * writes only ever create DRAFTS; the user confirms on Upwork (submit_proposal never submits)
  * reads are rate-limited by the Marketplace MCP server and the scout interval in RUNBOOK.md
"""
import asyncio

from agent.config import cfg
from agent.marketplace_port import MarketplaceUnavailable


class UpworkLiveAdapter:
    def __init__(self):
        self.map = cfg()["upwork"]["tool_map"]
        self.url = cfg()["upwork"]["url"]

    def _call(self, user: str, port_method: str, args: dict):
        from langchain_mcp_adapters.client import MultiServerMCPClient

        from apps.api.auth.tokens import load_token  # encrypted per-user OAuth token store
        token = load_token(user, "upwork")
        if not token:
            raise MarketplaceUnavailable("Upwork is not connected for this user. Connect it in Settings.")

        async def run():
            client = MultiServerMCPClient({"upwork": {"url": self.url, "transport": "streamable_http",
                                                      "headers": {"Authorization": f"Bearer {token['access_token']}"}}})
            tools = {t.name: t for t in await client.get_tools()}
            name = self.map[port_method]
            if name not in tools:
                raise MarketplaceUnavailable(f"Upwork tool '{name}' not found. Update upwork.tool_map in config.yaml.")
            return await asyncio.wait_for(tools[name].ainvoke(args), cfg()["marketplace"]["timeout_seconds"])
        try:
            return asyncio.run(run())
        except MarketplaceUnavailable:
            raise
        except Exception as e:
            raise MarketplaceUnavailable(f"Upwork call failed: {e}") from e

    def search_jobs(self, user, query, limit=20):
        return self._call(user, "search_jobs", {"query": query, "limit": limit})

    def get_job(self, user, job_id):
        return self._call(user, "get_job", {"job_id": job_id})

    def get_client_history(self, user, client_id):
        return self._call(user, "get_client_history", {"client_id": client_id})

    def get_connects_balance(self, user):
        return self._call(user, "get_connects_balance", {})

    def get_market_stats(self, user, category, skills):
        return {"category": category, "n": 0}  # no official endpoint: pricing falls back to budget and floor

    def list_messages(self, user, thread_id=None):
        return self._call(user, "list_messages", {"thread_id": thread_id} if thread_id else {})

    def list_events(self, user):
        return []

    def create_proposal_draft(self, user, job_id, cover_letter, bid_usd, screening_answers, idempotency_key):
        return self._call(user, "create_proposal_draft", {"job_id": job_id, "cover_letter": cover_letter,
                                                          "bid": bid_usd, "answers": screening_answers})

    def submit_proposal(self, user, draft_id, idempotency_key):
        # Live mode never submits. The draft waits on Upwork for the user's own confirmation.
        return {"status": "draft_awaiting_confirmation_on_upwork", "draft_id": draft_id, "connects_spent": 0}

    def send_message(self, user, thread_id, text, idempotency_key):
        return self._call(user, "create_message_draft", {"thread_id": thread_id, "text": text})
