"""Agent 1 - Care Intent.

Reads plan context, historical claims trajectory and recent Agent Assist call
summaries, and judges whether a significant planned procedure is likely in the
near term.

Two design points worth stating explicitly:

* Prior-authorization and provider-network records are deliberately withheld.
  Predicting a procedure from an authorization is trivial and commercially
  useless, because most procedures never generate one. Forcing the prediction
  onto claims and conversation is the hard and valuable case - and it also makes
  authorization records usable as a held-out evaluation label.

* Confidence is produced against an explicit rubric rather than a bare 0-1
  scale. Without anchors, models emit a plausible-sounding number instead of
  discriminating between members, which shows up as identical scores across very
  different cases.
"""

import hashlib
import json
import time
from datetime import date

from sqlalchemy.orm import Session

from app.agents.openai_provider import OpenAIProvider
from app.config import settings
from app.schemas import CareIntentResult
from app.services import result_store
from app.services.member_context import build_member_context, get_transcript
from app.services.settings_service import get_runtime_settings
from app.services.usage import estimate_tokens, log_usage

SYSTEM_PROMPT = """You are Agent 1, the Care Intent Agent for a payer Member Advocate support application.

Your task is administrative forecasting, not clinical decision-making. Review ONLY the supplied member enrollment/plan context, historical claims trajectory, and the member's most recent Agent Assist call summaries. Do not use prior-authorization records, provider-network records, future claims, or any facts not in the payload.

Decide whether the evidence supports a likely upcoming significant planned care event/procedure in roughly the next 30-60 days. Examples can include a knee replacement, hip replacement, cataract surgery, or another clearly supported procedure. Do not infer a procedure merely because a diagnosis, imaging test, or specialist visit exists. Explicit counterevidence such as 'not planning surgery', 'no surgery scheduled', or continued conservative treatment must materially lower confidence.

CONFIDENCE RUBRIC - you must place confidence in the band whose conditions are met, and no higher:

0.85 - 1.00  The member, or a summary quoting the member, states that a specific procedure is scheduled, booked, or has been recommended and accepted. A date, a pre-operative step, or a surgical scheduling action is referenced.
0.70 - 0.84  A specialist has recommended or discussed a specific procedure as the next step, OR the claims trajectory shows a clear pre-procedural sequence (specialist consultation, then imaging, then pre-operative workup) AND a recent call is consistent with it. No explicit scheduling language.
0.45 - 0.69  A relevant clinical pathway is progressing - repeat specialist visits, imaging, injections, or escalating treatment - but no procedure has been named by anyone and no scheduling signal exists.
0.20 - 0.44  A relevant diagnosis or a single specialist or imaging encounter exists, with no progression and no procedure mentioned anywhere.
0.00 - 0.19  No care-intent signal. Billing, ID card, pharmacy, or general benefit questions only.

Apply these adjustments after choosing a band:
- Explicit denial of a planned procedure: reduce by at least 0.25.
- Documented continued conservative management with no escalation: reduce by at least 0.15.
- The most recent relevant activity is more than 120 days old: reduce by at least 0.10.

Two members with materially different evidence should not receive the same confidence. The number is an evidence confidence score, not a calibrated clinical probability.

Also estimate the likelihood that the member will contact a Member Advocate again soon. This is a SEPARATE administrative signal and can be high even when upcoming-care confidence is low.

Use Agent Assist summaries first. If a summary is ambiguous and the exact wording of ONE recent call could materially change the assessment, set transcript_request_call_id to one of the supplied available_transcript_ids. Otherwise set it to null.

Every evidence item must be traceable to something in the supplied payload. Do not cite facts that are not present. Keep evidence concise and source-grounded. Never reveal chain-of-thought. Never provide treatment recommendations.

Return these JSON fields exactly:
{
  "member_id": "...",
  "care_intent": {
    "detected": true/false,
    "predicted_care_event": "..." or null,
    "care_category": "..." or null,
    "confidence": 0.0-1.0,
    "confidence_band_reason": "which rubric band you applied and why, one short sentence",
    "estimated_time_window": "..." or null
  },
  "advocate_contact": {
    "risk_level": "LOW" | "MEDIUM" | "HIGH",
    "confidence": 0.0-1.0,
    "reason": "concise evidence-based explanation"
  },
  "evidence": [
    {"type":"CLAIM_TRAJECTORY|CALL_SUMMARY|TRANSCRIPT", "description":"concise observable evidence", "source_id":null-or-id, "date":null-or-date}
  ],
  "transcript_request_call_id": null-or-call-id
}"""

FINALIZE_WITH_TRANSCRIPT_PROMPT = SYSTEM_PROMPT + """

A full transcript requested by the first pass is now included as fallback_transcript. Reassess using it together with the original evidence. Return the same JSON format and set transcript_request_call_id to null. Do not request another transcript."""

