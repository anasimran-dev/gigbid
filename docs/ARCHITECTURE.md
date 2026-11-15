# Architecture
```
React/Vite web --SSE/REST--> FastAPI --> LangGraph (bid graph, conversation graph) --> MCP client (allowlists)
                                 |                                                   |-> portfolio MCP  (RAG over CV/cases/repos)
                         Postgres (tenant docs,                                      |-> marketplace MCP -> port -> GigSim | Upwork
                          checkpointer) + Redis <-- Arq worker (scout cron)         |-> workspace MCP (email draft, calendar hold)
```
- **Bid graph**: scout -> parallel [analyst | risk | matcher] via `Send` -> decide -> pricing -> writer -> verifier -> critic (max 2 revisions) -> compliance -> preview -> approval `interrupt()` -> submit -> learn.
- **Conversation graph**: read -> classify -> draft reply -> reply compliance -> approval -> send.
- **State vs trace vs memory**: graph state is the working set; the JSONL trace (PII-masked) is the audit record; long-term memory (style, outcomes) is written only through `agent/memory/promotion_rules.py` (style: 2 repeats, outcome: 3 samples).
- **Config-driven**: thresholds, policy, budgets, models and RAG variant live in `agent/config.yaml`; prompts in `agent/prompts/*.md`.
- **Degraded mode**: if an MCP server is down the node retries, then marks `needs_attention` and the UI shows a banner.
- **Security**: bearer auth on MCP servers, tenant-scoped storage, injection delimiting, contact stripping, PII masking.
