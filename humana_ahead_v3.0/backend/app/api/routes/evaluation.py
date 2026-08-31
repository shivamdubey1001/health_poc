"""Evaluation endpoints.

Deliberately the only module that reads the eval_labels table. Nothing in the
assessment path imports this file, so the separation between what the model sees
and what grades it is enforced by structure rather than by convention.
"""

import asyncio
import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models
from app.agents.care_intent import (
    analyze_care_intent, build_model_packet, run_care_intent_on_packet,
)
from app.config import settings
from app.database import SessionLocal, get_db
from app.schemas import EvalRunRequest, PerturbationRequest
from app.services import eval_service
from app.services.activity_filter import get_candidate_member_ids
from app.services.member_context import build_member_context
from app.services.settings_service import get_runtime_settings

router = APIRouter()


@router.get("/eval/labels")
def labels(db: Session = Depends(get_db)):
    rows = db.query(models.EvalLabel).all()
    if not rows:
        summary = eval_service.rebuild_labels(db)
        rows = db.query(models.EvalLabel).all()
    else:
        counts: dict[str, int] = {}
        for r in rows:
            counts[r.label] = counts.get(r.label, 0) + 1
        summary = {"total": len(rows), "by_label": counts,
                   "index_date": rows[0].index_date if rows else ""}
    return {
        **summary,
        "method": (
            "Labels are derived from prior-authorization records. Agent 1's system "
            "prompt explicitly forbids it from seeing prior-authorization or "
            "provider-network data, so these are genuinely held out."
        ),
        "limitation": (
            "A member can have a real procedure with no authorization on file, and "
            "that population is exactly what this product exists to find. Members "
            "labelled NO_EVIDENCE are therefore treated as negatives, which makes "
            "measured precision a lower bound rather than a point estimate. "
            "AMBIGUOUS members are excluded from scoring entirely."
        ),
        "examples": [
            {"member_id": r.member_id, "label": r.label,
             "actual_procedure": r.actual_procedure,
             "actual_service_date": r.actual_service_date,
             "days_from_index": r.days_from_index}
            for r in rows if r.label == "UPCOMING_PROCEDURE"
        ][:10],
    }


@router.post("/eval/labels/rebuild")
def rebuild(index_date: str | None = None, db: Session = Depends(get_db)):
    idx = date.fromisoformat(index_date) if index_date else None
    return eval_service.rebuild_labels(db, idx)


