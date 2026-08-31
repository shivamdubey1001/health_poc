from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.care_intent import get_latest_care_intent
from app.database import get_db
from app.schemas import OutreachActionRequest
from app.services.outreach import build_outreach_draft, record_decision
from app.services.readiness import get_latest_readiness
from app.services.usage import outreach_decision_stats

router = APIRouter()


@router.post("/members/{member_id}/outreach/draft")
def draft(member_id: str, db: Session = Depends(get_db)):
    # Outreach is downstream of explicit Agent 1 and Agent 2 actions. Never
    # invoke either agent here.
    care = get_latest_care_intent(db, member_id)
    readiness = get_latest_readiness(db, member_id)
    if not care:
        raise HTTPException(409, detail={
            "error": "CARE_INTENT_REQUIRED",
            "message": "Run the upcoming-procedure scan before drafting outreach."})
    if not readiness:
        raise HTTPException(409, detail={
            "error": "READINESS_REQUIRED",
            "message": "Run the readiness assessment before drafting outreach."})
    return build_outreach_draft(db, member_id, care, readiness)


@router.post("/members/{member_id}/outreach/decision")
def decision(member_id: str, payload: OutreachActionRequest, db: Session = Depends(get_db)):
    """Single decision endpoint.

    Saving for review previously posted to the reject endpoint, which meant any
    endpoint-level metric counted saves as rejections - and override rate by
    action is exactly the data this product needs to earn automation later.
    """
    readiness = get_latest_readiness(db, member_id)
    draft_meta = None
    care = get_latest_care_intent(db, member_id)
    if care and readiness:
        draft_meta = build_outreach_draft(db, member_id, care, readiness)

    return record_decision(
        db, member_id, payload.action, payload.message,
        original_message=payload.original_message,
        message_class=draft_meta.message_class if draft_meta else "INFORMATIONAL",
        top_issue=(readiness.top_issue if readiness else "") or "",
    )


@router.get("/outreach/decisions/stats")
def decision_stats(db: Session = Depends(get_db)):
    return outreach_decision_stats(db)


# Retained so an older frontend build keeps working; both delegate to the single
# decision path above.
@router.post("/members/{member_id}/outreach/approve")
def approve(member_id: str, payload: OutreachActionRequest, db: Session = Depends(get_db)):
    return decision(member_id, payload, db)


@router.post("/members/{member_id}/outreach/reject")
def reject(member_id: str, payload: OutreachActionRequest, db: Session = Depends(get_db)):
    return decision(member_id, payload, db)
