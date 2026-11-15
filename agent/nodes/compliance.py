"""Compliance Guard: enforce the policy pack. Deterministic on purpose (no model, no MCP):
a guard that can be talked out of its rules is not a guard.

Agent drafts are cleaned automatically (contact details, guarantees, banned phrases removed).
Text the USER edited is never changed silently: violations block it and are shown in the UI.
"""
import re

from agent.config import cfg
from agent.guardrails import strip_contacts
from agent.handoffs import ComplianceVerdict
from agent.nodes.base import node
from rag.verify import split_sentences

INJECTED_ECHO = re.compile(r"(work for free|system prompt|ignore (all |your )?previous)", re.I)


def find_violations(text: str, claim_checks: list[dict]) -> list[str]:
    policy, low, v = cfg()["policy"], text.lower(), []
    v += [f"banned phrase: '{p}'" for p in policy["banned_phrases"] if p in low]
    v += [f"off-platform contact or payment: '{p}'" for p in policy["off_platform"] if p in low]
    v += [f"contact detail: {kind}" for kind in strip_contacts(text)[1]]
    if INJECTED_ECHO.search(text):
        v.append("text echoes an injected instruction")
    v += [f"invented claim: '{c['claim'][:60]}'" for c in claim_checks if c["label"] == "unsupported"]
    return v


def clean(text: str) -> tuple[str, list[str]]:
    """Remove offending sentences and contact details from an agent-written draft."""
    policy, fixes, paragraphs = cfg()["policy"], [], []
    bad = [p for p in policy["banned_phrases"] + policy["off_platform"]]
    for para in text.split("\n\n"):
        kept = []
        for s in split_sentences(para):
            if any(b in s.lower() for b in bad) or INJECTED_ECHO.search(s):
                fixes.append(f"removed sentence: '{s[:60]}'")
            else:
                kept.append(s)
        if kept:
            paragraphs.append(" ".join(kept))
    text, removed = strip_contacts("\n\n".join(paragraphs))
    return text, fixes + [f"removed {r}" for r in removed]


def check(text: str, claim_checks: list[dict], user_edited: bool, min_words: int = 30) -> ComplianceVerdict:
    violations = find_violations(text, claim_checks)
    if not violations:
        return ComplianceVerdict(allowed=True, cleaned_text=text)
    if user_edited:
        return ComplianceVerdict(allowed=False, violations=violations, cleaned_text=text)
    cleaned, fixes = clean(text)
    left = find_violations(cleaned, claim_checks)
    ok = not left and len(cleaned.split()) >= min_words
    return ComplianceVerdict(allowed=ok, violations=left or ([] if ok else ["draft too short after removing violations"]),
                             fixes=fixes, cleaned_text=cleaned)


@node("compliance")
def compliance(state):
    edited = state.get("approval", {}).get("action") == "edit"
    verdict = check(state["cover_letter"], state.get("claim_checks", []), edited)
    out = {"compliance": verdict.model_dump(), "cover_letter": verdict.cleaned_text or state["cover_letter"]}
    if not verdict.allowed and not edited:
        out.update(status="blocked", status_reason="Compliance Guard blocked the draft: " + "; ".join(verdict.violations))
    return out
