"""Job Analyst: turn a job post into a structured JobSpec. No MCP access."""
import re

from agent import llm
from agent.guardrails import strip_injection, wrap_untrusted
from agent.handoffs import JobSpec
from agent.nodes.base import node
from rag.skills import extract_skills


def heuristic_spec(job: dict) -> JobSpec:
    text = strip_injection(f"{job['title']}. {job['description']}")
    deliverables = [m.group(2).strip() for m in re.finditer(r"\b(deliver|need|build)\s+([^.;]{8,120})", text, re.I)][:3]
    skills = list(dict.fromkeys(extract_skills(text) + [s for s in job.get("skills", [])]))
    return JobSpec(job_id=job["id"], title=job["title"], category=job.get("category", ""), deliverables=deliverables,
                   required_skills=skills, budget_min=job.get("budget", {}).get("min", 0),
                   budget_max=job.get("budget", {}).get("max", 0), timeline_days=job.get("duration_days"),
                   screening_questions=job.get("screening_questions", []))


@node("analyst")
def analyst(state):
    job = state["job"]
    base = heuristic_spec(job)
    spec = llm.structured("analyst", JobSpec, job=wrap_untrusted(f"{job['title']}\n{job['description']}"), job_id=job["id"])
    if spec:  # keep facts that come from marketplace fields, not from the model
        spec = spec.model_copy(update={"job_id": job["id"], "budget_min": base.budget_min, "budget_max": base.budget_max,
                                       "screening_questions": base.screening_questions, "category": base.category or spec.category})
    return {"job_spec": (spec or base).model_dump()}
