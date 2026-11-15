"""Request and response models. The TypeScript client is generated from these via OpenAPI."""
from typing import Any, Literal

from pydantic import BaseModel, Field


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    persona: str = "ai_ml_engineer"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


class Settings(BaseModel):
    persona: str = "ai_ml_engineer"
    onboarded: bool = False
    marketplace: Literal["gigsim", "upwork"] = "gigsim"
    hourly_rate_usd: float = Field(30, ge=1, le=1000)
    min_project_usd: float = Field(150, ge=0, le=100000)
    weekly_connects_budget: int = Field(60, ge=0, le=1000)
    autonomy: Literal["manual", "auto_skip"] = "manual"
    saved_searches: list[str] = Field(default_factory=lambda: [""])
    strategy: str = ""
    categories: list[str] = Field(default_factory=list)


class ApprovalDecision(BaseModel):
    action: Literal["approve", "edit", "reject"]
    text: str = Field("", max_length=6000)
    reason: str = Field("", max_length=500)


class PortfolioUpload(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    text: str = Field(min_length=20, max_length=20000)
    type: Literal["case_study", "readme", "review", "proposal"] = "case_study"


class JobCard(BaseModel):
    id: str
    title: str = ""
    category: str = ""
    status: str = ""
    action: str = ""
    fit: float | None = None
    risk_flags: list[str] = Field(default_factory=list)
    price_usd: float | None = None
    connects_cost: int | None = None
    reason: str = ""


class RunInfo(BaseModel):
    id: str
    kind: str
    subject: str
    status: str
    trace_id: str
    started: float
    events: list[dict[str, Any]] = Field(default_factory=list)


class Started(BaseModel):
    run_id: str
    kind: str = "bid"


class Health(BaseModel):
    status: str = "ok"
    marketplace: dict[str, Any]
    mode: str
    profile: str
