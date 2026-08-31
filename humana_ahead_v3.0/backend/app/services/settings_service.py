from sqlalchemy.orm import Session
from app import models

DEFAULTS = {
    "care_intent_threshold": "0.70",
    "recent_call_limit": "6",
    "claim_lookback_months": "12",
    "enable_transcript_fallback": "true",
}


def get_runtime_settings(db: Session) -> dict:
    rows = {r.key: r.value for r in db.query(models.AppSetting).all()}
    merged = {**DEFAULTS, **rows}
    return {
        "care_intent_threshold": float(merged["care_intent_threshold"]),
        "recent_call_limit": int(merged["recent_call_limit"]),
        "claim_lookback_months": int(merged["claim_lookback_months"]),
        "enable_transcript_fallback": merged["enable_transcript_fallback"].lower() == "true",
        "require_advocate_approval": True,
    }


def update_runtime_settings(db: Session, payload: dict) -> dict:
    for key, value in payload.items():
        if value is None or key == "require_advocate_approval":
            continue
        row = db.get(models.AppSetting, key)
        text = str(value).lower() if isinstance(value, bool) else str(value)
        if row:
            row.value = text
        else:
            db.add(models.AppSetting(key=key, value=text))
    db.commit()
    return get_runtime_settings(db)
