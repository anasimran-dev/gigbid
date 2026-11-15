"""Portfolio MCP server (A1, read-only).

Run for Claude Desktop / Cursor (stdio):   python -m mcp_servers.portfolio.server
Run over HTTP:                             python -m mcp_servers.portfolio.server --http
Point it at your own portfolio folder with GIGBID_PERSONA_DIR and PORTFOLIO_PERSONA.
"""
import os
from typing import Annotated, Any

from pydantic import BaseModel, Field

from agent.config import cfg
from mcp_servers.common import READ, MCPServer, ToolError, audit, main_entry
from rag.retriever import get_corpus, get_retriever
from rag.skills import extract_skills

mcp = MCPServer("gigbid-portfolio", instructions="Read-only access to a freelancer's portfolio evidence. "
                "Use search_evidence before claiming any experience; cite evidence ids.")

Persona = Annotated[str, Field(description="Portfolio to search. Empty = server default.", max_length=64)]


def _persona(p: str) -> str:
    return p or os.getenv("PORTFOLIO_PERSONA", "ai_ml_engineer")


def _corpus(persona: str):
    emb = cfg()["embeddings"]
    return get_corpus(persona, emb["backend"], emb["model"])


def _public(item: dict, snippet: int = 800) -> dict:
    return {"id": item["id"], "type": item["type"], "title": item["title"], "project": item["project"],
            "source": item["source"], "date": item["date"], "outcome": item["outcome"], "industry": item["industry"],
            "skills": item["skills"], "snippet": item["text"][:snippet], "score": round(item.get("score", 0.0), 4)}


class Filters(BaseModel):
    types: list[str] = Field(default_factory=list, description="Keep only these evidence types: cv, case_study, readme, code, review, proposal")
    industry: str = Field("", description="Client industry to prefer, e.g. fintech")
    outcomes: list[str] = Field(default_factory=list, description="For past proposals: won, replied, ignored")


@mcp.tool(annotations=READ)
def search_evidence(requirement: Annotated[str, Field(min_length=2, max_length=4000, description="One job requirement, or a whole job post")],
                    k: Annotated[int, Field(ge=1, le=20)] = 5, filters: Filters | None = None,
                    persona: Persona = "", trace_id: str = "") -> dict[str, Any]:
    """Find portfolio evidence that proves a requirement. Returns items with type, source, date and outcome.
    Use the returned ids as citations; never claim experience that no item supports."""
    f = filters or Filters()
    job = {"title": "", "description": requirement, "industry": f.industry}
    spec = {"required_skills": extract_skills(requirement)}
    hits = get_retriever(cfg()["rag"]["variant"]).retrieve(_persona(persona), job, spec, k=k * 3, cfg=cfg())
    hits = [h for h in hits if (not f.types or h["type"] in f.types) and (not f.outcomes or h["outcome"] in f.outcomes)][:k]
    out = {"evidence": [_public(h) for h in hits], "variant": cfg()["rag"]["variant"]}
    audit("portfolio", _persona(persona), "search_evidence", {"requirement": requirement[:200], "k": k}, {"n": len(hits)}, trace_id)
    return out


@mcp.tool(annotations=READ)
def get_case_study(id: Annotated[str, Field(min_length=3, max_length=80, description="Evidence id from search_evidence")],
                   persona: Persona = "", trace_id: str = "") -> dict[str, Any]:
    """Load one full evidence item (case study, README, review or past proposal) by id."""
    item = _corpus(_persona(persona)).by_id.get(id)
    if not item:
        raise ToolError(f"not_found: no evidence item with id {id}")
    return {**_public(item, snippet=10_000), "text": item["text"]}


@mcp.tool(annotations=READ)
def list_skills(persona: Persona = "") -> dict[str, Any]:
    """List every skill the portfolio can prove, with the number of projects behind each."""
    counts: dict[str, set] = {}
    for it in _corpus(_persona(persona)).items:
        if it["project"]:
            for s in it["skills"]:
                counts.setdefault(s, set()).add(it["project"])
    return {"skills": [{"skill": s, "projects": len(p)} for s, p in sorted(counts.items(), key=lambda x: -len(x[1]))]}


@mcp.resource("portfolio://case/{id}")
def case_resource(id: str) -> str:
    """Full text of a case study or other evidence item."""
    return get_case_study(id)["text"]


@mcp.resource("portfolio://proposal/{id}")
def proposal_resource(id: str) -> str:
    """Full text and outcome of a past proposal."""
    item = get_case_study(id)
    return f"outcome: {item['outcome']}\n\n{item['text']}"


@mcp.prompt()
def answer_screening_question(question: str) -> str:
    """Answer a client's screening question from my portfolio."""
    return (f"Answer this screening question for a freelance job: \"{question}\".\n"
            "First call search_evidence with the question. Use only facts found in the returned items, "
            "cite each item id in brackets, keep it under 120 words, and say so plainly if no evidence exists.")


@mcp.prompt()
def prove_requirement(requirement: str) -> str:
    """Show which of my projects prove a job requirement."""
    return (f"Call search_evidence for: \"{requirement}\". List the best three items as "
            "'project - what I did - measurable result [id]'. If nothing matches, reply 'no evidence'.")


def main():
    main_entry(mcp, "PORTFOLIO_MCP_PORT", 9001)


if __name__ == "__main__":
    main()
