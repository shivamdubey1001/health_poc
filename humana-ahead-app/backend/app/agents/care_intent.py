import json, time
from sqlalchemy.orm import Session
from app.config import settings
from app.schemas import CareIntentResult
from app.services.member_context import build_member_context, get_transcript
from app.services.settings_service import get_runtime_settings
from app.services.usage import estimate_tokens, log_usage
from app.agents.openai_provider import OpenAIProvider

DEMO = {
    "M0001": {"event":"Total knee replacement","category":"Orthopedic surgery","confidence":0.86,"window":"4–6 weeks","contact":"HIGH","contact_conf":0.78,"reason":"Repeated benefit and network questions as orthopedic care progresses."},
    "M0002": {"event":"Total knee replacement","category":"Orthopedic surgery","confidence":0.91,"window":"3–5 weeks","contact":"HIGH","contact_conf":0.82,"reason":"Member has progressively contacted the plan about surgeon, facility and surgical coverage."},
    "M0003": {"event":"Total hip replacement","category":"Orthopedic surgery","confidence":0.84,"window":"3–5 weeks","contact":"HIGH","contact_conf":0.76,"reason":"Recent calls focus on a possible hip procedure and unresolved administrative review."},
    "M0004": {"event":"Cataract surgery","category":"Ophthalmic surgery","confidence":0.82,"window":"2–4 weeks","contact":"MEDIUM","contact_conf":0.68,"reason":"Member expects scheduling details and indicated they may call back once finalized."},
    "M0005": {"event":None,"category":None,"confidence":0.42,"window":None,"contact":"LOW","contact_conf":0.35,"reason":"Recent calls emphasize continued conservative treatment rather than a scheduled procedure."},
    "M0006": {"event":None,"category":None,"confidence":0.24,"window":None,"contact":"HIGH","contact_conf":0.90,"reason":"Repeated unresolved billing follow-ups make another advocate contact likely even without a surgery trajectory."},
}

CARE_CACHE: dict[tuple[str, float, int, int, bool], CareIntentResult] = {}

SYSTEM_PROMPT = """You are the Care Intent Agent for a payer Member Advocate support system.
Use only administrative evidence in the supplied member packet: member/plan context, recent claims trajectory and recent Agent Assist summaries.
Identify an upcoming significant care event only when multiple pieces of evidence support it. Pay special attention to explicit counterevidence such as 'not planning surgery' or 'continue therapy'.
Do not diagnose or recommend treatment. A confidence score is an internal evidence confidence, not a clinical probability.
Return JSON with member_id, care_intent {detected,predicted_care_event,care_category,confidence,estimated_time_window}, advocate_contact {risk_level,confidence,reason}, evidence [{type,description,source_id,date}], recommended_action, transcript_tool_invoked, generated_by.
If care confidence is below threshold, recommended_action must be MONITOR."""


def _build_evidence(context: dict, max_items: int = 5) -> list[dict]:
    evidence = []
    trajectory = context.get("recent_claim_trajectory", [])
    ortho = [x for x in trajectory if any(k in x.lower() for k in ["knee", "hip", "mri", "joint", "therapeutic", "orthopedic"])]
    eye = [x for x in trajectory if any(k in x.lower() for k in ["ophthalm", "cataract", "biometry"])]
    chosen = ortho[-5:] or eye[-5:] or trajectory[-4:]
    if chosen:
        evidence.append({"type":"CLAIM_TRAJECTORY","description":" → ".join(chosen),"source_id":None,"date":None})
    calls = context.get("recent_calls", [])
    for c in calls[-4:]:
        if c.get("summary"):
            evidence.append({"type":"CALL_SUMMARY","description":c["summary"],"source_id":c["call_id"],"date":c["timestamp"][:10]})
    return evidence[:max_items]


