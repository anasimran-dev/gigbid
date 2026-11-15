---
title: "GigBid: a multi-agent freelancer copilot"
author: "Anas Imran (22i-1319), AI-4016 R&D Assignment II"
---

## 1. Problem and scope
GigBid scouts freelance jobs, decides bid or skip, retrieves evidence from the freelancer's portfolio, writes a verified proposal, and waits for human approval before submitting. It also triages client messages. All data is synthetic (seed 4016); the marketplace is a simulator I wrote.

## 2. Architecture
A LangGraph bid graph (scout, parallel analyst/risk/matcher via `Send`, decide, pricing, writer, verifier, critic loop with at most 2 revisions, compliance, preview, approval interrupt, submit, learn) and a conversation graph. Agents call three MCP servers (Portfolio, Marketplace, Workspace) through per-agent allowlists. Marketplace access goes through one port with GigSim and live Upwork adapters. Thresholds, policy, budgets, model routing and the retrieval variant are in `agent/config.yaml`; prompts are in `agent/prompts/`.

## 3. MCP servers
Sixteen tools across the three servers (see `docs/TOOLS.md`). Writes use idempotency keys and dry-run; all calls are audited; servers use bearer auth and rate limits. A contract test snapshots every tool schema. GitHub is intended as a third-party server for repo ingestion; it was not run.

**R&D question A (tool granularity).** Hypothesis: rewritten, example-bearing descriptions would beat both fine and coarse tool sets. Setup: 40 tasks with a known correct call, gpt-oss-20b on Groq (`evals/results/tool_granularity.json`). Result: fine-grained (10 tools) tool selection 0.825, arguments 0.775, 411.25 tokens/task; coarse (3 tools) 0.525, 0.5, 319.675; rewritten descriptions 0.525, 0.525, 301.75. The hypothesis was not supported: fine-grained tools won and the rewritten descriptions matched the coarse set. I did not test why.

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
Every agent has a rule-based path and an optional LLM path with small/strong model routing. A verifier labels each claim supported, partly supported or unsupported and removes unsupported ones. Memory is written only through promotion rules (style after 2 repeats, outcomes after 3 samples). **R&D question C (single agent vs supervisor vs graph).** 20 dev jobs (AI/ML persona), Qwen3.8-27B for (a) and (b) because gpt-oss rejected their tool calls, Groq free tier (`evals/results/agent_comparison.json`). (c) hand-built graph: bid/skip accuracy 1.0, 0.3333 unsupported claims per proposal, 0 compliance violations, reply rate 0.5, p95 latency 33.9905 s. (a) single ReAct agent: 17 of 20 runs failed (malformed tool calls or unparsable output); (b) prebuilt supervisor: 18 of 20 failed. Their accuracy of 0.7 is what always answering skip scores on this set, they sent no proposals (reply rate 0.0), and p95 latency was 88.7464 s and 331.7153 s. So this run shows the graph is far more robust with a small free model, not that it writes better proposals: the baselines mostly did not complete, so quality cannot be compared. I did not find a job type where (a) won, because (a) rarely finished. With a stronger tool-calling model the comparison could come out differently. Sample size is 20, not 50.

## 6. Web UI
React + Vite + TypeScript with nine screens, SSE run streaming, evidence hover, approval panel, run timeline, degraded-mode banner, and five Playwright specs. The web app builds and type-checks against the client generated from the FastAPI OpenAPI schema, and all 10 Playwright runs pass (5 specs on a laptop and a phone profile). It is deployed on Render (see README).

## 7. Production
Arq worker with cron scouting, Postgres checkpointer and tenant-scoped storage, Fernet-encrypted OAuth tokens, docker compose, CI with an eval gate, and PII-masked JSONL traces. The Render deployment runs the API and the built web app in one process with inline job execution. The docker compose stack, the Arq worker, the Postgres checkpointer and CI were not executed.

## 8. Evaluation
Decision eval: bid/skip F1 about 0.95; scam recall 1.0 (precision 0.81-0.875); price in fair band 0.70-0.78. GigSim reply rates by variant are 0.675-0.833 and reflect my simulator's hidden preferences only. Injection: 33 injection jobs; with a model behind the pipeline attack success was 0.0 before and 0.0 after the defences, flagged rate 1.0. gpt-oss did not obey the injected text even without the defence, so this run does not show the defence's own effect. LLM decision eval (first 20 dev jobs per persona, gpt-oss-20b/120b): bid/skip F1 1.0, 0.857, 1.0; 0.0 unsupported claims before and after verification; p95 latency per job 32.2865, 38.0901, 14.1213 s; cost 0.0 USD on the free tier (`decision_eval_llm.json`). Only 15 proposals were drafted across the three personas, so price and proposal-quality numbers are thin. Judge calibration: Cohen's kappa 0.047 on 25 items, near chance, with reference labels assigned by Claude rather than by me (`docs/AI_USAGE.md`); I therefore do not report per-variant judge scores. A/B extension: reply rate 0.855 vs 0.855, p = 1.0, no effect, as expected from the simulator.

## 9. Failures
25 decision failures: vague posts (11 wrong bids, 4 wrong skips) and injection posts (6 wrong bids, 4 wrong skips). Proposed fixes: a clarifying-question path for vague posts, and neutralise-then-re-evaluate for injected posts.

## 10. Limitations and not run
Synthetic data only. Not executed: Docker compose, the Postgres checkpointer crash-and-resume demo, the worker, live Upwork and GitHub MCP, the blind human panel and the hidden test run. LLM evals used small samples (20 jobs per persona; 20 for the agent comparison) on a free-tier hosted open model.

**A bug the evals exposed.** My first LLM-backed runs reported plausible numbers while the provider was rejecting every request with HTTP 403 (it blocked Python's default user agent). Each node silently fell back to its rule-based path, so the eval looked healthy with no model in it. I caught it because token counts were near zero and latency was too low, discarded those runs, added a User-Agent header and reran everything. The lesson for the design: a fallback that hides a dead dependency needs a visible counter of how many calls actually reached the model.
