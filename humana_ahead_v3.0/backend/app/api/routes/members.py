from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.activity_filter import get_candidate_member_ids
from app.services.member_context import list_members, get_member_profile, build_member_context, get_recent_claims, get_recent_calls, get_transcript

router = APIRouter()


@router.get("/members")
def members(
    search: str = "",
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
    candidates_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Paginated member list.

    At real scale the working view is not an unbounded roster. The Tier-0
    activity filter already narrows to members with meaningful recent activity,
    so candidates_only exposes that worklist rather than the full population.
    """
    rows = list_members(db, search=search, limit=10_000)
    if candidates_only:
        candidate_ids = set(get_candidate_member_ids(db))
        rows = [r for r in rows if r["member_id"] in candidate_ids]
    total = len(rows)
    page = rows[offset: offset + limit]
    return {
        "members": page,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < total,
        "candidates_only": candidates_only,
    }

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
