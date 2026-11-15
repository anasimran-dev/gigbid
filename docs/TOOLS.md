# Tools
One row per MCP tool (from `tests/contract/tool_schemas.snapshot.json`; schema changes fail the contract test).

| Tool | Kind | Safety |
|---|---|---|
| `marketplace.create_proposal_draft` | write | idempotency key + dry_run |
| `marketplace.get_client_history` | read | - |
| `marketplace.get_connects_balance` | read | - |
| `marketplace.get_job` | read | - |
| `marketplace.get_market_stats` | read | - |
| `marketplace.list_events` | read | - |
| `marketplace.list_messages` | read | - |
| `marketplace.search_jobs` | read | - |
| `marketplace.send_message` | write | idempotency key + dry_run |
| `marketplace.submit_proposal` | write | idempotency key + dry_run |
| `portfolio.get_case_study` | read | - |
| `portfolio.list_skills` | read | - |
| `portfolio.search_evidence` | read | - |
| `workspace.create_email_draft` | write | idempotency key + dry_run |
| `workspace.create_interview_hold` | write | idempotency key + dry_run |
| `workspace.free_slots` | read | - |

Per-agent allowlists live in `agent/config.yaml` (`tool_allowlists`) and are enforced in `agent/mcp_client.py`.

## Trust rationale for third-party servers
- **Upwork MCP** (`upwork_live` adapter): read tools are used for scouting; write tools (`submit_proposal`, `send_message`) are reachable only after the approval interrupt and with an idempotency key. OAuth tokens are Fernet-encrypted per tenant. Not run against real Upwork in this build; the `tool_map` in config is unverified.
- **GitHub MCP**: read-only repo ingestion (`rag/ingest/github.py`), token scoped to public repo read. Not exercised here (needs a token).
- Tool output from either server is untrusted text: it is delimited by `wrap_untrusted` and never treated as instructions.
