from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import OutreachActionRequest
from app.agents.care_intent import analyze_care_intent
from app.services.readiness import run_readiness_assessment
from app.services.outreach import build_outreach_draft, record_decision

router = APIRouter()

@router.post("/members/{member_id}/outreach/draft")
async def draft(member_id: str, db: Session = Depends(get_db)):
    care = await analyze_care_intent(db, member_id)
    if not care:
        raise HTTPException(404, "Member not found")
    try:
        readiness = run_readiness_assessment(db, member_id, care)
    except ValueError:
        raise HTTPException(409, detail={"error":"CARE_INTENT_BELOW_THRESHOLD","message":"Outreach draft is unavailable because care-intent confidence is below threshold."})
    return build_outreach_draft(db, member_id, care, readiness)

@router.post("/members/{member_id}/outreach/approve")
def approve(member_id: str, payload: OutreachActionRequest, db: Session = Depends(get_db)):
    return record_decision(db, member_id, "APPROVE", payload.message)

@router.post("/members/{member_id}/outreach/reject")
def reject(member_id: str, payload: OutreachActionRequest, db: Session = Depends(get_db)):
    action = "SAVE_FOR_REVIEW" if payload.action == "SAVE_FOR_REVIEW" else "REJECT"
    return record_decision(db, member_id, action, payload.message)
