"""Critic: check grounding of every claim, personalisation and length; send back with reasons,
at most twice (the limit is enforced by the graph router, not by this node)."""
import re

from agent import llm
from agent.config import cfg
from agent.handoffs import Critique
from agent.nodes.base import node

GENERIC = re.compile(r"^(dear (sir|madam|hiring)|hello,? i am|hi,? i (am|have read)|i am writing to|to whom)", re.I)


def heuristic_critique(text: str, job: dict, claim_checks: list[dict]) -> Critique:
    p, issues = cfg()["proposal"], []
    words = len(text.split())
    if any(c["label"] == "unsupported" for c in claim_checks):
        issues.append("unsupported claim remains")
    if not any(c["evidence_ids"] for c in claim_checks):
        issues.append("no evidence cited")
    if words > p["max_words"]:
        issues.append(f"too long: {words} words, max {p['max_words']}")
    if words < p["min_words"]:
        issues.append(f"too short: {words} words, min {p['min_words']}")
    if GENERIC.match(text.strip()):
        issues.append("generic opening")
    keywords = {w for w in re.findall(r"[a-z]{4,}", f"{job['title']} {job.get('industry', '')}".lower())}
    if keywords and not any(k in text.lower() for k in keywords):
        issues.append("not personalised: never mentions the client's project")
    return Critique(approved=not issues, issues=issues, score=round(max(0.0, 1 - 0.25 * len(issues)), 2))


@node("critic")
def critic(state):
    text, job = state["cover_letter"], state["job"]
    base = heuristic_critique(text, job, state.get("claim_checks", []))
    model = llm.structured("critic", Critique, draft=text, job_title=job["title"], claim_checks=state.get("claim_checks", []),
                           min_words=cfg()["proposal"]["min_words"], max_words=cfg()["proposal"]["max_words"])
    if model:  # hard checks (length, grounding) always count
        issues = list(dict.fromkeys(base.issues + model.issues))
        base = Critique(approved=not issues, issues=issues, score=min(base.score, model.score))
    return {"critiques": [{**base.model_dump(), "revision": state.get("revisions", 0)}]}


@node("revise")
def revise(state):
    """Counts one trip back to the Writer."""
    return {"revisions": state.get("revisions", 0) + 1}
