from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.agents.care_intent import analyze_care_intent
from app.services.readiness import run_readiness_assessment, get_alternatives

router = APIRouter()

@router.post("/members/{member_id}/care-intent")
async def care_intent(member_id: str, db: Session = Depends(get_db)):
    result = await analyze_care_intent(db, member_id)
    if not result:
        raise HTTPException(404, "Member not found")
    return result

@router.post("/members/{member_id}/readiness")
async def readiness(member_id: str, db: Session = Depends(get_db)):
    care = await analyze_care_intent(db, member_id)
    if not care:
        raise HTTPException(404, "Member not found")
    try:
        return run_readiness_assessment(db, member_id, care)
    except ValueError as exc:
        if str(exc) == "CARE_INTENT_BELOW_THRESHOLD":
            raise HTTPException(409, detail={"error":"CARE_INTENT_BELOW_THRESHOLD","message":"Care Intent confidence is below the configured threshold. Continue monitoring."})
        raise

@router.get("/members/{member_id}/provider-alternatives")
def alternatives(member_id: str, specialty: str = Query(...), provider_type: str | None = None, db: Session = Depends(get_db)):
    return get_alternatives(db, member_id, specialty=specialty, provider_type=provider_type)
