# GigBid Portfolio MCP server

Read-only access to a freelancer's portfolio evidence, built with the official MCP Python SDK.

**Tools:** `search_evidence(requirement, k, filters)`, `get_case_study(id)`, `list_skills()`
**Resources:** `portfolio://case/{id}`, `portfolio://proposal/{id}`
**Prompts:** `answer_screening_question`, `prove_requirement`

## Install and run (documented command)
```bash
git clone https://github.com/anasimran-dev/gigbid && cd gigbid
uv venv --python 3.12 && uv pip install .
python -m mcp_servers.portfolio.server            # stdio, for Claude Desktop or Cursor
python -m mcp_servers.portfolio.server --http     # HTTP with bearer token (MCP_TOKEN)
```
Use your own portfolio with `GIGBID_PERSONA_DIR` and `PORTFOLIO_PERSONA`; the sample personas in `data/personas/` are synthetic.

## Claude Desktop / Cursor config
```json
{ "mcpServers": { "gigbid-portfolio": {
    "command": "python", "args": ["-m", "mcp_servers.portfolio.server"],
    "cwd": "/path/to/gigbid", "env": { "PORTFOLIO_PERSONA": "ai_ml_engineer" } } } }
```
Not published to PyPI; this clone-and-run command is the install path.
