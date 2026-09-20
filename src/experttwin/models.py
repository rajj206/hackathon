from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class ExpertCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)


class Expert(BaseModel):
    id: str
    name: str
    description: str = ""
    created_at: datetime


class PortfolioSummary(BaseModel):
    expert_count: int = Field(ge=0)
    source_count: int = Field(ge=0)
    decision_count: int = Field(ge=0)
    projects: list[str]


class ExpertFinderRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=11)


class ExpertMatch(BaseModel):
    expert_id: str
    expert_name: str
    role: str
    score: float = Field(ge=0.0, le=1.0)
    confidence: Literal["strong", "limited"]
    evidence_count: int = Field(ge=1)
    project_count: int = Field(ge=0)
    matched_terms: list[str]
    explanation: str
    citations: list["Citation"]


class ExpertFinderResponse(BaseModel):
    question: str
    matches: list[ExpertMatch]
    simulation_notice: str = (
        "Ranked from synthetic demo evidence only; this is not an assessment of "
        "actual employee expertise."
    )


class Source(BaseModel):
    id: str
    expert_id: str
    title: str
    filename: str
    source_type: str
    status: Literal["processing", "ready", "failed"]
    error: str | None = None
    created_at: datetime
    decision_count: int = 0
    simulation: bool = False
    simulation_namespace: str | None = None


class ParsedSegment(BaseModel):
    text: str
    page_or_segment: str
    timestamp: str | None = None
    author: str | None = None
    speaker_role: str | None = None
    comment_id: str | None = None
    anchor_text: str | None = None
    parent_comment_id: str | None = None
    parent_author: str | None = None
    parent_text: str | None = None


class DecisionRecord(BaseModel):
    id: str
    expert_id: str
    expert: str
    decision: str
    choice: str
    alternatives: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    outcome: str | None = None
    source_id: str
    source_title: str
    evidence_text: str
    page_or_segment: str
    evidence_type: Literal["document", "review_comment", "transcript_turn"] = "document"
    evidence_author: str | None = None
    evidence_role: str | None = None
    comment_id: str | None = None
    anchor_text: str | None = None
    parent_comment_id: str | None = None
    parent_author: str | None = None
    parent_text: str | None = None
    timestamp: str | None = None
    tags: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    simulation: bool = False
    simulation_namespace: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class FingerprintPattern(BaseModel):
    category: str
    pattern: str
    support_count: int
    decision_ids: list[str]
    confidence: float


class EngineeringDecisionFingerprint(BaseModel):
    expert_id: str
    expert_name: str
    decision_count: int
    total_decision_count: int
    expert_attributed_decision_count: int
    contextual_decision_count: int
    recurring_preferences: list[FingerprintPattern]
    tradeoffs: list[FingerprintPattern]
    risk_posture: list[FingerprintPattern]
    technology_criteria: list[FingerprintPattern]
    troubleshooting_strategies: list[FingerprintPattern]
    operational_practices: list[FingerprintPattern]
    outcome_backed_lessons: list[FingerprintPattern]
    generated_at: datetime = Field(default_factory=utc_now)


class Citation(BaseModel):
    source_id: str
    source_title: str
    page_or_segment: str
    decision_id: str
    excerpt: str
    evidence_type: Literal["document", "review_comment", "transcript_turn"] = "document"
    evidence_author: str | None = None
    evidence_role: str | None = None
    comment_id: str | None = None
    anchor_text: str | None = None
    parent_comment_id: str | None = None
    parent_author: str | None = None
    attribution_status: Literal["expert_attributed", "contextual"] = "contextual"
    decision_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    simulation: bool = False
    simulation_namespace: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=10)


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    evidence_strength: Literal["strong", "limited", "insufficient"]
    expert_attributed_citation_count: int = 0
    contextual_citation_count: int = 0
    simulation_notice: str = "AI Clone"


class IngestionResult(BaseModel):
    source: Source
    decisions: list[DecisionRecord]


class WarRoomRequest(BaseModel):
    topic: str = Field(min_length=5, max_length=2000)


class WarRoomMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str = Field(min_length=1, max_length=40)
    speaker: str
    role: str
    ai_clone: Literal[True]
    text: str = Field(min_length=1, max_length=360)
    message_type: Literal["frame", "position", "challenge", "response", "refinement"]
    responds_to: str | None
    mentions: list[str] = Field(max_length=5)
    evidence_strength: Literal["strong", "limited", "insufficient"]
    citation_ids: list[str] = Field(max_length=2)


class WarRoomDissent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    view: str = Field(min_length=1, max_length=280)


class WarRoomRiskMitigation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk: str = Field(min_length=1, max_length=240)
    mitigation: str = Field(min_length=1, max_length=240)


class WarRoomActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner: str
    action: str = Field(min_length=1, max_length=240)


class WarRoomFinalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_owner: str
    recommendation: str = Field(min_length=1, max_length=500)
    rationale_tradeoffs: list[str] = Field(min_length=1, max_length=4)
    dissenting_views: list[WarRoomDissent] = Field(min_length=1, max_length=3)
    risks_mitigations: list[WarRoomRiskMitigation] = Field(min_length=1, max_length=4)
    action_items: list[WarRoomActionItem] = Field(min_length=1, max_length=6)
    citation_ids: list[str] = Field(min_length=1, max_length=12)


class WarRoomDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[WarRoomMessage] = Field(min_length=11, max_length=11)
    final_decision: WarRoomFinalDecision


class WarRoomResponse(WarRoomDraft):
    topic: str
    moderator: str
    citations: list[Citation]
