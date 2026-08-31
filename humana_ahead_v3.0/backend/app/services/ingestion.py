from pathlib import Path
import pandas as pd
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, SessionLocal
from app import models

TABLES = {
    "member_enrollment.csv": (models.MemberEnrollment, "member_enrollment"),
    "plan_master.csv": (models.PlanMaster, "plan_master"),
    "plan_benefits.csv": (models.PlanBenefit, "plan_benefits"),
    "benefit_accumulators.csv": (models.BenefitAccumulator, "benefit_accumulators"),
    "claims_history.csv": (models.ClaimHistory, "claims_history"),
    "member_advocate_calls.csv": (models.MemberAdvocateCall, "member_advocate_calls"),
    "call_transcripts.csv": (models.CallTranscript, "call_transcripts"),
    "agent_assist_call_summaries.csv": (models.AgentAssistSummary, "agent_assist_call_summaries"),
    "provider_directory.csv": (models.ProviderDirectory, "provider_directory"),
    "provider_network.csv": (models.ProviderNetwork, "provider_network"),
    "prior_authorizations.csv": (models.PriorAuthorization, "prior_authorizations"),
}


def initialize_database(force: bool = False) -> None:
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    if not force and inspector.has_table("member_enrollment"):
        with SessionLocal() as db:
            if db.query(models.MemberEnrollment).count() > 0:
                ensure_default_settings(db)
                ensure_eval_labels(db)
                return

    for filename, (_, table_name) in TABLES.items():
        path = settings.data_path / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing data file: {path}")
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        # Convert booleans/numerics as expected by SQLite/SQLAlchemy while retaining raw meaning.
        bool_cols = [c for c in df.columns if c in {"communication_consent", "pcp_required", "follow_up_required", "accepting_new_patients"}]
        for col in bool_cols:
            df[col] = df[col].str.lower().map({"true": True, "false": False}).fillna(False)
        numeric_cols = {
            "benefit_year", "call_duration_seconds", "monthly_plan_premium", "medical_deductible",
            "in_network_max_out_of_pocket", "medical_deductible_total", "medical_deductible_met",
            "medical_deductible_remaining", "in_network_oop_max", "in_network_oop_accumulated",
            "in_network_oop_remaining", "billed_amount", "allowed_amount", "plan_paid_amount",
            "member_responsibility"
        }
        for col in [c for c in df.columns if c in numeric_cols]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        df.to_sql(table_name, engine, if_exists="replace", index=False)

    # Recreate ORM-owned operational tables because pandas replacement may reset metadata relationships/indexes.
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_default_settings(db)
        ensure_eval_labels(db)


def ensure_default_settings(db: Session) -> None:
    defaults = {
        "care_intent_threshold": str(settings.care_intent_threshold),
        "recent_call_limit": str(settings.recent_call_limit),
        "claim_lookback_months": str(settings.claim_lookback_months),
        "enable_transcript_fallback": str(settings.enable_transcript_fallback).lower(),
    }
    for key, value in defaults.items():
        if not db.get(models.AppSetting, key):
            db.add(models.AppSetting(key=key, value=value))
    db.commit()


def ensure_eval_labels(db: Session) -> None:
    """Derive held-out evaluation labels once, on first boot.

    Labels come from prior-authorization records, which Agent 1 is explicitly
    forbidden from seeing. Only the evaluation module reads this table.
    """
    from app.services.eval_service import rebuild_labels

    if db.query(models.EvalLabel).count() == 0:
        rebuild_labels(db)
