# AI usage
- Tool: Claude (chat/agent assistant) was used to scaffold and write most of the code, tests, docs and the data generator, which I directed and reviewed.
- Files: nearly every file in `agent/`, `rag/`, `mcp_servers/`, `apps/`, `evals/`, `docs/`.
- Something it got wrong and was caught: the first decomposed-retrieval variants scored recall@5 about 0.15 (worse than naive) until query expansion and project collapsing were added; separately, proposal "result" sentences contained markdown headings, found by reading output, and fixed.
- Offline evals use stand-ins (LSA, lexical rerank); the LLM paths were not run in the build environment.
- [Student to complete: your own review notes and anything you changed.]
