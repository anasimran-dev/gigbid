"""Contract test (A7): fails CI when an MCP tool's name, input schema or annotations change
unintentionally. To accept an intended change: UPDATE_SNAPSHOT=1 pytest tests/contract"""
import asyncio
import json
import os
from pathlib import Path

import mcp_servers.marketplace.server as marketplace
import mcp_servers.portfolio.server as portfolio
import mcp_servers.workspace.server as workspace

SNAPSHOT = Path(__file__).parent / "tool_schemas.snapshot.json"


def current() -> dict:
    out = {}
    for name, server in (("portfolio", portfolio), ("marketplace", marketplace), ("workspace", workspace)):
        for tool in asyncio.run(server.mcp.list_tools()):
            d = tool.model_dump(exclude_none=True)
            schema = d.get("input_schema") or d.get("inputSchema")
            out[f"{name}.{tool.name}"] = {"required": sorted(schema.get("required", [])),
                                          "properties": {k: {x: v[x] for x in sorted(v) if x not in ("title", "description")}
                                                         for k, v in sorted(schema["properties"].items())},
                                          "annotations": {k.replace("_", "").lower(): v for k, v in sorted(d.get("annotations", {}).items())}}
    return out


def test_tool_schemas_match_snapshot():
    now = current()
    if os.getenv("UPDATE_SNAPSHOT") or not SNAPSHOT.exists():
        SNAPSHOT.write_text(json.dumps(now, indent=1, sort_keys=True))
    assert now == json.loads(SNAPSHOT.read_text()), "MCP tool schema changed. If intended, rerun with UPDATE_SNAPSHOT=1."


def test_write_tools_are_annotated_and_idempotent():
    for name, spec in current().items():
        tool = name.split(".")[1]
        if tool in ("create_proposal_draft", "submit_proposal", "send_message", "create_interview_hold", "create_email_draft"):
            assert spec["annotations"]["readonlyhint"] is False and spec["annotations"]["idempotenthint"] is True
            assert "idempotency_key" in spec["required"] and "dry_run" in spec["properties"]
        else:
            assert spec["annotations"]["readonlyhint"] is True
    assert current()["marketplace.submit_proposal"]["annotations"]["destructivehint"] is True
