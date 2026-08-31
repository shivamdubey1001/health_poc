import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.care_intent import analyze_care_intent, get_latest_care_intent
from app.config import settings
from app.database import SessionLocal, get_db
from app.schemas import MemberBatchRequest
from app.services.member_context import get_member_profile
from app.services.readiness import analyze_readiness, get_alternatives, get_latest_readiness

router = APIRouter()

UNSUPPORTED_MESSAGE = (
    "Readiness is configured for knee replacement, hip replacement and cataract "
    "surgery. Agent 1 can predict other procedures, but the readiness checklist "
    "requires a benefit-group mapping for each procedure family, which is "
    "configuration rather than code. This member's predicted procedure has no "
    "mapping yet, so no readiness score is produced rather than an unreliable one."
)


def _guard_batch(member_ids: list[str]):
    if len(member_ids) > settings.max_scan_batch:
        raise HTTPException(400, detail={
            "error": "BATCH_LIMIT_EXCEEDED",
            "message": f"Select {settings.max_scan_batch} or fewer members per scan "
                       f"to control API cost and latency.",
        })


def _openai_error(exc: RuntimeError):
    raise HTTPException(503, detail={"error": "OPENAI_UNAVAILABLE", "message": str(exc)})


async def _bounded(coro_factory, semaphore: asyncio.Semaphore):
    async with semaphore:
        return await coro_factory()


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
def latest_care_intent(member_id: str, db: Session = Depends(get_db)):
    result = get_latest_care_intent(db, member_id)
    if not result:
        raise HTTPException(404, detail={
            "error": "ASSESSMENT_NOT_RUN",
            "message": "Run the upcoming-procedure scan for this member first.",
        })
    return result


@router.post("/assessments/care-intent")
async def care_intent_batch(request: MemberBatchRequest, db: Session = Depends(get_db)):
    """Assess the selected members concurrently.

    Running serially meant a 25-member scan took roughly two minutes of wall time
    with no partial feedback. A small semaphore keeps us inside provider rate
    limits while cutting that by roughly the concurrency factor. Each member gets
    its own database session because SQLAlchemy sessions are not thread-safe and
    these coroutines interleave.
    """
    _guard_batch(request.member_ids)
    known = {mid: get_member_profile(db, mid) for mid in request.member_ids}
    semaphore = asyncio.Semaphore(settings.scan_concurrency)

    async def assess(member_id: str):
        if not known.get(member_id):
            return {"member_id": member_id, "error": "MEMBER_NOT_FOUND"}

        async def run():
            with SessionLocal() as scoped:
                try:
                    assessment = await analyze_care_intent(scoped, member_id)
                except RuntimeError as exc:
                    return {"member_id": member_id, "error": "OPENAI_UNAVAILABLE",
                            "message": str(exc)}
                if not assessment:
                    return {"member_id": member_id, "error": "MEMBER_NOT_FOUND"}
                return {"member": known[member_id], "assessment": assessment.model_dump()}

        return await _bounded(run, semaphore)

    rows = await asyncio.gather(*(assess(mid) for mid in request.member_ids))

    failures = [r for r in rows if r.get("error") == "OPENAI_UNAVAILABLE"]
    if failures and len(failures) == len(rows):
        raise HTTPException(503, detail={
            "error": "OPENAI_UNAVAILABLE",
            "message": failures[0].get("message", "The model provider is unavailable."),
        })

    return {
        "selected_count": len(request.member_ids),
        "model": settings.openai_model,
        "threshold": settings.care_intent_threshold,
        "concurrency": settings.scan_concurrency,
        "failed_count": len(failures),
        "results": list(rows),
    }


@router.post("/members/{member_id}/readiness")
async def readiness(member_id: str, db: Session = Depends(get_db)):
    care = get_latest_care_intent(db, member_id)
    if not care:
        raise HTTPException(409, detail={
            "error": "CARE_INTENT_REQUIRED",
            "message": "Run Agent 1 for this member before running readiness. "
                       "Agent 1 will not be called automatically.",
        })
    try:
        return await analyze_readiness(db, member_id, care)
    except ValueError as exc:
        code = str(exc)
        if code == "CARE_INTENT_BELOW_THRESHOLD":
            raise HTTPException(409, detail={
                "error": code,
                "message": "Care intent confidence is below the configured threshold, "
                           "so readiness is not eligible for this member.",
            })
        if code == "SERVICE_GROUP_UNSUPPORTED":
            raise HTTPException(422, detail={
                "error": code, "message": UNSUPPORTED_MESSAGE,
            })
        raise HTTPException(400, detail={"error": code, "message": code})
    except RuntimeError as exc:
        _openai_error(exc)


@router.get("/members/{member_id}/readiness/latest")
def latest_readiness(member_id: str, db: Session = Depends(get_db)):
    result = get_latest_readiness(db, member_id)
    if not result:
        raise HTTPException(404, detail={
            "error": "READINESS_NOT_RUN",
            "message": "Run the readiness assessment for this member first.",
        })
    return result


@router.post("/assessments/readiness")
async def readiness_batch(request: MemberBatchRequest, db: Session = Depends(get_db)):
    """Run Agent 2 for the explicitly selected members, concurrently.

    Members that cannot be assessed are returned in `skipped` with a reason
    rather than being silently dropped, so the interface can explain the gap -
    a procedure outside the configured readiness scope, or Agent 1 not yet run
    for that member.
    """
    _guard_batch(request.member_ids)
    semaphore = asyncio.Semaphore(settings.scan_concurrency)

    async def assess(member_id: str):
        async def run():
            with SessionLocal() as scoped:
                profile = get_member_profile(scoped, member_id)
                if not profile:
                    return {"skipped": {"member_id": member_id,
                                        "reason": "Member not found."}}
                care = get_latest_care_intent(scoped, member_id)
                if not care:
                    return {"skipped": {"member_id": member_id,
                                        "reason": "Run the upcoming-procedure scan for this member first."}}
                try:
                    result = await analyze_readiness(scoped, member_id, care)
                except ValueError as exc:
                    reason = (UNSUPPORTED_MESSAGE if str(exc) == "SERVICE_GROUP_UNSUPPORTED"
                              else "Care intent confidence is below the configured threshold."
                              if str(exc) == "CARE_INTENT_BELOW_THRESHOLD" else str(exc))
                    return {"skipped": {"member_id": member_id, "reason": reason}}
                except RuntimeError as exc:
                    return {"skipped": {"member_id": member_id, "reason": str(exc)}}
                return {"row": {
                    "member": profile,
                    "care_intent": care.model_dump(),
                    "readiness": result.model_dump(),
                }}

        return await _bounded(run, semaphore)

    outcomes = await asyncio.gather(*(assess(mid) for mid in request.member_ids))
    results = [o["row"] for o in outcomes if "row" in o]
    skipped = [o["skipped"] for o in outcomes if "skipped" in o]
    return {
        "selected_count": len(request.member_ids),
        "processed_count": len(results),
        "model": settings.openai_model,
        "concurrency": settings.scan_concurrency,
        "results": results,
        "skipped": skipped,
    }


@router.get("/members/{member_id}/alternatives")
def alternatives(member_id: str, specialty: str = "", provider_type: str = "",
                 db: Session = Depends(get_db)):
    return get_alternatives(db, member_id, specialty, provider_type or None)
