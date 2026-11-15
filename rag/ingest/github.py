"""Ingest a GitHub repo's README and top-level code through the GitHub MCP server.

Third-party server (not written by us): https://github.com/github/github-mcp-server
Requires GITHUB_TOKEN. Uses the same MCP client the agents use, so no direct GitHub API calls.
"""
from rag.ingest.loaders import _item, add_upload


def ingest_repo(persona: str, owner: str, repo: str) -> list[dict]:
    from agent.mcp_client import call_tool  # imported lazily: needs the MCP client configured

    items = []
    for path in ("README.md",):
        res = call_tool("ingest", "get_file_contents", {"owner": owner, "repo": repo, "path": path}, server="github")
        text = res if isinstance(res, str) else str(res)
        stored = add_upload(persona, f"{owner}/{repo}/{path}", text, "readme")
        items.append(_item(persona, stored["id"], "readme", text, stored["project"], stored["title"],
                           source=f"github:{owner}/{repo}"))
    return items