# Strict schema. The API enforces the shape so a malformed response is a
# provider-side failure rather than a parsing gamble in our code.
CARE_INTENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["member_id", "care_intent", "advocate_contact", "evidence",
                 "transcript_request_call_id"],
    "properties": {
        "member_id": {"type": "string"},
        "care_intent": {
            "type": "object",
            "additionalProperties": False,
            "required": ["detected", "predicted_care_event", "care_category",
                         "confidence", "confidence_band_reason", "estimated_time_window"],
            "properties": {
                "detected": {"type": "boolean"},
                "predicted_care_event": {"type": ["string", "null"]},
                "care_category": {"type": ["string", "null"]},
                "confidence": {"type": "number"},
                "confidence_band_reason": {"type": "string"},
                "estimated_time_window": {"type": ["string", "null"]},
            },
        },
        "advocate_contact": {
            "type": "object",
            "additionalProperties": False,
            "required": ["risk_level", "confidence", "reason"],
            "properties": {
                "risk_level": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
                "confidence": {"type": "number"},
                "reason": {"type": "string"},
            },
        },
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["type", "description", "source_id", "date"],
                "properties": {
                    "type": {"type": "string"},
                    "description": {"type": "string"},
                    "source_id": {"type": ["string", "null"]},
                    "date": {"type": ["string", "null"]},
                },
            },
        },
        "transcript_request_call_id": {"type": ["string", "null"]},
    },
}


def build_model_packet(context: dict, threshold: float) -> dict:
    """The exact payload sent to the model. Carries member_id, age band and plan
    attributes only - no name, no date of birth, no address."""
    return {
        "member": {
            "member_id": context["member"]["member_id"],
            "age_band": context["member"]["age_band"],
            "plan_id": context["member"]["plan_id"],
            "plan_name": context["member"]["plan_name"],
            "plan_type": context["member"]["plan_type"],
            "coverage_status": context["member"]["coverage_status"],
        },
        "plan": context["plan"],
        "recent_claim_trajectory": context["recent_claim_trajectory"],
        "recent_claims": context["recent_claims"][-12:],
        "recent_agent_assist_summaries": context["recent_agent_assist_summaries"],
        "available_transcript_ids": context["available_transcript_ids"],
        "configured_readiness_threshold": threshold,
        "data_as_of": settings.data_as_of,
    }


def _canonicalize_event(event: str | None) -> str | None:
    if not event:
        return None
    text = event.strip()
    lower = text.lower()
    if "knee" in lower and any(k in lower for k in ["replacement", "arthroplasty"]):
        return "Total knee replacement"
    if "hip" in lower and any(k in lower for k in ["replacement", "arthroplasty"]):
        return "Total hip replacement"
    if "cataract" in lower and any(k in lower for k in ["surgery", "procedure", "extraction"]):
        return "Cataract surgery"
    return text


def confidence_band(confidence: float) -> str:
    """Displayed instead of a raw percentage.

    Two significant figures imply a precision that has not been earned while the
    score is uncalibrated. Bands communicate the same decision without the false
    precision, and the raw value remains available in the detail view.
    """
    if confidence >= 0.85:
        return "HIGH"
    if confidence >= 0.70:
        return "MODERATE_HIGH"
    if confidence >= 0.45:
        return "MODERATE"
    if confidence >= 0.20:
        return "LOW"
    return "MINIMAL"


def _normalize_payload(payload: dict, *, member_id: str, threshold: float,
                       transcript_used: bool) -> dict:
    care = payload.setdefault("care_intent", {})
    confidence = float(care.get("confidence") or 0)
    confidence = max(0.0, min(1.0, confidence))
    event = _canonicalize_event(care.get("predicted_care_event") or None)
    care["predicted_care_event"] = event
    # The gate is applied here, deterministically, rather than trusting the
    # model's own "detected" flag.
    detected = bool(event) and confidence >= threshold
    care["confidence"] = confidence
    care["confidence_band"] = confidence_band(confidence)
    care["detected"] = detected
    care.setdefault("confidence_band_reason", "")
    if not detected:
        care.setdefault("estimated_time_window", None)

    advocate = payload.setdefault("advocate_contact", {})
    risk = str(advocate.get("risk_level") or "LOW").upper()
    if risk not in {"LOW", "MEDIUM", "HIGH"}:
        risk = "LOW"
    advocate["risk_level"] = risk
    advocate["confidence"] = max(0.0, min(1.0, float(advocate.get("confidence") or 0)))
    advocate.setdefault("reason", "Insufficient evidence to characterize future contact risk.")

    payload["member_id"] = member_id
    payload["evidence"] = payload.get("evidence") or []
    payload["recommended_action"] = "RUN_READINESS_ASSESSMENT" if detected else "MONITOR"
    payload["threshold"] = threshold
    payload["transcript_tool_invoked"] = transcript_used
    payload["generated_by"] = f"OPENAI · {settings.openai_model}"
    payload["prompt_version"] = settings.prompt_version
    payload.pop("transcript_request_call_id", None)
    return payload


