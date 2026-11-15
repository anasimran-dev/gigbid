"""Proposal Writer: draft the cover letter and screening answers with evidence citations.
MCP: portfolio (read). Every proof sentence is built from one evidence item and carries its id."""
import re

from agent import llm
from agent.config import cfg
from agent.guardrails import wrap_untrusted
from agent.handoffs import Paragraph, ProposalDraft, ScreeningAnswer
from agent.memory import promotion_rules as rules
from agent.memory.store import get_store
from agent.nodes.base import node


def result_sentence(evidence: dict) -> str:
    """The measurable result stated in the evidence item (first prose sentence that contains a number)."""
    for line in evidence.get("snippet", "").split("\n"):
        if line.startswith(("#", "---", "**", "`")) or re.match(r"^\w+: ", line):
            continue  # headings, front matter, metadata lines
        for s in re.split(r"(?<=[.!?])\s+", line):
            if re.search(r"\d", s) and len(s.split()) > 4 and s.rstrip().endswith((".", "!")):
                s = s.split(" and it ", 1)[1] if " and it " in s else s
                return re.sub(r"^(The project|It|it)\s+", "", s.strip()).rstrip(".!")
    return ""


def article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def proofs_for(evidence: list[dict], required: list[str], limit: int) -> list[dict]:
    """One item per project, best coverage of the required skills first."""
    seen, picked = set(), []
    ranked = sorted((e for e in evidence if e.get("project")), key=lambda e: -len(set(e.get("skills", [])) & set(required)))
    for e in ranked:
        if e["project"] not in seen and result_sentence(e):
            seen.add(e["project"])
            picked.append(e)
    return picked[:limit]


def heuristic_draft(job: dict, spec: dict, fit: dict, evidence: list[dict], strategy: str, revision: int,
                    issues: list[str], style: dict) -> ProposalDraft:
    limit = 3 - revision if any("too long" in i for i in issues) else 3 + (1 if any("too short" in i for i in issues) else 0)
    if style.get("shorter"):
        limit = min(limit, 2)
    required = spec.get("required_skills", [])
    proofs = proofs_for(evidence, required, max(1, limit))
    need = (spec.get("deliverables") or [job["title"].lower()])[0]
    industry = job.get("industry") or "your"
    if strategy == "question_first":
        opening = f"For {need}, is the first priority speed of delivery or long-term maintainability? Either way, this is close to work already in my portfolio."
    else:
        opening = f"You need {need} for your {industry} business, and the projects below are the closest matches from my portfolio."
    paragraphs = [] if style.get("cut_first_sentence") else [Paragraph(text=opening)]
    mentioned = set()
    for e in proofs:
        used = [s for s in e.get("skills", []) if s in required][:3] or e.get("skills", [])[:2]
        mentioned |= set(used)
        ind = e.get("industry") or "past"
        text = f"On {e['title']} for {article(ind)} {ind} client I used {', '.join(used)} and {result_sentence(e)}."
        paragraphs.append(Paragraph(text=text, evidence_ids=[e["id"]]))
    extra = [m for m in fit.get("matrix", []) if m["covered"] and m["requirement"] not in mentioned][:3]
    if extra:
        paragraphs.append(Paragraph(text="I have also worked with " + ", ".join(m["requirement"] for m in extra) + " on other client projects.",
                                    evidence_ids=[i for m in extra for i in m["evidence_ids"][:1]]))
    paragraphs.append(Paragraph(text="I can start this week. Would a 20 minute call suit you to confirm scope and milestones?"))
    answers = []
    for q in spec.get("screening_questions", []):
        if proofs:
            e = proofs[0]
            answers.append(ScreeningAnswer(question=q, evidence_ids=[e["id"]],
                                           answer=f"The closest match is {e['title']}, where I {result_sentence(e)}."))
    for p in paragraphs:
        p.text = rules.apply_style(p.text, style)
    return ProposalDraft(job_id=job["id"], paragraphs=paragraphs, screening_answers=answers, strategy=strategy, revision=revision)


@node("writer")
def writer(state):
    job, spec = state["job"], state["job_spec"]
    store, user = get_store(), state["user_id"]
    style = rules.style_rules(store, user)
    strategy = (state.get("settings", {}).get("strategy") or rules.best_strategy(store, user, spec.get("category", ""))
                or cfg()["proposal"]["strategy"])
    revision = state.get("revisions", 0)
    issues = state["critiques"][-1]["issues"] if state.get("critiques") else []
    draft = llm.structured("writer", ProposalDraft, job=wrap_untrusted(f"{job['title']}\n{job['description']}"),
                           job_id=job["id"], spec=spec, evidence=state.get("evidence", []), strategy=strategy,
                           style_rules=style["rules"], critic_issues=issues, min_words=cfg()["proposal"]["min_words"],
                           max_words=cfg()["proposal"]["max_words"])
    if draft:
        known = {e["id"] for e in state.get("evidence", [])}
        for p in draft.paragraphs:  # the model may only cite evidence it was given
            p.evidence_ids = [i for i in p.evidence_ids if i in known]
            p.text = rules.apply_style(p.text, style)
        draft = draft.model_copy(update={"job_id": job["id"], "strategy": strategy, "revision": revision})
    draft = draft or heuristic_draft(job, spec, state["fit_report"], state.get("evidence", []), strategy, revision, issues, style)
    return {"draft": draft.model_dump(), "cover_letter": draft.cover_letter}