@router.post("/eval/backtest")
async def backtest(request: EvalRunRequest, db: Session = Depends(get_db)):
    """Score Agent 1 against held-out labels.

    Supplying an index_date hides every claim and call after that date, so the
    model sees only what was knowable then. That is what makes a real precision
    and recall number available today instead of in ninety days.
    """
    idx = date.fromisoformat(request.index_date) if request.index_date else None
    runtime = get_runtime_settings(db)
    threshold = request.threshold or runtime["care_intent_threshold"]

    if not db.query(models.EvalLabel).first():
        eval_service.rebuild_labels(db, idx)

    if request.member_ids:
        member_ids = request.member_ids[: request.limit]
    else:
        # Stratify so a small run contains both positives and negatives; scoring
        # a sample of only positives would be meaningless.
        labels = eval_service.get_labels(db)
        candidates = get_candidate_member_ids(db)
        positives = [m for m in candidates if labels.get(m) and labels[m].label == "UPCOMING_PROCEDURE"]
        negatives = [m for m in candidates if labels.get(m) and labels[m].label == "NO_EVIDENCE"]
        take_pos = min(len(positives), max(1, request.limit // 2))
        member_ids = positives[:take_pos] + negatives[: request.limit - take_pos]

    if not member_ids:
        raise HTTPException(400, detail={"error": "NO_MEMBERS",
                                         "message": "No labelled members available to score."})

    run_id = eval_service.new_run(db, "backtest", request.index_date or "", threshold, len(member_ids))
    semaphore = asyncio.Semaphore(settings.scan_concurrency)
    predictions: list[dict] = []
    grounded_scores: list[float] = []

    async def assess(member_id: str):
        async with semaphore:
            with SessionLocal() as scoped:
                try:
                    result = await analyze_care_intent(scoped, member_id, index_date=idx)
                except RuntimeError as exc:
                    return {"member_id": member_id, "error": str(exc)}
                if not result:
                    return {"member_id": member_id, "error": "MEMBER_NOT_FOUND"}
                context = build_member_context(scoped, member_id, index_date=idx)
                packet = build_model_packet(context, threshold) if context else {}
                g = eval_service.groundedness([e.model_dump() for e in result.evidence], packet)
                return {
                    "member_id": member_id,
                    "confidence": result.care_intent.confidence,
                    "predicted_care_event": result.care_intent.predicted_care_event,
                    "confidence_band": result.care_intent.confidence_band,
                    "groundedness": g["score"],
                }

    try:
        rows = await asyncio.gather(*(assess(m) for m in member_ids))
    except Exception as exc:  # noqa: BLE001
        eval_service.fail_run(db, run_id, str(exc))
        raise HTTPException(503, detail={"error": "EVAL_FAILED", "message": str(exc)})

    errors = [r for r in rows if r.get("error")]
    for r in rows:
        if r.get("error"):
            continue
        predictions.append(r)
        grounded_scores.append(r["groundedness"])

    if not predictions:
        eval_service.fail_run(db, run_id, "All assessments failed.")
        raise HTTPException(503, detail={
            "error": "EVAL_FAILED",
            "message": errors[0].get("error", "All assessments failed."),
        })

    scored = eval_service.score_predictions(db, predictions, threshold)
    sweep = eval_service.threshold_sweep(db, predictions)
    result = {
        "run_id": run_id,
        "index_date": request.index_date or settings.data_as_of,
        "model": settings.openai_model,
        "prompt_version": settings.prompt_version,
        "members_assessed": len(predictions),
        "failed": len(errors),
        "scored": scored,
        "threshold_sweep": sweep,
        "mean_groundedness": round(sum(grounded_scores) / len(grounded_scores), 3),
        "groundedness_note": (
            "Fraction of cited evidence whose content appears in the payload the "
            "model was given. Requires no outcome label and catches fabrication."
        ),
    }
    eval_service.finish_run(db, run_id, result)
    return result


@router.get("/eval/runs")
def runs(db: Session = Depends(get_db)):
    rows = (db.query(models.EvalRun)
            .order_by(models.EvalRun.created_at.desc()).limit(20).all())
    return [{
        "run_id": r.run_id, "kind": r.kind, "status": r.status,
        "index_date": r.index_date, "threshold": r.threshold,
        "model": r.model, "prompt_version": r.prompt_version,
        "total": r.total, "created_at": r.created_at.isoformat() if r.created_at else "",
        "result": json.loads(r.result_json) if r.result_json else None,
        "error": r.error,
    } for r in rows]


@router.post("/eval/perturbation")
async def perturbation(request: PerturbationRequest, db: Session = Depends(get_db)):
    """Does confidence actually respond to evidence?

    Three runs on one member: unchanged, with procedure mentions stripped from
    the call summaries, and with an explicit denial appended. Confidence should
    fall in both altered variants. Flat confidence across all three is evidence
    of anchoring rather than reasoning, and is the strongest argument for
    reporting bands instead of a two-significant-figure percentage.
    """
    context = build_member_context(db, request.member_id)
    if not context:
        raise HTTPException(404, "Member not found")
    threshold = get_runtime_settings(db)["care_intent_threshold"]
    packet = build_model_packet(context, threshold)
    cases = eval_service.perturbation_cases(packet)

    async def run_case(name: str, case_packet: dict):
        try:
            result, _ = await run_care_intent_on_packet(case_packet, threshold, request.member_id)
            return name, result.care_intent.confidence, result.care_intent.predicted_care_event
        except RuntimeError as exc:
            raise HTTPException(503, detail={"error": "OPENAI_UNAVAILABLE", "message": str(exc)})

    results = await asyncio.gather(*(run_case(n, p) for n, p in cases.items()))
    by_name = {n: (c, e) for n, c, e in results}

    verdict = eval_service.perturbation_verdict(
        by_name["baseline"][0], by_name["stripped"][0], by_name["contradicted"][0],
    )
    return {
        "member_id": request.member_id,
        "cases": [
            {"case": n, "confidence": c, "predicted_care_event": e,
             "description": {
                 "baseline": "Unchanged payload.",
                 "stripped": "Sentences naming a procedure removed from call summaries.",
                 "contradicted": "An explicit statement that no surgery is scheduled appended.",
             }[n]}
            for n, (c, e) in by_name.items()
        ],
        "verdict": verdict,
    }


@router.post("/eval/consistency")
async def consistency(member_id: str, runs_count: int = Query(3, ge=2, le=5),
                      db: Session = Depends(get_db)):
    """Run the same member repeatedly and report the spread.

    With temperature pinned to zero the spread should be zero. A non-zero spread
    means any single reported confidence is not reproducible, which would
    undermine every evaluation number.
    """
    context = build_member_context(db, member_id)
    if not context:
        raise HTTPException(404, "Member not found")
    threshold = get_runtime_settings(db)["care_intent_threshold"]
    packet = build_model_packet(context, threshold)

    confidences: list[float] = []
    for _ in range(runs_count):
        try:
            result, _ = await run_care_intent_on_packet(packet, threshold, member_id)
        except RuntimeError as exc:
            raise HTTPException(503, detail={"error": "OPENAI_UNAVAILABLE", "message": str(exc)})
        confidences.append(result.care_intent.confidence)

    stats = eval_service.consistency(confidences)
    stats["temperature"] = settings.openai_temperature
    stats["confidences"] = confidences
    stats["interpretation"] = (
        "Zero spread confirms the assessment is reproducible, which is a "
        "precondition for any evaluation number being meaningful."
        if stats.get("spread", 0) == 0 else
        "Non-zero spread means the same input produces different assessments, so "
        "a single reported confidence cannot be relied upon."
    )
    return stats
