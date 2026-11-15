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
