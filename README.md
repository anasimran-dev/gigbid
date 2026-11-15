# GigBid: multi-agent freelancer copilot
Finds jobs, checks fit and risk, retrieves evidence from my portfolio, writes a verified proposal, and waits for my approval before anything is sent. Built for AI-4016 Assignment II (22i-1319).

**Live demo:** https://gigbid-m75r.onrender.com (reviewer login is given privately in the Classroom submission; free tier, the first load after idle can take about a minute). Source: https://github.com/anasimran-dev/gigbid

Architecture: see `docs/ARCHITECTURE.md`. Tools: `docs/TOOLS.md`. Run: `docs/RUNBOOK.md`. Data: `docs/DATA_CARD.md`.

## Run
`cp .env.example .env && make seed && make test && make eval && make dev`

## Results
### Retrieval and outcome (offline profile, synthetic data, LSA + lexical rerank stand-ins; `evals/results/results_table.md`)
| Variant | Evidence Recall@5 | nDCG@10 | Unsupported claims per proposal | Judge score | GigSim reply rate | p95 latency (s) | Cost per proposal (USD) |
|---|---|---|---|---|---|---|---|
| v0_naive | 0.577 | 0.633 | 0.0 | not run per variant (judge calibration only: see judge_calibration.json) | 0.783 | 0.0553 | 0.0 |
| v1_decompose | 0.616 | 0.673 | 0.0 | not run per variant (judge calibration only: see judge_calibration.json) | 0.675 | 0.0542 | 0.0 |
| v2_hybrid | 0.598 | 0.660 | 0.0 | not run per variant (judge calibration only: see judge_calibration.json) | 0.8 | 0.0538 | 0.0 |
| v3_rerank | 0.627 | 0.702 | 0.0 | not run per variant (judge calibration only: see judge_calibration.json) | 0.775 | 0.0496 | 0.0 |
| v4_outcome | 0.633 | 0.694 | 0.0 | not run per variant (judge calibration only: see judge_calibration.json) | 0.833 | 0.0495 | 0.0 |
| v5_multivector | 0.625 | 0.685 | 0.0 | not run per variant (judge calibration only: see judge_calibration.json) | 0.808 | 0.0475 | 0.0 |
| v9_skill_graph | 0.821 | 0.913 | 0.0 | not run per variant (judge calibration only: see judge_calibration.json) | 0.825 | 0.0463 | 0.0 |
| v10_combined | 0.720 | 0.781 | 0.0 | not run per variant (judge calibration only: see judge_calibration.json) | 0.825 | 0.0555 | 0.0 |

Per-variant judge scores were not run: the judge was calibrated (below) and disagreed with my labels too much to rank variants with.

- Shipped retrieval: V9 skill graph (recall@5 0.821). Combining everything (V10, 0.720) did not beat it. Ablation: `evals/results/ablation.json`.
- A/B extension X2: no significant difference (`docs/EXTENSION.md`, `evals/results/ab_experiment.json`).

### LLM-backed runs (Groq free tier, `openai/gpt-oss-20b` for cheap nodes, `openai/gpt-oss-120b` for Writer/Critic/Liaison/judge)
| Study | Result | File |
|---|---|---|
| Tool granularity, 40 tasks, gpt-oss-20b | fine (10 tools): selection 0.825, arguments 0.775, 411.25 tokens/task; coarse (3 tools): 0.525, 0.5, 319.675; rewritten descriptions: 0.525, 0.525, 301.75. Fine-grained tools won; rewriting descriptions did not help (negative result). | `tool_granularity.json` |
| Decision eval with LLM, first 20 dev jobs per persona | bid/skip F1 1.0 / 0.857 / 1.0 (AI-ML / full-stack / analyst); unsupported claims per proposal 0.0 before and after verification; p95 latency per job 32.2865 / 38.0901 / 14.1213 s; tokens per job 304.15 / 1490.75 / 486.85; USD 0.0 (free tier; prices in config set to 0). Only 6 / 8 / 1 proposals were drafted, so price-in-band is not meaningful here. | `decision_eval_llm.json` |
| Injection attack success, 33 planted-injection jobs | 0.0 before defences, 0.0 after; flagged rate 1.0. The model did not obey the injected text even raw, so these numbers do not show the defence's own effect. | `injection_eval.json` |
| Single agent vs supervisor vs graph, 20 dev jobs, Qwen3.8-27B for (a)/(b) | graph: accuracy 1.0, unsupported 0.3333, reply rate 0.5; single ReAct agent: 17/20 runs failed; prebuilt supervisor: 18/20 failed. Baselines mostly did not complete with this free model, so this shows robustness, not proposal quality. | `agent_comparison.json` |
| Judge calibration | Cohen's kappa 0.047 on 25 of 30 items (binned low/mid/high), close to chance. The 30 reference labels were assigned by Claude, not by me (see `docs/AI_USAGE.md`). | `judge_calibration.json` |

Full offline decision eval (all 600 dev jobs, rule-based path): bid/skip F1 0.90-0.98, scam recall 1.0, price in band 0.70-0.78 (`decision_eval.json`); failures are in `docs/FAILURES.md`.

Profile and versions: pinned in `pyproject.toml` and `requirements.lock` (LangGraph 0.6.11, Python 3.12). Data: synthetic (`scripts/generate_data.py`, seed 4016, see `docs/DATA_CARD.md`).

## Tests
31 Python tests pass with the real LangGraph (`python -m pytest -q`); 10 Playwright runs pass (5 specs on laptop and phone profiles); the web app builds and type-checks against the generated API client.

## Honest limitations
- All data is synthetic; GigSim here is my own stand-in, so outcome numbers measure that simulator.
- Not run: Docker compose and the Postgres checkpointer crash-and-resume demo (no Docker available while building), the live Upwork and GitHub MCP servers, the blind human panel, and the instructor's hidden test run.
- LLM evals used small samples to fit the time (20 jobs per persona for decisions, 20 for the agent comparison) and a free-tier hosted open model.
- The judge is not reliable enough to rank variants (kappa near chance), and its reference labels came from Claude, not a human.

Pinned versions: `pyproject.toml`, `requirements.lock`, `apps/web/package.json`.
