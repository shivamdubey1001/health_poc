from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.agents.care_intent import get_all_latest_care_intents
from app.database import get_db
from app.services.readiness import get_all_latest_readiness

router = APIRouter()


@router.get("/queue/ahead")
def ahead_queue(db: Session = Depends(get_db)):
    """Returns only assessments the user has explicitly run.

    This endpoint never invokes Agent 1 or Agent 2. It is safe to open without incurring model cost.
    """
    care = get_all_latest_care_intents(db)
    readiness = get_all_latest_readiness(db)
    rows = []
    for member_id, assessment in care.items():
        rr = readiness.get(member_id)
        rows.append({
            "member_id": member_id,
            "predicted_care_event": assessment.care_intent.predicted_care_event or "No high-confidence care event",
            "care_intent_confidence": assessment.care_intent.confidence,
            "estimated_time_window": assessment.care_intent.estimated_time_window,
            "advocate_contact_risk": assessment.advocate_contact.risk_level,
            "advocate_contact_confidence": assessment.advocate_contact.confidence,
            "readiness": rr.readiness_score if rr else None,
            "top_issue": rr.top_issue if rr else ("Eligible for readiness" if assessment.recommended_action == "RUN_READINESS_ASSESSMENT" else "Monitor"),
            "status": "READINESS_COMPLETE" if rr else "READY_FOR_READINESS" if assessment.recommended_action == "RUN_READINESS_ASSESSMENT" else "MONITOR",
        })
    return rows