def _cache_key(member_id: str, runtime: dict, index_date: str) -> str:
    raw = json.dumps({
        "m": member_id,
        "t": runtime["care_intent_threshold"],
        "c": runtime["recent_call_limit"],
        "l": runtime["claim_lookback_months"],
        "f": runtime["enable_transcript_fallback"],
        "model": settings.openai_model,
        "pv": settings.prompt_version,
        "idx": index_date,
    }, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def get_latest_care_intent(db: Session, member_id: str) -> CareIntentResult | None:
    return result_store.get_latest_care_intent(db, member_id)


def get_all_latest_care_intents(db: Session) -> dict[str, CareIntentResult]:
    return result_store.all_latest_care_intents(db)


async def run_care_intent_on_packet(packet: dict, threshold: float, member_id: str,
                                    ) -> tuple[CareIntentResult, dict]:
    """Single assessment on a prepared packet. Used by the evaluation harness so
    perturbation and backtest runs share exactly the production code path."""
    provider = OpenAIProvider()
    payload, usage = await provider.generate_json(
        system_prompt=SYSTEM_PROMPT, user_payload=packet,
        schema=CARE_INTENT_SCHEMA, schema_name="care_intent",
    )
    payload = _normalize_payload(payload, member_id=member_id, threshold=threshold,
                                 transcript_used=False)
    return CareIntentResult.model_validate(payload), usage


async def analyze_care_intent(db: Session, member_id: str,
                              index_date: date | None = None) -> CareIntentResult | None:
    context = build_member_context(db, member_id, index_date=index_date)
    if not context:
        return None
    if settings.use_mock_ai:
        raise RuntimeError("Mock AI is disabled for this version. Set USE_MOCK_AI=false "
                           "and configure OPENAI_API_KEY.")

    runtime = get_runtime_settings(db)
    threshold = runtime["care_intent_threshold"]
    index_key = index_date.isoformat() if index_date else ""
    cache_key = _cache_key(member_id, runtime, index_key)

    cached = result_store.get_care_intent_by_key(db, cache_key)
    if cached:
        return cached

    started = time.perf_counter()
    provider = OpenAIProvider()
    packet = build_model_packet(context, threshold)

    payload, usage = await provider.generate_json(
        system_prompt=SYSTEM_PROMPT, user_payload=packet,
        schema=CARE_INTENT_SCHEMA, schema_name="care_intent",
    )
    total_in = usage.get("input_tokens") or estimate_tokens(json.dumps(packet, default=str))
    total_out = usage.get("output_tokens") or estimate_tokens(json.dumps(payload))
    token_source = "API" if usage.get("input_tokens") else "ESTIMATED"
    transcript_used = False

    requested_call_id = payload.get("transcript_request_call_id")
    if (runtime["enable_transcript_fallback"] and requested_call_id
            and requested_call_id in context["available_transcript_ids"]):
        transcript = get_transcript(db, requested_call_id)
        if transcript:
            transcript_used = True
            second_packet = dict(packet)
            second_packet["fallback_transcript"] = {
                "call_id": requested_call_id,
                "call_start_timestamp": transcript["call_start_timestamp"],
                "transcript_text": transcript["transcript_text"],
            }
            second_payload, second_usage = await provider.generate_json(
                system_prompt=FINALIZE_WITH_TRANSCRIPT_PROMPT,
                user_payload=second_packet,
                schema=CARE_INTENT_SCHEMA, schema_name="care_intent",
            )
            payload = second_payload
            total_in += second_usage.get("input_tokens") or estimate_tokens(
                json.dumps(second_packet, default=str))
            total_out += second_usage.get("output_tokens") or estimate_tokens(
                json.dumps(second_payload))
            usage = second_usage

    payload = _normalize_payload(payload, member_id=member_id, threshold=threshold,
                                 transcript_used=transcript_used)
    result = CareIntentResult.model_validate(payload)
    latency = int((time.perf_counter() - started) * 1000)

    log_usage(
        db, agent_name="CARE_INTENT", member_id=member_id,
        input_tokens=total_in, output_tokens=total_out, latency_ms=latency,
        transcript_tool_invoked=transcript_used,
        mode=f"OPENAI:{settings.openai_model}",
        correlation_id=usage.get("correlation_id", ""),
        prompt_version=settings.prompt_version,
        token_source=token_source,
    )
    result_store.save_care_intent(
        db, cache_key=cache_key, member_id=member_id, index_date=index_key,
        result=result, prompt_version=settings.prompt_version,
        model=settings.openai_model, correlation_id=usage.get("correlation_id", ""),
    )
    return result
