"""C3 structured hand-offs. Agents exchange these Pydantic objects, never free text,
for anything a later step decides on."""
from typing import Literal

from pydantic import BaseModel, Field


class JobSpec(BaseModel):
    job_id: str
    title: str
    category: str = ""
    deliverables: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    budget_min: float = 0
    budget_max: float = 0
    timeline_days: int | None = None
    screening_questions: list[str] = Field(default_factory=list)
    hidden_needs: list[str] = Field(default_factory=list, description="Needs the client implies but does not name")


class RiskReport(BaseModel):
    score: float = Field(ge=0, le=1)
    scam: bool = False
    injection: bool = False
    flags: list[str] = Field(default_factory=list)
    client_quality: float = Field(0.5, ge=0, le=1)
    explanation: str = ""


class RequirementMatch(BaseModel):
    requirement: str
    evidence_ids: list[str] = Field(default_factory=list)
    covered: bool = False


class FitReport(BaseModel):
    score: float = Field(ge=0, le=1)
    matrix: list[RequirementMatch] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class BidDecision(BaseModel):
    action: Literal["bid", "watch", "skip"]
    reasons: list[str] = Field(default_factory=list)


class PriceQuote(BaseModel):
    amount_usd: float = Field(gt=0)
    low_usd: float = 0
    high_usd: float = 0
    connects_cost: int = 0
    connects_worth_it: bool = True
    rationale: str = ""


class Paragraph(BaseModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)


class ScreeningAnswer(BaseModel):
    question: str
    answer: str
    evidence_ids: list[str] = Field(default_factory=list)


class ProposalDraft(BaseModel):
    job_id: str
    paragraphs: list[Paragraph]
    screening_answers: list[ScreeningAnswer] = Field(default_factory=list)
    strategy: str = "evidence_first"
    revision: int = 0

    @property
    def cover_letter(self) -> str:
        return "\n\n".join(p.text for p in self.paragraphs if p.text.strip())


class ClaimCheck(BaseModel):
    claim: str
    label: Literal["supported", "partly_supported", "unsupported"]
    evidence_ids: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class Critique(BaseModel):
    approved: bool
    issues: list[str] = Field(default_factory=list)
    score: float = Field(0.0, ge=0, le=1)


class ComplianceVerdict(BaseModel):
    allowed: bool
    violations: list[str] = Field(default_factory=list)
    fixes: list[str] = Field(default_factory=list, description="What was removed automatically")
    cleaned_text: str = ""


class MessageIntent(BaseModel):
    intent: Literal["question", "negotiation", "interview_request", "scam_signal", "other"]
    reason: str = ""


class ReplyDraft(BaseModel):
    thread_id: str
    text: str
    intent: str
    slots: list[str] = Field(default_factory=list)
    hold_scam: bool = False
