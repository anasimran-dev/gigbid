"""C2 typed graph state with reducers.

Three things are kept apart on purpose:
  STATE            (this file)            what one job or conversation needs right now
  EXECUTION TRACE  (agent/tracing.py)     every node, tool call, argument and result, for audit
  LONG-TERM MEMORY (agent/memory/)        only promoted knowledge, written by an explicit rule

Reducers are needed wherever parallel branches write the same key: Job Analyst, Risk Assessor
and Fit Matcher all append to `steps`, `tokens`, `usd`, `errors` and `log` in the same super-step.
"""
import operator
from typing import Annotated, Any, TypedDict


def last(a, b):
    """Reducer: the newest value wins. Lets two parallel branches both report a failure status."""
    return b


def counter(a, b):
    """Reducer: add, or reset to zero when the update is None (a new round of a conversation)."""
    return 0 if b is None else (a or 0) + b


class BidState(TypedDict, total=False):
    # identity
    user_id: str
    persona: str
    trace_id: str
    settings: dict[str, Any]          # rates, floor, weekly Connects budget, autonomy, known fingerprints
    # the job
    job: dict[str, Any]
    duplicate_of: str
    # analyses (written by the three parallel branches; one key each, so no conflict)
    job_spec: dict[str, Any]
    risk_report: dict[str, Any]
    fit_report: dict[str, Any]
    evidence: list[dict[str, Any]]
    # decision and price
    decision: dict[str, Any]
    price_quote: dict[str, Any]
    # drafts and checks
    draft: dict[str, Any]
    cover_letter: str
    claim_checks: list[dict[str, Any]]
    claim_stats: dict[str, Any]
    critiques: Annotated[list[dict[str, Any]], operator.add]
    revisions: int
    compliance: dict[str, Any]
    # approval and outcome
    preview: dict[str, Any]
    approval: dict[str, Any]
    edits: Annotated[list[dict[str, Any]], operator.add]
    submission: dict[str, Any]
    status: Annotated[str, last]       # analysing | skipped | watching | awaiting_approval | submitted | rejected | blocked | needs_attention | dead_letter
    status_reason: Annotated[str, last]
    # budgets and audit (parallel writers -> reducers)
    steps: Annotated[int, operator.add]
    tokens: Annotated[int, operator.add]
    usd: Annotated[float, operator.add]
    errors: Annotated[list[str], operator.add]
    log: Annotated[list[str], operator.add]


class ConversationState(TypedDict, total=False):
    user_id: str
    persona: str
    trace_id: str
    thread_id: str
    thread: dict[str, Any]
    last_client_message: str
    intent: dict[str, Any]
    reply: dict[str, Any]
    compliance: dict[str, Any]
    preview: dict[str, Any]
    approval: dict[str, Any]
    edits: Annotated[list[dict[str, Any]], operator.add]
    sent: dict[str, Any]
    status: Annotated[str, last]
    status_reason: Annotated[str, last]
    steps: Annotated[int, counter]
    tokens: Annotated[int, counter]
    usd: Annotated[float, operator.add]
    errors: Annotated[list[str], operator.add]
    log: Annotated[list[str], operator.add]