def _heuristic(context: dict, threshold: float) -> dict:
    mid = context["member"]["member_id"]
    if mid in DEMO:
        d = DEMO[mid]
        detected = d["confidence"] >= threshold and bool(d["event"])
        return {
            "member_id": mid,
            "care_intent": {"detected": detected, "predicted_care_event": d["event"], "care_category": d["category"], "confidence": d["confidence"], "estimated_time_window": d["window"]},
            "advocate_contact": {"risk_level": d["contact"], "confidence": d["contact_conf"], "reason": d["reason"]},
            "evidence": _build_evidence(context),
            "recommended_action": "RUN_READINESS_ASSESSMENT" if detected else "MONITOR",
            "threshold": threshold,
            "transcript_tool_invoked": False,
            "generated_by": "MOCK_AI",
        }

    text = " ".join((c.get("summary") or "") + " " + (c.get("follow_up_note") or "") for c in context.get("recent_calls", [])).lower()
    claim_text = " ".join((c.get("diagnosis_description") or "") + " " + (c.get("procedure_description") or "") for c in context.get("recent_claims", [])).lower()
    negative = any(x in text for x in ["no surgery scheduled", "not planning surgery", "continue conservative", "continue therapy"])
    knee = "knee" in text and any(x in text for x in ["replacement", "procedure", "surgery"])
    hip = "hip" in text and any(x in text for x in ["replacement", "procedure", "surgery"])
    cataract = "cataract" in text and "surgery" in text
    progression = sum(k in claim_text for k in ["mri", "therapeutic exercise", "joint injection", "orthopedic"])
    score = 0.18 + min(0.28, progression * 0.07)
    event = category = None
    if knee:
        event, category, score = "Total knee replacement", "Orthopedic surgery", score + 0.42
    elif hip:
        event, category, score = "Total hip replacement", "Orthopedic surgery", score + 0.42
    elif cataract:
        event, category, score = "Cataract surgery", "Ophthalmic surgery", score + 0.45
    if negative:
        score -= 0.35
    score = max(0.05, min(0.95, round(score, 2)))
    calls = context.get("recent_calls", [])
    followups = sum(bool(c.get("follow_up_required")) for c in calls)
    contact_conf = min(0.92, round(0.2 + 0.09 * len(calls) + 0.12 * followups, 2))
    risk = "HIGH" if contact_conf >= 0.72 else "MEDIUM" if contact_conf >= 0.45 else "LOW"
    detected = score >= threshold and event is not None
    return {
        "member_id": mid,
        "care_intent": {"detected": detected, "predicted_care_event": event, "care_category": category, "confidence": score, "estimated_time_window": "30–60 days" if detected else None},
        "advocate_contact": {"risk_level": risk, "confidence": contact_conf, "reason": "Recent contact frequency and unresolved follow-up indicators were evaluated separately from care intent."},
        "evidence": _build_evidence(context),
        "recommended_action": "RUN_READINESS_ASSESSMENT" if detected else "MONITOR",
        "threshold": threshold,
        "transcript_tool_invoked": False,
        "generated_by": "MOCK_AI",
    }


async def analyze_care_intent(db: Session, member_id: str) -> CareIntentResult | None:
    context = build_member_context(db, member_id)
    if not context:
        return None
    runtime = get_runtime_settings(db)
    threshold = runtime["care_intent_threshold"]
    cache_key = (member_id, threshold, runtime["recent_call_limit"], runtime["claim_lookback_months"], runtime["enable_transcript_fallback"])
    if cache_key in CARE_CACHE:
        return CARE_CACHE[cache_key]
    started = time.perf_counter()

    # Agent gets compact summaries by default, not full transcript text.
    model_packet = {
        "member": context["member"],
        "plan": context["plan"],
        "recent_claim_trajectory": context["recent_claim_trajectory"],
        "recent_claims": context["recent_claims"][-12:],
        "recent_agent_assist_summaries": context["recent_agent_assist_summaries"],
        "available_transcript_ids": context["available_transcript_ids"],
        "threshold": threshold,
    }

    # Exception-based transcript retrieval: summaries remain the default. A full transcript is opened
    # only when recent summary language contains explicit counterevidence that can materially change the prediction.
    fallback_used = False
    negative_terms = ["not planning surgery", "no surgery scheduled", "continue conservative", "continue therapy"]
    matching_call_id = None
    for summary in reversed(context["recent_agent_assist_summaries"]):
        text = (summary.get("summary") or "").lower() + " " + (summary.get("follow_up_note") or "").lower()
        if any(term in text for term in negative_terms):
            matching_call_id = summary.get("call_id")
            break
    if runtime["enable_transcript_fallback"] and matching_call_id:
        transcript = get_transcript(db, matching_call_id)
        if transcript:
            model_packet["fallback_transcript"] = {"call_id": matching_call_id, "transcript_text": transcript["transcript_text"]}
            fallback_used = True

    input_text = json.dumps(model_packet, default=str)

    if settings.use_mock_ai:
        payload = _heuristic(context, threshold)
        payload["transcript_tool_invoked"] = fallback_used
        if fallback_used:
            payload["evidence"].append({"type":"TRANSCRIPT","description":"Full transcript confirmed the member stated there is still no surgery scheduled and wants to continue therapy.","source_id":model_packet["fallback_transcript"]["call_id"],"date":None})
        output_text = json.dumps(payload)
        usage_in, usage_out, mode = estimate_tokens(input_text), estimate_tokens(output_text), "MOCK"
    else:
        provider = OpenAIProvider()
        payload, usage = await provider.generate_json(system_prompt=SYSTEM_PROMPT, user_payload=model_packet)
        payload["threshold"] = threshold
        payload.setdefault("transcript_tool_invoked", False)
        payload.setdefault("generated_by", "OPENAI")
        usage_in = usage.get("input_tokens") or estimate_tokens(input_text)
        usage_out = usage.get("output_tokens") or estimate_tokens(json.dumps(payload))
        mode = usage.get("mode", "OPENAI")

    result = CareIntentResult.model_validate(payload)
    latency = int((time.perf_counter() - started) * 1000)
    log_usage(db, agent_name="CARE_INTENT", member_id=member_id, input_tokens=usage_in,
              output_tokens=usage_out, latency_ms=max(latency, 35 if settings.use_mock_ai else latency),
              transcript_tool_invoked=result.transcript_tool_invoked, mode=mode)
    CARE_CACHE[cache_key] = result
    return result
