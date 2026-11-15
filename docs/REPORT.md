---
title: "GigBid: a multi-agent freelancer copilot"
author: "Anas Imran (22i-1319), AI-4016 R&D Assignment II"
---

## 1. Problem and scope
GigBid scouts freelance jobs, decides bid or skip, retrieves evidence from the freelancer's portfolio, writes a verified proposal, and waits for human approval before submitting. It also triages client messages. All data is synthetic (seed 4016); the marketplace is a simulator I wrote.

## 2. Architecture
A LangGraph bid graph (scout, parallel analyst/risk/matcher via `Send`, decide, pricing, writer, verifier, critic loop with at most 2 revisions, compliance, preview, approval interrupt, submit, learn) and a conversation graph. Agents call three MCP servers (Portfolio, Marketplace, Workspace) through per-agent allowlists. Marketplace access goes through one port with GigSim and live Upwork adapters. Thresholds, policy, budgets, model routing and the retrieval variant are in `agent/config.yaml`; prompts are in `agent/prompts/`.

## 3. MCP servers
Sixteen tools across the three servers (see `docs/TOOLS.md`). Writes use idempotency keys and dry-run; all calls are audited; servers use bearer auth and rate limits. A contract test snapshots every tool schema. GitHub is intended as a third-party server for repo ingestion; it was not run here.

## 4. Retrieval and ablation
| Variant | Recall@5 | nDCG@10 |
|---|---|---|
| V0 naive | 0.577 | 0.633 |
| V1 decompose | 0.616 | 0.673 |
| V2 hybrid | 0.598 | 0.660 |
| V3 rerank | 0.627 | 0.702 |
| V4 outcome | 0.633 | 0.694 |
| V5 multi-vector | 0.625 | 0.685 |
| V9 skill graph | 0.821 | 0.913 |
| V10 combined | 0.720 | 0.781 |

Removing one component from V10 changes recall@5 by 0.4 to 4.2 points (decompose -0.042, rerank -0.020, hybrid -0.014, collapse -0.006, outcome -0.007), so components overlap. V9 is the default. Caveat: LSA embeddings and a lexical reranker stand in for open models, and synthetic skill vocabulary favours graph expansion.

## 5. Agents and verification
Every agent has a rule-based path and an optional LLM path with small/strong model routing. A verifier labels each claim supported, partly supported or unsupported and removes unsupported ones. Memory is written only through promotion rules (style after 2 repeats, outcomes after 3 samples). Comparison of single-agent vs supervisor vs graph: only the graph (c) was measured offline (accuracy 0.96, 0.11 unsupported claims per proposal, 0 compliance violations); (a) and (b) need an LLM and are not run.

## 6. Web UI
React + Vite + TypeScript with nine screens, SSE run streaming, evidence hover, approval panel, run timeline, degraded-mode banner, and five Playwright specs. The UI was written but not built or tested in this environment.

## 7. Production
Arq worker with cron scouting, Postgres checkpointer and tenant-scoped storage, Fernet-encrypted OAuth tokens, docker compose, CI with an eval gate, and PII-masked JSONL traces. None of the container, worker or CI paths were executed here.

## 8. Evaluation
Decision eval: bid/skip F1 about 0.95; scam recall 1.0 (precision 0.81-0.875); price in fair band 0.70-0.78. GigSim reply rates by variant are 0.675-0.833 and reflect my simulator's hidden preferences only. Injection: 33 injection jobs, attack success 0.0 and flagged 1.0, from the rule-based path; the model-backed measurement is not run. A/B extension: reply rate 0.855 vs 0.855, p = 1.0, no effect, as expected from the simulator.

## 9. Failures
25 decision failures: vague posts (11 wrong bids, 4 wrong skips) and injection posts (6 wrong bids, 4 wrong skips). Proposed fixes: a clarifying-question path for vague posts, and neutralise-then-re-evaluate for injected posts.

## 10. Limitations and not run
Synthetic data only. Not executed: real LangGraph and Postgres checkpointer, FastAPI, worker, web build, Docker, Playwright, live Upwork and GitHub, all LLM calls. Judge calibration (needs 30 human labels), tool-granularity study, and single-agent/supervisor comparison are not run; no numbers are given for them.
