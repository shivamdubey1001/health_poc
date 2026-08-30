from typing import Literal
from pydantic import BaseModel, Field, field_validator


class EvidenceItem(BaseModel):
    type: str
    description: str
    source_id: str | None = None
    date: str | None = None


class CareIntentBlock(BaseModel):
    detected: bool
    predicted_care_event: str | None = None
    care_category: str | None = None
    confidence: float = Field(ge=0, le=1)
    estimated_time_window: str | None = None


class AdvocateContactBlock(BaseModel):
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    confidence: float = Field(ge=0, le=1)
    reason: str


class CareIntentResult(BaseModel):
    member_id: str
    care_intent: CareIntentBlock
    advocate_contact: AdvocateContactBlock
    evidence: list[EvidenceItem]
    recommended_action: Literal["RUN_READINESS_ASSESSMENT", "MONITOR"]
    threshold: float
    transcript_tool_invoked: bool = False
    generated_by: str = "OPENAI"


class ReadinessItem(BaseModel):
    key: str
    label: str
    status: Literal["READY", "NEEDS_ATTENTION", "IN_PROGRESS", "UNKNOWN", "NOT_APPLICABLE"]
    detail: str
    deduction: int = 0


class ProviderAlternative(BaseModel):
    provider_id: str
    provider_name: str
    organization_name: str
    specialty: str
    city: str
    state: str
    zip3: str
    network_status: str
    accepting_new_patients: bool


class ReadinessResult(BaseModel):
    member_id: str
    predicted_care_event: str
    readiness_score: int
    readiness_label: str
    checklist: list[ReadinessItem]
    top_issue: str | None
    score_explanation: list[str]
    alternatives: list[ProviderAlternative]
    recommended_next_action: str
    generated_by: str = "OPENAI + deterministic checks"


class MemberBatchRequest(BaseModel):
    member_ids: list[str] = Field(min_length=1, max_length=250)

    @field_validator("member_ids")
    @classmethod
    def unique_ids(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in value:
            if item not in seen:
                result.append(item)
                seen.add(item)
        return result


class OutreachDraft(BaseModel):
    member_id: str
    channel: str
    message: str
    human_approval_required: bool = True


class OutreachActionRequest(BaseModel):
    message: str
    action: Literal["APPROVE", "REJECT", "SAVE_FOR_REVIEW"]


class SettingsUpdate(BaseModel):
    care_intent_threshold: float | None = Field(default=None, ge=0.5, le=0.95)
    recent_call_limit: int | None = Field(default=None, ge=1, le=10)
    claim_lookback_months: int | None = Field(default=None, ge=3, le=24)
    enable_transcript_fallback: bool | None = None
