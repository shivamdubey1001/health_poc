import asyncio
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.agents.care_intent import analyze_care_intent
from app.services.member_context import get_member_profile

router = APIRouter()

@router.get("/queue/ahead")
async def ahead_queue(limit: int = Query(40, ge=1, le=100), db: Session = Depends(get_db)):
    # Keep queue generation bounded. Showcase members are first; the rest are lightweight demo rows.
    ids = ["M0001","M0002","M0003","M0004","M0005","M0006"]
    rows = []
    for mid in ids[:limit]:
        profile = get_member_profile(db, mid)
        care = await analyze_care_intent(db, mid)
        rows.append({
            "member_id":mid, "member_name":profile["name"], "plan_name":profile["plan_name"],
            "predicted_care_event":care.care_intent.predicted_care_event or "No high-confidence care event",
            "care_intent_confidence":care.care_intent.confidence,
            "estimated_time_window":care.care_intent.estimated_time_window,
            "advocate_contact_risk":care.advocate_contact.risk_level,
            "advocate_contact_confidence":care.advocate_contact.confidence,
            "readiness": (85 if mid=="M0001" else 40 if mid=="M0002" else 90 if mid=="M0003" else 67 if mid=="M0004" else None) if care.recommended_action == "RUN_READINESS_ASSESSMENT" else None,
            "top_issue": "Transportation" if mid=="M0001" else "Facility network" if mid=="M0002" else "Authorization pending" if mid=="M0003" else "Facility / authorization review" if mid=="M0004" else "Monitor",
            "status":"READY_FOR_REVIEW" if care.recommended_action == "RUN_READINESS_ASSESSMENT" else "MONITOR",
        })
    return rows
