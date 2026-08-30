from datetime import date, timedelta
from sqlalchemy.orm import Session
from app import models
from app.services.settings_service import get_runtime_settings


def _row(obj, fields: list[str]) -> dict:
    if obj is None:
        return {}
    return {field: getattr(obj, field) for field in fields}


def get_member_or_none(db: Session, member_id: str):
    return db.get(models.MemberEnrollment, member_id)


def get_member_profile(db: Session, member_id: str) -> dict | None:
    member = get_member_or_none(db, member_id)
    if not member:
        return None
    plan = db.get(models.PlanMaster, member.plan_id)
    accumulator = db.get(models.BenefitAccumulator, member_id)
    last_call = (
        db.query(models.MemberAdvocateCall)
        .filter(models.MemberAdvocateCall.member_id == member_id)
        .order_by(models.MemberAdvocateCall.call_start_timestamp.desc())
        .first()
    )
    claim_count = db.query(models.ClaimHistory).filter(models.ClaimHistory.member_id == member_id).count()
    return {
        "member_id": member.member_id,
        "name": f"{member.synthetic_first_name} {member.synthetic_last_name}",
        "first_name": member.synthetic_first_name,
        "last_name": member.synthetic_last_name,
        "age_band": member.age_band,
        "preferred_language": member.preferred_language,
        "preferred_contact_channel": member.preferred_contact_channel,
        "plan_id": member.plan_id,
        "plan_name": plan.plan_name if plan else member.plan_id,
        "plan_type": plan.plan_type if plan else "",
        "coverage_status": member.coverage_status,
        "zip3": member.zip3,
        "county": member.county,
        "communication_consent": member.communication_consent,
        "last_advocate_call": last_call.call_start_timestamp if last_call else None,
        "claim_count": claim_count,
        "accumulator": _row(accumulator, [
            "medical_deductible_total", "medical_deductible_met", "medical_deductible_remaining",
            "in_network_oop_max", "in_network_oop_accumulated", "in_network_oop_remaining"
        ]) if accumulator else None,
    }


def get_recent_claims(db: Session, member_id: str, months: int | None = None) -> list[dict]:
    runtime = get_runtime_settings(db)
    months = months or runtime["claim_lookback_months"]
    cutoff = (date(2026, 8, 29) - timedelta(days=months * 30)).isoformat()
    rows = (
        db.query(models.ClaimHistory)
        .filter(models.ClaimHistory.member_id == member_id, models.ClaimHistory.service_from_date >= cutoff)
        .order_by(models.ClaimHistory.service_from_date.asc())
        .all()
    )
    return [{
        "claim_id": r.claim_id,
        "service_date": r.service_from_date,
        "diagnosis_code": r.diagnosis_code_1,
        "diagnosis_description": r.diagnosis_description_1,
        "procedure_code": r.procedure_code,
        "procedure_description": r.procedure_description,
        "provider_id": r.provider_id,
        "facility_id": r.facility_id,
        "allowed_amount": r.allowed_amount,
        "member_responsibility": r.member_responsibility,
        "network_status_at_service": r.network_status_at_service,
    } for r in rows]


def get_recent_calls(db: Session, member_id: str, limit: int | None = None) -> list[dict]:
    runtime = get_runtime_settings(db)
    limit = limit or runtime["recent_call_limit"]
    calls = (
        db.query(models.MemberAdvocateCall)
        .filter(models.MemberAdvocateCall.member_id == member_id)
        .order_by(models.MemberAdvocateCall.call_start_timestamp.desc())
        .limit(limit)
        .all()
    )
    summaries = {
        s.call_id: s for s in db.query(models.AgentAssistSummary)
        .filter(models.AgentAssistSummary.call_id.in_([c.call_id for c in calls] or ["__none__"]))
        .all()
    }
    return [{
        "call_id": c.call_id,
        "timestamp": c.call_start_timestamp,
        "duration_seconds": c.call_duration_seconds,
        "topic": c.primary_topic_display,
        "disposition": c.call_disposition,
        "summary": summaries[c.call_id].summary_text if c.call_id in summaries else None,
        "member_need": summaries[c.call_id].member_need if c.call_id in summaries else None,
        "advocate_action": summaries[c.call_id].advocate_action if c.call_id in summaries else None,
        "follow_up_required": summaries[c.call_id].follow_up_required if c.call_id in summaries else False,
        "follow_up_note": summaries[c.call_id].follow_up_note if c.call_id in summaries else None,
        "transcript_available": db.get(models.CallTranscript, c.call_id) is not None,
    } for c in reversed(calls)]


def get_transcript(db: Session, call_id: str) -> dict | None:
    row = db.get(models.CallTranscript, call_id)
    if not row:
        return None
    return {
        "call_id": row.call_id,
        "member_id": row.member_id,
        "call_start_timestamp": row.call_start_timestamp,
        "transcript_text": row.transcript_text,
    }


def _claim_trajectory(claims: list[dict]) -> list[str]:
    seen = []
    for c in claims:
        label = c["procedure_description"] or c["diagnosis_description"]
        if label and label not in seen:
            seen.append(label)
    return seen[-8:]


def build_member_context(db: Session, member_id: str) -> dict | None:
    profile = get_member_profile(db, member_id)
    if not profile:
        return None
    plan = db.get(models.PlanMaster, profile["plan_id"])
    accumulator = db.get(models.BenefitAccumulator, member_id)
    claims = get_recent_claims(db, member_id)
    calls = get_recent_calls(db, member_id)
    return {
        "member": profile,
        "plan": _row(plan, [
            "plan_id", "plan_name", "plan_type", "benefit_year", "network_model", "service_area",
            "medical_deductible", "in_network_max_out_of_pocket", "specialist_referral_default", "pcp_required"
        ]),
        "benefit_accumulators": _row(accumulator, [
            "benefit_year", "as_of_date", "medical_deductible_total", "medical_deductible_met",
            "medical_deductible_remaining", "in_network_oop_max", "in_network_oop_accumulated", "in_network_oop_remaining"
        ]),
        "recent_claims": claims,
        "recent_claim_trajectory": _claim_trajectory(claims),
        "recent_calls": calls,
        "recent_agent_assist_summaries": [{
            "call_id": c["call_id"], "timestamp": c["timestamp"], "summary": c["summary"],
            "follow_up_required": c["follow_up_required"], "follow_up_note": c["follow_up_note"]
        } for c in calls],
        "available_transcript_ids": [c["call_id"] for c in calls if c["transcript_available"]],
    }


def list_members(db: Session, search: str = "", limit: int = 250) -> list[dict]:
    query = db.query(models.MemberEnrollment)
    if search:
        token = f"%{search.lower()}%"
        query = query.filter(
            (models.MemberEnrollment.member_id.ilike(token)) |
            (models.MemberEnrollment.synthetic_first_name.ilike(token)) |
            (models.MemberEnrollment.synthetic_last_name.ilike(token))
        )
    members = query.order_by(models.MemberEnrollment.member_id.asc()).limit(limit).all()
    return [get_member_profile(db, m.member_id) for m in members]
