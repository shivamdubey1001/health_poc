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
    # Displayed instead of a raw percentage while the score is uncalibrated.
    confidence_band: Literal["HIGH", "MODERATE_HIGH", "MODERATE", "LOW", "MINIMAL"] = "MINIMAL"
    confidence_band_reason: str = ""
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
    prompt_version: str = ""


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
    weight_rationale: str = ""
    provider_provenance: list[str] = []


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
    # Governance is applied per message class, not per confidence level. A
    # message that asks a member to change provider is high consequence at any
    # confidence; a reassurance message is low consequence at any confidence.
    message_class: Literal["INFORMATIONAL", "BENEFIT_SURFACING", "COST_DISCLOSURE",
                           "CARE_REDIRECTION", "CLINICAL_ADJACENT"] = "INFORMATIONAL"
    gating_policy: str = "ADVOCATE_APPROVAL_REQUIRED"
    top_issue: str | None = None

    # The notification carries the full readiness picture, not just a sentence.
    # A member told only that "something needs attention" has to call to find out
    # what, which is the behaviour this product exists to prevent.
    headline: str = ""
    predicted_care_event: str = ""
    readiness_score: int = 0
    readiness_label: str = ""
    highlighted_action: str = ""
    checklist: list[dict] = []
    ready_count: int = 0
    total_items: int = 0

    # The notification resolves rather than refers. Where the plan already knows
    # the answer, the member is given a choice they can act on instead of being
    # told to call somebody.
    resolution_mode: Literal["CHOOSE_OPTION", "CONFIRM", "NO_ACTION", "ADVOCATE"] = "NO_ACTION"
    call_to_action: str = ""
    member_options: list[dict] = []
    advocate_required: bool = False
    advocate_reason: str = ""
    alternatives: list[dict] = []


class OutreachActionRequest(BaseModel):
    message: str
    action: Literal["APPROVE", "REJECT", "SAVE_FOR_REVIEW"]
    original_message: str = ""


class EvalRunRequest(BaseModel):
    member_ids: list[str] | None = None
    limit: int = Field(default=40, ge=1, le=250)
    index_date: str | None = None
    threshold: float | None = Field(default=None, ge=0.1, le=0.95)


class PerturbationRequest(BaseModel):
    member_id: str


class SettingsUpdate(BaseModel):
    care_intent_threshold: float | None = Field(default=None, ge=0.5, le=0.95)
    recent_call_limit: int | None = Field(default=None, ge=1, le=10)
    claim_lookback_months: int | None = Field(default=None, ge=3, le=24)
    enable_transcript_fallback: bool | None = None
