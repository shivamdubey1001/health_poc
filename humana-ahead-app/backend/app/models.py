from datetime import datetime
from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MemberEnrollment(Base):
    __tablename__ = "member_enrollment"
    member_id: Mapped[str] = mapped_column(String, primary_key=True)
    synthetic_first_name: Mapped[str] = mapped_column(String)
    synthetic_last_name: Mapped[str] = mapped_column(String)
    age_band: Mapped[str] = mapped_column(String)
    preferred_language: Mapped[str] = mapped_column(String)
    preferred_contact_channel: Mapped[str] = mapped_column(String)
    plan_id: Mapped[str] = mapped_column(String, index=True)
    coverage_status: Mapped[str] = mapped_column(String)
    coverage_effective_date: Mapped[str] = mapped_column(String)
    coverage_end_date: Mapped[str] = mapped_column(String)
    zip3: Mapped[str] = mapped_column(String)
    county: Mapped[str] = mapped_column(String)
    communication_consent: Mapped[bool] = mapped_column(Boolean)
    source_system: Mapped[str] = mapped_column(String)


class PlanMaster(Base):
    __tablename__ = "plan_master"
    plan_id: Mapped[str] = mapped_column(String, primary_key=True)
    plan_name: Mapped[str] = mapped_column(String)
    plan_type: Mapped[str] = mapped_column(String)
    benefit_year: Mapped[int] = mapped_column(Integer)
    network_model: Mapped[str] = mapped_column(String)
    service_area: Mapped[str] = mapped_column(String)
    monthly_plan_premium: Mapped[float] = mapped_column(Float)
    medical_deductible: Mapped[float] = mapped_column(Float)
    in_network_max_out_of_pocket: Mapped[float] = mapped_column(Float)
    combined_max_out_of_pocket: Mapped[str] = mapped_column(String)
    specialist_referral_default: Mapped[str] = mapped_column(String)
    pcp_required: Mapped[bool] = mapped_column(Boolean)
    source_system: Mapped[str] = mapped_column(String)


class PlanBenefit(Base):
    __tablename__ = "plan_benefits"
    plan_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    benefit_year: Mapped[int] = mapped_column(Integer)
    service_group: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    benefit_name: Mapped[str] = mapped_column(String)
    coverage_status: Mapped[str] = mapped_column(String)
    in_network_member_cost_share: Mapped[str] = mapped_column(String)
    coverage_limit_or_note: Mapped[str] = mapped_column(String)
    prior_authorization_rule: Mapped[str] = mapped_column(String)
    referral_rule: Mapped[str] = mapped_column(String)
    source_system: Mapped[str] = mapped_column(String)


class BenefitAccumulator(Base):
    __tablename__ = "benefit_accumulators"
    member_id: Mapped[str] = mapped_column(String, primary_key=True)
    plan_id: Mapped[str] = mapped_column(String, index=True)
    benefit_year: Mapped[int] = mapped_column(Integer)
    as_of_date: Mapped[str] = mapped_column(String)
    medical_deductible_total: Mapped[float] = mapped_column(Float)
    medical_deductible_met: Mapped[float] = mapped_column(Float)
    medical_deductible_remaining: Mapped[float] = mapped_column(Float)
    in_network_oop_max: Mapped[float] = mapped_column(Float)
    in_network_oop_accumulated: Mapped[float] = mapped_column(Float)
    in_network_oop_remaining: Mapped[float] = mapped_column(Float)
    source_system: Mapped[str] = mapped_column(String)


class ClaimHistory(Base):
    __tablename__ = "claims_history"
    claim_id: Mapped[str] = mapped_column(String, primary_key=True)
    member_id: Mapped[str] = mapped_column(String, index=True)
    service_from_date: Mapped[str] = mapped_column(String, index=True)
    service_to_date: Mapped[str] = mapped_column(String)
    claim_received_date: Mapped[str] = mapped_column(String)
    claim_adjudicated_date: Mapped[str] = mapped_column(String)
    claim_type: Mapped[str] = mapped_column(String)
    place_of_service: Mapped[str] = mapped_column(String)
    provider_id: Mapped[str] = mapped_column(String, index=True)
    facility_id: Mapped[str] = mapped_column(String)
    diagnosis_code_1: Mapped[str] = mapped_column(String)
    diagnosis_description_1: Mapped[str] = mapped_column(String)
    diagnosis_code_2: Mapped[str] = mapped_column(String)
    diagnosis_description_2: Mapped[str] = mapped_column(String)
    procedure_code: Mapped[str] = mapped_column(String)
    procedure_description: Mapped[str] = mapped_column(String)
    billed_amount: Mapped[float] = mapped_column(Float)
    allowed_amount: Mapped[float] = mapped_column(Float)
    plan_paid_amount: Mapped[float] = mapped_column(Float)
    member_responsibility: Mapped[float] = mapped_column(Float)
    claim_status: Mapped[str] = mapped_column(String)
    network_status_at_service: Mapped[str] = mapped_column(String)
    source_system: Mapped[str] = mapped_column(String)


