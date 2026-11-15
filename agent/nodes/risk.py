"""Risk Assessor: score client quality from history; flag scams, free-work requests,
off-platform asks and injected instructions. MCP: marketplace (read)."""
import re

from agent import llm
from agent.config import cfg
from agent.guardrails import detect_injection, wrap_untrusted
from agent.handoffs import RiskReport
from agent.mcp_client import call_tool
from agent.nodes.base import node

FREE_WORK = re.compile(r"\b(for free|unpaid|free (trial|test|sample)|payment only if|no payment until)\b", re.I)
UPFRONT_FEE = re.compile(r"\b(registration fee|pay a .{0,20}fee|refundable (fee|deposit)|security deposit)\b", re.I)


def client_quality(history: dict) -> float:
    q = 0.2 + 0.35 * bool(history.get("payment_verified")) + 0.25 * min(1.0, history.get("total_spent_usd", 0) / 3000)
    return round(min(1.0, q + 0.2 * history.get("hire_rate", 0.0)), 2)


def heuristic_risk(job: dict, history: dict) -> RiskReport:
    text = f"{job['title']} {job['description']}".lower()
    flags, score = [], 0.0
    if any(p in text for p in cfg()["policy"]["off_platform"]):
        flags.append("off_platform_contact_or_payment"); score += 0.6
    if FREE_WORK.search(text):
        flags.append("free_work_request"); score += 0.6
    if UPFRONT_FEE.search(text):
        flags.append("upfront_fee"); score += 0.7
    scam = bool(flags)
    injection = bool(detect_injection(job["description"]))
    if injection:
        flags.append("injected_instructions"); score += 0.3
    if not history.get("payment_verified"):
        flags.append("payment_not_verified"); score += 0.2
    if job.get("budget", {}).get("max", 0) <= 0:
        flags.append("no_budget"); score += 0.2
    quality = client_quality(history)
    return RiskReport(score=min(1.0, round(score, 2)), scam=scam, injection=injection, flags=flags, client_quality=quality,
                      explanation=("Flags: " + ", ".join(flags)) if flags else "No risk signals; client history looks normal.")


@node("risk")
def risk(state):
    job = state["job"]
    history = call_tool("risk", "get_client_history", {"user_id": state["user_id"], "client_id": job["client_id"]})
    base = heuristic_risk(job, history)
    report = llm.structured("risk", RiskReport, job=wrap_untrusted(f"{job['title']}\n{job['description']}"),
                            client_history=history, rule_flags=base.flags)
    if report:  # rules are a floor: the model may add flags but can never remove a rule-based one
        report = report.model_copy(update={"flags": sorted(set(report.flags) | set(base.flags)), "scam": report.scam or base.scam,
                                           "injection": base.injection, "score": max(report.score, base.score),
                                           "client_quality": base.client_quality})
    return {"risk_report": (report or base).model_dump()}
