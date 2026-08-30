from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import OutreachActionRequest
from app.agents.care_intent import get_latest_care_intent
from app.services.readiness import get_latest_readiness
from app.services.outreach import build_outreach_draft, record_decision

router = APIRouter()


@router.post("/members/{member_id}/outreach/draft")
def draft(member_id: str, db: Session = Depends(get_db)):
    # Outreach is downstream of explicit Agent 1 + Agent 2 actions. Never invoke either agent here.
    care = get_latest_care_intent(member_id)
    readiness = get_latest_readiness(member_id)
    if not care:
        raise HTTPException(409, detail={"error":"CARE_INTENT_REQUIRED","message":"Run the upcoming-procedure scan before drafting outreach."})
    if not readiness:
        raise HTTPException(409, detail={"error":"READINESS_REQUIRED","message":"Run the readiness assessment before drafting outreach."})
    return build_outreach_draft(db, member_id, care, readiness)


@router.post("/members/{member_id}/outreach/approve")
def approve(member_id: str, payload: OutreachActionRequest, db: Session = Depends(get_db)):
    return record_decision(db, member_id, "APPROVE", payload.message)


@router.post("/members/{member_id}/outreach/reject")
def reject(member_id: str, payload: OutreachActionRequest, db: Session = Depends(get_db)):
    action = "SAVE_FOR_REVIEW" if payload.action == "SAVE_FOR_REVIEW" else "REJECT"
    return record_decision(db, member_id, action, payload.message)
