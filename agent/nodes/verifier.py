"""Claim verification node (B3, R5). Runs after the Writer and before the Critic.
Unsupported claims are removed; the before/after counts are kept for the report."""
from pydantic import BaseModel

from agent import llm
from agent.handoffs import ClaimCheck
from agent.nodes.base import node
from rag.verify import remove_unsupported, verify_claims


class ClaimChecks(BaseModel):
    checks: list[ClaimCheck]


def verify(text: str, evidence: list[dict]) -> list[dict]:
    """Model first (when a profile is configured), rules as the fallback and as a second opinion:
    a claim is kept as supported only if the rules do not call it unsupported."""
    rule_checks = verify_claims(text, evidence)
    model = llm.structured("verifier", ClaimChecks, draft=text, evidence=[{"id": e["id"], "text": e.get("snippet", "")} for e in evidence])
    if not model:
        return rule_checks
    by_claim = {c["claim"]: c for c in rule_checks}
    merged = []
    for c in model.checks:
        rule = by_claim.get(c.claim)
        label = "unsupported" if (rule and rule["label"] == "unsupported") else c.label
        merged.append({**c.model_dump(), "label": label})
    return merged or rule_checks


@node("verifier")
def verifier(state):
    evidence = state.get("evidence", [])
    if state.get("approval", {}).get("action") == "edit":
        # The user's own edit is never rewritten: only re-checked. Compliance blocks invented claims.
        return {"claim_checks": verify_claims(state["cover_letter"], evidence)}
    before = verify(state["cover_letter"], evidence)
    cleaned = remove_unsupported(state["cover_letter"], before)
    after = verify_claims(cleaned, evidence)
    stats = {"claims": len(before), "unsupported_before": sum(c["label"] == "unsupported" for c in before),
             "unsupported_after": sum(c["label"] == "unsupported" for c in after),
             "removed": [c["claim"] for c in before if c["label"] == "unsupported"]}
    return {"cover_letter": cleaned, "claim_checks": after, "claim_stats": stats}
