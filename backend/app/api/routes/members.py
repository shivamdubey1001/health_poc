from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.member_context import list_members, get_member_profile, build_member_context, get_recent_claims, get_recent_calls, get_transcript

router = APIRouter()

@router.get("/members")
def members(search: str = "", limit: int = Query(250, ge=1, le=500), db: Session = Depends(get_db)):
    return list_members(db, search=search, limit=limit)

@router.get("/members/{member_id}")
def member(member_id: str, db: Session = Depends(get_db)):
    result = get_member_profile(db, member_id)
    if not result:
        raise HTTPException(404, "Member not found")
    return result

@router.get("/members/{member_id}/context")
def context(member_id: str, db: Session = Depends(get_db)):
    result = build_member_context(db, member_id)
    if not result:
        raise HTTPException(404, "Member not found")
    return result

@router.get("/members/{member_id}/claims")
def claims(member_id: str, db: Session = Depends(get_db)):
    if not get_member_profile(db, member_id):
        raise HTTPException(404, "Member not found")
    return get_recent_claims(db, member_id)

@router.get("/members/{member_id}/calls")
def calls(member_id: str, db: Session = Depends(get_db)):
    if not get_member_profile(db, member_id):
        raise HTTPException(404, "Member not found")
    return get_recent_calls(db, member_id)

@router.get("/calls/{call_id}/transcript")
def transcript(call_id: str, db: Session = Depends(get_db)):
    result = get_transcript(db, call_id)
    if not result:
        raise HTTPException(404, "Transcript not found")
    return result
