# Runbook
- Start: `cp .env.example .env && make seed && make dev`. Reviewer login is seeded by `apps/api/auth/users.py`.
- Scout interval: 30 min (worker cron). Rationale: new jobs on a 10-minute scale are rarely worth a bid within the response-time window, while 30 min keeps connects and LLM cost bounded.
- Crash/resume: every graph run uses `thread_id`; restart the API/worker and call resume on the same thread. The Postgres checkpointer restores state from the last completed node; pending approvals stay at the interrupt.
- Degraded demo: `MCPClient.kill("marketplace")` simulates an outage; expect the banner and `needs_attention` runs, not failures.
- Budgets: per-run token/connect caps in config; exceeding routes to the attention node.
- Change request (2 Nov): edit `agent/config.yaml` only (policy/thresholds); no code change.
