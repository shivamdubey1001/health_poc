"""Durable storage for agent results.

Results previously lived in module-level dicts, which meant a restart lost every
assessment and a second uvicorn worker saw none of them. The cache key was
already content-addressed on member, threshold, window settings and model, so
persistence is a table rather than a redesign - and it gives the audit trail a
regulated workflow needs.
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app import models
from app.schemas import CareIntentResult, ReadinessResult


# ------------------------------------------------------------------ care intent
def save_care_intent(db: Session, *, cache_key: str, member_id: str, index_date: str,
                     result: CareIntentResult, prompt_version: str, model: str,
                     correlation_id: str) -> None:
    row = db.query(models.CareIntentRecord).filter_by(cache_key=cache_key).first()
    payload = result.model_dump_json()
    if row:
        row.payload_json = payload
        row.confidence = result.care_intent.confidence
        row.predicted_care_event = result.care_intent.predicted_care_event or ""
        row.detected = result.care_intent.detected
        row.correlation_id = correlation_id
    else:
        db.add(models.CareIntentRecord(
            cache_key=cache_key, member_id=member_id, index_date=index_date,
            payload_json=payload, confidence=result.care_intent.confidence,
            predicted_care_event=result.care_intent.predicted_care_event or "",
            detected=result.care_intent.detected, prompt_version=prompt_version,
            model=model, correlation_id=correlation_id,
        ))
    db.commit()


def get_care_intent_by_key(db: Session, cache_key: str) -> CareIntentResult | None:
    row = db.query(models.CareIntentRecord).filter_by(cache_key=cache_key).first()
    return CareIntentResult.model_validate_json(row.payload_json) if row else None


def get_latest_care_intent(db: Session, member_id: str) -> CareIntentResult | None:
    row = (db.query(models.CareIntentRecord)
           .filter_by(member_id=member_id, index_date="")
           .order_by(models.CareIntentRecord.created_at.desc())
           .first())
    return CareIntentResult.model_validate_json(row.payload_json) if row else None


def all_latest_care_intents(db: Session) -> dict[str, CareIntentResult]:
    out: dict[str, CareIntentResult] = {}
    rows = (db.query(models.CareIntentRecord)
            .filter_by(index_date="")
            .order_by(models.CareIntentRecord.created_at.asc()).all())
    for r in rows:
        out[r.member_id] = CareIntentResult.model_validate_json(r.payload_json)
    return out


# -------------------------------------------------------------------- readiness
def save_readiness(db: Session, *, cache_key: str, member_id: str,
                   result: ReadinessResult, model: str) -> None:
    row = db.query(models.ReadinessRecord).filter_by(cache_key=cache_key).first()
    payload = result.model_dump_json()
    if row:
        row.payload_json = payload
        row.readiness_score = result.readiness_score
        row.top_issue = result.top_issue or ""
    else:
        db.add(models.ReadinessRecord(
            cache_key=cache_key, member_id=member_id, payload_json=payload,
            readiness_score=result.readiness_score, top_issue=result.top_issue or "",
            model=model,
        ))
    db.commit()


def get_readiness_by_key(db: Session, cache_key: str) -> ReadinessResult | None:
    row = db.query(models.ReadinessRecord).filter_by(cache_key=cache_key).first()
    return ReadinessResult.model_validate_json(row.payload_json) if row else None


def get_latest_readiness(db: Session, member_id: str) -> ReadinessResult | None:
    row = (db.query(models.ReadinessRecord)
           .filter_by(member_id=member_id)
           .order_by(models.ReadinessRecord.created_at.desc()).first())
    return ReadinessResult.model_validate_json(row.payload_json) if row else None


def all_latest_readiness(db: Session) -> dict[str, ReadinessResult]:
    out: dict[str, ReadinessResult] = {}
    rows = (db.query(models.ReadinessRecord)
            .order_by(models.ReadinessRecord.created_at.asc()).all())
    for r in rows:
        out[r.member_id] = ReadinessResult.model_validate_json(r.payload_json)
    return out