class MemberAdvocateCall(Base):
    __tablename__ = "member_advocate_calls"
    call_id: Mapped[str] = mapped_column(String, primary_key=True)
    member_id: Mapped[str] = mapped_column(String, index=True)
    call_start_timestamp: Mapped[str] = mapped_column(String, index=True)
    call_duration_seconds: Mapped[int] = mapped_column(Integer)
    channel: Mapped[str] = mapped_column(String)
    advocate_id: Mapped[str] = mapped_column(String)
    primary_topic: Mapped[str] = mapped_column(String)
    primary_topic_display: Mapped[str] = mapped_column(String)
    call_disposition: Mapped[str] = mapped_column(String)
    source_system: Mapped[str] = mapped_column(String)


class CallTranscript(Base):
    __tablename__ = "call_transcripts"
    call_id: Mapped[str] = mapped_column(String, primary_key=True)
    member_id: Mapped[str] = mapped_column(String, index=True)
    call_start_timestamp: Mapped[str] = mapped_column(String)
    transcript_text: Mapped[str] = mapped_column(Text)
    source_system: Mapped[str] = mapped_column(String)


class AgentAssistSummary(Base):
    __tablename__ = "agent_assist_call_summaries"
    call_id: Mapped[str] = mapped_column(String, primary_key=True)
    member_id: Mapped[str] = mapped_column(String, index=True)
    call_start_timestamp: Mapped[str] = mapped_column(String, index=True)
    summary_text: Mapped[str] = mapped_column(Text)
    member_need: Mapped[str] = mapped_column(Text)
    advocate_action: Mapped[str] = mapped_column(Text)
    follow_up_required: Mapped[bool] = mapped_column(Boolean)
    follow_up_note: Mapped[str] = mapped_column(Text)
    source_system: Mapped[str] = mapped_column(String)


class ProviderDirectory(Base):
    __tablename__ = "provider_directory"
    provider_id: Mapped[str] = mapped_column(String, primary_key=True)
    provider_type: Mapped[str] = mapped_column(String)
    provider_name: Mapped[str] = mapped_column(String)
    organization_name: Mapped[str] = mapped_column(String)
    specialty: Mapped[str] = mapped_column(String, index=True)
    city: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String)
    zip3: Mapped[str] = mapped_column(String, index=True)
    accepting_new_patients: Mapped[bool] = mapped_column(Boolean)
    source_system: Mapped[str] = mapped_column(String)


class ProviderNetwork(Base):
    __tablename__ = "provider_network"
    plan_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    provider_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    network_status: Mapped[str] = mapped_column(String)
    effective_date: Mapped[str] = mapped_column(String)
    termination_date: Mapped[str] = mapped_column(String)
    last_verified_date: Mapped[str] = mapped_column(String)
    source_system: Mapped[str] = mapped_column(String)


class PriorAuthorization(Base):
    __tablename__ = "prior_authorizations"
    authorization_id: Mapped[str] = mapped_column(String, primary_key=True)
    member_id: Mapped[str] = mapped_column(String, index=True)
    requesting_provider_id: Mapped[str] = mapped_column(String)
    facility_id: Mapped[str] = mapped_column(String)
    service_group: Mapped[str] = mapped_column(String, index=True)
    procedure_code: Mapped[str] = mapped_column(String)
    procedure_description: Mapped[str] = mapped_column(String)
    request_date: Mapped[str] = mapped_column(String)
    requested_service_date: Mapped[str] = mapped_column(String)
    authorization_status: Mapped[str] = mapped_column(String)
    decision_date: Mapped[str] = mapped_column(String)
    administrative_reason: Mapped[str] = mapped_column(Text)
    source_system: Mapped[str] = mapped_column(String)


class AIUsageLog(Base):
    __tablename__ = "ai_usage_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_name: Mapped[str] = mapped_column(String, index=True)
    member_id: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    estimated_cost: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[int] = mapped_column(Integer)
    transcript_tool_invoked: Mapped[bool] = mapped_column(Boolean, default=False)
    mode: Mapped[str] = mapped_column(String, default="MOCK")


class OutreachDecision(Base):
    __tablename__ = "outreach_decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String)
    message_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String)
