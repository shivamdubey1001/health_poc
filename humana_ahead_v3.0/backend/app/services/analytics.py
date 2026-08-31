from datetime import date, timedelta
from sqlalchemy.orm import Session
from app import models
from app.config import settings
from app.services.activity_filter import get_candidate_member_ids
from app.services.usage import aggregate_usage, outreach_decision_stats
from app.agents.care_intent import get_all_latest_care_intents
from app.services.readiness import get_all_latest_readiness

AS_OF = date.fromisoformat(settings.data_as_of)


def landing_summary(db: Session) -> dict:
    claims_cutoff = (AS_OF - timedelta(days=180)).isoformat()
    calls_cutoff = (AS_OF - timedelta(days=90)).isoformat()
    usage = aggregate_usage(db)
    return {
        "members": db.query(models.MemberEnrollment).count(),
        "claims_180d": db.query(models.ClaimHistory).filter(
            models.ClaimHistory.service_from_date >= claims_cutoff,
            models.ClaimHistory.service_from_date <= AS_OF.isoformat(),
        ).count(),
        "calls_90d": db.query(models.MemberAdvocateCall).filter(
            models.MemberAdvocateCall.call_start_timestamp >= calls_cutoff,
            models.MemberAdvocateCall.call_start_timestamp <= f"{AS_OF.isoformat()}T23:59:59",
        ).count(),
        "authorizations": db.query(models.PriorAuthorization).count(),
        "prompt_tokens_used": usage["total_input_tokens"],
        "prompt_tokens_label": "Prompt tokens used this session",
        "has_usage": usage["total_ai_calls"] > 0,
        "openai_configured": bool(settings.openai_api_key),
        "model": settings.openai_model,
        "data_as_of": settings.data_as_of,
    }


def dashboard_overview(db: Session) -> dict:
    total_members = db.query(models.MemberEnrollment).count()
    candidates = get_candidate_member_ids(db)
    usage = aggregate_usage(db)
    care = get_all_latest_care_intents(db)
    readiness = get_all_latest_readiness(db)
    high_conf = [r for r in care.values() if r.recommended_action == "RUN_READINESS_ASSESSMENT"]
    issues = [r for r in readiness.values() if r.top_issue]
    return {
        "kpis": {
            "active_members": total_members,
            "meaningful_activity": len(candidates),
            "members_evaluated": len(care),
            "high_confidence_care_intent": len(high_conf),
            "readiness_assessments": len(readiness),
            "administrative_issues_found": len(issues),
            "estimated_ai_cost": usage["estimated_ai_cost"],
        },
        "funnel": [
            {"label": "Active members", "value": total_members},
            {"label": "Meaningful new activity", "value": len(candidates)},
            {"label": "Agent 1 evaluated", "value": len(care)},
            {"label": "High-confidence care intent", "value": len(high_conf)},
            {"label": "Agent 2 assessed", "value": len(readiness)},
        ],
        "recent_assessments": [
            {
                "member_id": mid,
                "event": r.care_intent.predicted_care_event or "No high-confidence care event",
                "confidence": r.care_intent.confidence,
                "contact_risk": r.advocate_contact.risk_level,
                "readiness": readiness[mid].readiness_score if mid in readiness else None,
            }
            for mid, r in list(care.items())[-8:]
        ],
    }


def cost_analytics(db: Session) -> dict:
    usage = aggregate_usage(db)
    care = get_all_latest_care_intents(db)
    readiness = get_all_latest_readiness(db)
    high_conf = sum(1 for r in care.values() if r.recommended_action == "RUN_READINESS_ASSESSMENT")
    return {
        **usage,
        "model": settings.openai_model,
        "outreach_decisions": outreach_decision_stats(db),
        "funnel": [
            {"label": "Agent 1 assessments", "value": len(care)},
            {"label": "High-confidence", "value": high_conf},
            {"label": "Agent 2 assessments", "value": len(readiness)},
        ],
        "business_value_note": "No profitability claim is calculated from invented labor or call-deflection assumptions. Validate business value in a pilot using actual AHT, repeat-contact, avoided-call and loaded-labor data.",
    }
