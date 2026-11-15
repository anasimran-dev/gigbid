"""R1: the ONE marketplace interface. Two adapters implement it (GigSim, live Upwork).

Switch with marketplace.mode in agent/config.yaml or the MARKETPLACE_MODE env var.
Only the Marketplace MCP server imports this; agents reach it through MCP tools.
"""
from typing import Any, Protocol

from agent.config import cfg


class MarketplaceUnavailable(Exception):
    """Raised after bounded retries. The UI shows a degraded banner and work is queued."""


class MarketplacePort(Protocol):
    def search_jobs(self, user: str, query: str, limit: int = 20) -> list[dict[str, Any]]: ...
    def get_job(self, user: str, job_id: str) -> dict[str, Any]: ...
    def get_client_history(self, user: str, client_id: str) -> dict[str, Any]: ...
    def get_connects_balance(self, user: str) -> dict[str, Any]: ...
    def get_market_stats(self, user: str, category: str, skills: list[str]) -> dict[str, Any]: ...
    def list_messages(self, user: str, thread_id: str | None = None) -> list[dict[str, Any]]: ...
    def list_events(self, user: str) -> list[dict[str, Any]]: ...
    def create_proposal_draft(self, user: str, job_id: str, cover_letter: str, bid_usd: float,
                              screening_answers: list[str], idempotency_key: str) -> dict[str, Any]: ...
    def submit_proposal(self, user: str, draft_id: str, idempotency_key: str) -> dict[str, Any]: ...
    def send_message(self, user: str, thread_id: str, text: str, idempotency_key: str) -> dict[str, Any]: ...


def get_marketplace() -> MarketplacePort:
    mode = cfg()["marketplace"]["mode"]
    if mode == "upwork":
        from mcp_servers.marketplace.adapters.upwork_live import UpworkLiveAdapter
        return UpworkLiveAdapter()
    from mcp_servers.marketplace.adapters.gigsim import GigSimAdapter
    return GigSimAdapter()
