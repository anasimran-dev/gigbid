# GigBid: multi-agent freelancer copilot
Finds jobs, checks fit and risk, retrieves evidence from my portfolio, writes a verified proposal, and waits for my approval before anything is sent. Built for AI-4016 Assignment II (22i-1319).

Architecture: see `docs/ARCHITECTURE.md`. Tools: `docs/TOOLS.md`. Run: `docs/RUNBOOK.md`. Data: `docs/DATA_CARD.md`.

## Run
`cp .env.example .env && make seed && make test && make eval && make dev`

## Results (offline profile, synthetic data, LSA + lexical rerank stand-ins)
| Variant | Evidence Recall@5 | nDCG@10 | Unsupported claims per proposal | Judge score | GigSim reply rate | p95 latency (s) | Cost per proposal (USD) |
|---|---|---|---|---|---|---|---|
| v0_naive | 0.577 | 0.633 | 0.0 | not run (needs LLM) | 0.783 | 0.0553 | 0.0 |
| v1_decompose | 0.616 | 0.673 | 0.0 | not run (needs LLM) | 0.675 | 0.0542 | 0.0 |
| v2_hybrid | 0.598 | 0.660 | 0.0 | not run (needs LLM) | 0.8 | 0.0538 | 0.0 |
| v3_rerank | 0.627 | 0.702 | 0.0 | not run (needs LLM) | 0.775 | 0.0496 | 0.0 |
| v4_outcome | 0.633 | 0.694 | 0.0 | not run (needs LLM) | 0.833 | 0.0495 | 0.0 |
| v5_multivector | 0.625 | 0.685 | 0.0 | not run (needs LLM) | 0.808 | 0.0475 | 0.0 |
| v9_skill_graph | 0.821 | 0.913 | 0.0 | not run (needs LLM) | 0.825 | 0.0463 | 0.0 |
| v10_combined | 0.720 | 0.781 | 0.0 | not run (needs LLM) | 0.825 | 0.0555 | 0.0 |

Profile: offline; embeddings: lsa; reranker: lexical; data: synthetic (scripts/generate_data.py, seed 4016).

- Best retrieval: V9 skill graph (recall@5 0.821). Combining everything (V10, 0.720) did not beat it.
- Decision eval: bid/skip F1 about 0.95, scam recall 1.0, price-in-band 0.70-0.78. Failures concentrate on vague posts and injection jobs (`evals/results/decision_eval.json`).
- A/B extension: no significant difference (`docs/EXTENSION.md`).

## Honest limitations
- All data synthetic; GigSim here is my own stand-in, so outcome numbers measure the simulator.
- Not run in the build environment: real LangGraph + Postgres checkpointer, FastAPI, Arq worker, the web app build, Docker, Playwright, live Upwork/GitHub MCP, any LLM call. Judge score, tool granularity study, single-agent/supervisor comparison and post-defence injection ASR need an LLM key (marked "not run" rather than invented).
- Judge calibration needs your 30 hand labels.

Pinned versions: `pyproject.toml`, `apps/web/package.json`.
