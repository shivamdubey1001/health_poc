from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.schemas import MemberBatchRequest
from app.agents.care_intent import analyze_care_intent, get_latest_care_intent
from app.services.readiness import analyze_readiness, get_alternatives, get_latest_readiness
from app.services.member_context import get_member_profile

router = APIRouter()


def _guard_batch(member_ids: list[str]):
    if len(member_ids) > settings.max_scan_batch:
        raise HTTPException(
            400,
            detail={
                "error": "BATCH_LIMIT_EXCEEDED",
                "message": f"Select {settings.max_scan_batch} or fewer members per scan to control API cost and latency.",
            },
        )


def _openai_error(exc: RuntimeError):
    raise HTTPException(503, detail={"error": "OPENAI_UNAVAILABLE", "message": str(exc)})


@router.post("/members/{member_id}/care-intent")
async def care_intent(member_id: str, db: Session = Depends(get_db)):
    try:
        result = await analyze_care_intent(db, member_id)
    except RuntimeError as exc:
        _openai_error(exc)
    if not result:
        raise HTTPException(404, "Member not found")
    return result


@router.get("/members/{member_id}/care-intent/latest")
def latest_care_intent(member_id: str):
    result = get_latest_care_intent(member_id)
    if not result:
        raise HTTPException(404, detail={"error": "ASSESSMENT_NOT_RUN", "message": "Run the upcoming-procedure scan for this member first."})
    return result


@router.post("/assessments/care-intent")
async def care_intent_batch(request: MemberBatchRequest, db: Session = Depends(get_db)):
    _guard_batch(request.member_ids)
    rows = []
    for member_id in request.member_ids:
        member = get_member_profile(db, member_id)
        if not member:
            rows.append({"member_id": member_id, "error": "MEMBER_NOT_FOUND"})
            continue
        try:
            assessment = await analyze_care_intent(db, member_id)
        except RuntimeError as exc:
            _openai_error(exc)
        rows.append({"member": member, "assessment": assessment.model_dump()})
    return {
        "selected_count": len(request.member_ids),
        "model": settings.openai_model,
        "threshold": settings.care_intent_threshold,
        "results": rows,
    }


@router.post("/members/{member_id}/readiness")
async def readiness(member_id: str, db: Session = Depends(get_db)):
    care = get_latest_care_intent(member_id)
    if not care:
        raise HTTPException(409, detail={
            "error": "CARE_INTENT_REQUIRED",
            "message": "Run Agent 1 for this member before running readiness. Agent 1 will not be called automatically.",
        })
    try:
        return await analyze_readiness(db, member_id, care)
    except ValueError as exc:
        if str(exc) == "CARE_INTENT_BELOW_THRESHOLD":
            raise HTTPException(409, detail={
                "error": "CARE_INTENT_BELOW_THRESHOLD",
                "message": "Care Intent confidence is below the configured threshold. Continue monitoring.",
            })
        raise
    except RuntimeError as exc:
        _openai_error(exc)


@router.get("/members/{member_id}/readiness/latest")
def latest_readiness(member_id: str):
    result = get_latest_readiness(member_id)
    if not result:
        raise HTTPException(404, detail={"error": "READINESS_NOT_RUN", "message": "Run the readiness assessment first."})
    return result


@router.post("/assessments/readiness")
async def readiness_batch(request: MemberBatchRequest, db: Session = Depends(get_db)):
    _guard_batch(request.member_ids)
    results = []
    skipped = []
    for member_id in request.member_ids:
        care = get_latest_care_intent(member_id)
        if not care:
            skipped.append({"member_id": member_id, "reason": "CARE_INTENT_REQUIRED"})
            continue
        if care.recommended_action != "RUN_READINESS_ASSESSMENT":
            skipped.append({"member_id": member_id, "reason": "CARE_INTENT_BELOW_THRESHOLD"})
            continue
        member = get_member_profile(db, member_id)
        try:
            readiness = await analyze_readiness(db, member_id, care)
        except RuntimeError as exc:
            _openai_error(exc)
        results.append({"member": member, "care_intent": care.model_dump(), "readiness": readiness.model_dump()})
    return {
        "selected_count": len(request.member_ids),
        "processed_count": len(results),
        "model": settings.openai_model,
        "results": results,
        "skipped": skipped,
    }


@router.get("/members/{member_id}/provider-alternatives")
def alternatives(member_id: str, specialty: str = Query(...), provider_type: str | None = None, db: Session = Depends(get_db)):
    return get_alternatives(db, member_id, specialty=specialty, provider_type=provider_type)
