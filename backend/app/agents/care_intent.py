import json
import time
from sqlalchemy.orm import Session
from app.config import settings
from app.schemas import CareIntentResult
from app.services.member_context import build_member_context, get_transcript
from app.services.settings_service import get_runtime_settings
from app.services.usage import estimate_tokens, log_usage
from app.agents.openai_provider import OpenAIProvider


CARE_CACHE: dict[tuple[str, float, int, int, bool, str], CareIntentResult] = {}
LATEST_CARE_RESULTS: dict[str, CareIntentResult] = {}

SYSTEM_PROMPT = """You are Agent 1, the Care Intent Agent for a payer Member Advocate support application.

Your task is administrative forecasting, not clinical decision-making. Review ONLY the supplied member enrollment/plan context, historical claims trajectory, and the member's most recent Agent Assist call summaries. Do not use prior-authorization records, provider-network records, future claims, or any facts not in the payload.

Decide whether the evidence supports a likely upcoming significant planned care event/procedure in roughly the next 30-60 days. Examples can include a knee replacement, hip replacement, cataract surgery, or another clearly supported procedure. Do not infer a procedure merely because a diagnosis, imaging test, or specialist visit exists. Explicit counterevidence such as 'not planning surgery', 'no surgery scheduled', or continued conservative treatment must materially lower confidence.

Also estimate the likelihood that the member will contact a Member Advocate again soon. This is a SEPARATE administrative signal and can be high even when upcoming-care confidence is low.

The confidence number is an evidence confidence score, not a calibrated clinical probability.

Use Agent Assist summaries first. If a summary is ambiguous and the exact wording of ONE recent call could materially change the assessment, set transcript_request_call_id to one of the supplied available_transcript_ids. Otherwise set it to null.

Return these JSON fields exactly:
{
  "member_id": "...",
  "care_intent": {
    "detected": true/false,
    "predicted_care_event": "..." or null,
    "care_category": "..." or null,
    "confidence": 0.0-1.0,
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
}

Keep evidence concise and source-grounded. Never reveal chain-of-thought. Never provide treatment recommendations."""

FINALIZE_WITH_TRANSCRIPT_PROMPT = SYSTEM_PROMPT + """

A full transcript requested by the first pass is now included as fallback_transcript. Reassess using it together with the original evidence. Return the same JSON format and set transcript_request_call_id to null. Do not request another transcript."""


def _model_packet(context: dict, threshold: float) -> dict:
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

def _normalize_payload(payload: dict, *, member_id: str, threshold: float, transcript_used: bool) -> dict:
    care = payload.setdefault("care_intent", {})
    confidence = float(care.get("confidence") or 0)
    confidence = max(0.0, min(1.0, confidence))
    event = _canonicalize_event(care.get("predicted_care_event") or None)
    care["predicted_care_event"] = event
    detected = bool(event) and confidence >= threshold
    care["confidence"] = confidence
    care["detected"] = detected
    if not detected and confidence < threshold:
        # The event may remain visible as a weak hypothesis, but readiness is not eligible.
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
    payload.pop("transcript_request_call_id", None)
    return payload


def get_latest_care_intent(member_id: str) -> CareIntentResult | None:
    return LATEST_CARE_RESULTS.get(member_id)


def get_all_latest_care_intents() -> dict[str, CareIntentResult]:
    return dict(LATEST_CARE_RESULTS)


async def analyze_care_intent(db: Session, member_id: str) -> CareIntentResult | None:
    context = build_member_context(db, member_id)
    if not context:
        return None
    if settings.use_mock_ai:
        raise RuntimeError("Mock AI is disabled for this version. Set USE_MOCK_AI=false and configure OPENAI_API_KEY.")

    runtime = get_runtime_settings(db)
    threshold = runtime["care_intent_threshold"]
    cache_key = (
        member_id,
        threshold,
        runtime["recent_call_limit"],
        runtime["claim_lookback_months"],
        runtime["enable_transcript_fallback"],
        settings.openai_model,
    )
    if cache_key in CARE_CACHE:
        result = CARE_CACHE[cache_key]
        LATEST_CARE_RESULTS[member_id] = result
        return result

    started = time.perf_counter()
    provider = OpenAIProvider()
    packet = _model_packet(context, threshold)
    input_text = json.dumps(packet, default=str)

    payload, usage = await provider.generate_json(system_prompt=SYSTEM_PROMPT, user_payload=packet)
    total_in = usage.get("input_tokens") or estimate_tokens(input_text)
    total_out = usage.get("output_tokens") or estimate_tokens(json.dumps(payload))
    transcript_used = False

    requested_call_id = payload.get("transcript_request_call_id")
    if (
        runtime["enable_transcript_fallback"]
        and requested_call_id
        and requested_call_id in context["available_transcript_ids"]
    ):
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
            )
            payload = second_payload
            total_in += second_usage.get("input_tokens") or estimate_tokens(json.dumps(second_packet, default=str))
            total_out += second_usage.get("output_tokens") or estimate_tokens(json.dumps(second_payload))

    payload = _normalize_payload(payload, member_id=member_id, threshold=threshold, transcript_used=transcript_used)
    result = CareIntentResult.model_validate(payload)
    latency = int((time.perf_counter() - started) * 1000)
    log_usage(
        db,
        agent_name="CARE_INTENT",
        member_id=member_id,
        input_tokens=total_in,
        output_tokens=total_out,
        latency_ms=latency,
        transcript_tool_invoked=transcript_used,
        mode=f"OPENAI:{settings.openai_model}",
    )
    CARE_CACHE[cache_key] = result
    LATEST_CARE_RESULTS[member_id] = result
    return result
