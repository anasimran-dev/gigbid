"""Fit Matcher: map every requirement to portfolio evidence; produce a fit score with reasons.
MCP: portfolio (read). Runs in parallel with the Job Analyst, so it extracts requirements itself."""
from agent.config import cfg
from agent.guardrails import strip_injection
from agent.handoffs import FitReport, RequirementMatch
from agent.mcp_client import call_tool
from agent.nodes.base import node
from rag.skills import extract_skills


def build_fit(requirements: list[str], evidence: list[dict]) -> FitReport:
    """Only evidence tied to a real project counts as proof (keyword-stuffed proposals do not)."""
    proofs = [e for e in evidence if e.get("project")]
    matrix = []
    for req in requirements:
        ids = [e["id"] for e in proofs if req in e.get("skills", []) or req in extract_skills(e.get("snippet", ""))]
        matrix.append(RequirementMatch(requirement=req, evidence_ids=ids[:3], covered=bool(ids)))
    covered = [m for m in matrix if m.covered]
    score = len(covered) / len(matrix) if matrix else (0.35 if proofs else 0.0)
    reasons = [f"{len(covered)} of {len(matrix)} requirements have portfolio evidence"] if matrix else \
              ["No explicit requirements could be extracted from the post; fit is uncertain"]
    return FitReport(score=round(score, 2), matrix=matrix, missing=[m.requirement for m in matrix if not m.covered],
                     evidence_ids=[e["id"] for e in proofs], reasons=reasons)


@node("matcher")
def matcher(state):
    job = state["job"]
    text = strip_injection(f"{job['title']}. {job['description']}")
    requirements = list(dict.fromkeys(extract_skills(text) + job.get("skills", [])))
    found = call_tool("matcher", "search_evidence", {"requirement": text[:3900], "k": max(8, cfg()["rag"]["k"]),
                                                     "persona": state["persona"], "filters": {"industry": job.get("industry", "")}})
    evidence = found["evidence"]
    return {"fit_report": build_fit(requirements, evidence).model_dump(), "evidence": evidence}
