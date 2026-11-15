"""MCP server tests through an in-memory MCP client (A7)."""
import json

import pytest

import mcp_servers.marketplace.server as marketplace
import mcp_servers.portfolio.server as portfolio
import mcp_servers.workspace.server as workspace
from agent.mcp_client import ToolNotAllowed, ToolUnavailable, call_tool, kill, status
from tests.conftest import call

LETTER = "I built a RAG assistant with LangChain and FAISS that cut first-response time from 9 hours to 40 minutes."


def test_portfolio_search_returns_evidence_with_metadata():
    out = call(portfolio.mcp, "search_evidence", {"requirement": "RAG chatbot with LangChain", "k": 3, "persona": "ai_ml_engineer"})
    assert out["evidence"] and {"id", "type", "source", "date", "outcome"} <= set(out["evidence"][0])
    full = call(portfolio.mcp, "get_case_study", {"id": out["evidence"][0]["id"], "persona": "ai_ml_engineer"})
    assert full["text"]
    assert call(portfolio.mcp, "list_skills", {"persona": "data_analyst"})["skills"]


def test_input_schema_is_enforced():
    with pytest.raises(RuntimeError):
        call(marketplace.mcp, "create_proposal_draft", {"user_id": "u", "job_id": "job-0001", "cover_letter": "short", "bid_usd": -5, "idempotency_key": "k"})


def test_dry_run_has_no_side_effects(isolated):
    out = call(marketplace.mcp, "create_proposal_draft", {"user_id": "u", "job_id": "job-0001", "cover_letter": LETTER, "bid_usd": 500,
                                                          "idempotency_key": "dry-run-key-1", "dry_run": True})
    assert out["dry_run"] and out["preview"]["cover_letter"] == LETTER and out["connects_cost"] > 0
    assert isolated.s["drafts"] == {}


def test_retried_submit_never_spends_connects_twice(isolated):
    args = {"user_id": "u", "job_id": "job-0001", "cover_letter": LETTER, "bid_usd": 500, "idempotency_key": "draft-key-01"}
    draft = call(marketplace.mcp, "create_proposal_draft", args)
    assert call(marketplace.mcp, "create_proposal_draft", args)["id"] == draft["id"]
    sub = {"user_id": "u", "draft_id": draft["id"], "idempotency_key": "submit-key-01"}
    first, second = call(marketplace.mcp, "submit_proposal", sub), call(marketplace.mcp, "submit_proposal", sub)
    assert second["idempotent_replay"] and second["balance_after"] == first["balance_after"]
    assert len(isolated.s["proposals"]) == 1


def test_rate_limit_and_audit_log(tmp_path):
    marketplace.limiter.per_minute = 2
    call(marketplace.mcp, "get_connects_balance", {"user_id": "u", "trace_id": "trace-1"})
    call(marketplace.mcp, "get_connects_balance", {"user_id": "u"})
    with pytest.raises(RuntimeError, match="rate_limited"):
        call(marketplace.mcp, "get_connects_balance", {"user_id": "u"})
    line = json.loads((tmp_path / "audit.jsonl").read_text().splitlines()[0])
    assert line["user"] == "u" and line["tool"] == "get_connects_balance" and line["trace_id"] == "trace-1"


def test_workspace_hold_is_idempotent():
    slots = call(workspace.mcp, "free_slots", {"user_id": "u", "start_date": "2026-11-16", "days": 1})["slots"]
    args = {"user_id": "u", "slot": slots[0], "title": "Interview", "idempotency_key": "hold-key-01"}
    assert call(workspace.mcp, "create_interview_hold", args)["id"] == call(workspace.mcp, "create_interview_hold", args)["id"]
    assert slots[0] not in call(workspace.mcp, "free_slots", {"user_id": "u", "start_date": "2026-11-16", "days": 1})["slots"]


def test_agents_only_get_their_own_tools():
    with pytest.raises(ToolNotAllowed):
        call_tool("scout", "submit_proposal", {})
    with pytest.raises(ToolNotAllowed):
        call_tool("analyst", "search_jobs", {})


def test_degraded_mode_when_marketplace_server_is_down():
    kill("marketplace")
    with pytest.raises(ToolUnavailable):
        call_tool("scout", "search_jobs", {"user_id": "u"})
    assert status()["ok"] is False
    kill("marketplace", False)
    call_tool("scout", "search_jobs", {"user_id": "u"})
    assert status()["ok"] is True
