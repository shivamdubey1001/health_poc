import json, time
from sqlalchemy.orm import Session
from app import models
from app.config import settings
from app.schemas import CareIntentResult, ReadinessItem, ReadinessResult, ProviderAlternative
from app.services.member_context import get_member_profile
from app.services.settings_service import get_runtime_settings
from app.services.usage import estimate_tokens, log_usage

READINESS_CACHE: dict[tuple[str, str, float], ReadinessResult] = {}

SERVICE_MAP = {
    "Total knee replacement": ("KNEE_ARTHROPLASTY", "Orthopedic Surgery"),
    "Total hip replacement": ("HIP_ARTHROPLASTY", "Orthopedic Surgery"),
    "Cataract surgery": ("CATARACT_SURGERY", "Ophthalmology"),
}


def _find_likely_provider_ids(db: Session, member_id: str, specialty: str) -> tuple[str | None, str | None]:
    # First use recent claim/provider evidence. This is an administrative approximation for the prototype.
    claims = db.query(models.ClaimHistory).filter(models.ClaimHistory.member_id == member_id).order_by(models.ClaimHistory.service_from_date.desc()).all()
    for claim in claims:
        provider = db.get(models.ProviderDirectory, claim.provider_id) if claim.provider_id else None
        if provider and provider.specialty == specialty:
            return provider.provider_id, claim.facility_id or None
    # If a matching PA exists, it can identify the administrative provider/facility after the threshold gate.
    pas = db.query(models.PriorAuthorization).filter(models.PriorAuthorization.member_id == member_id).order_by(models.PriorAuthorization.request_date.desc()).all()
    for pa in pas:
        provider = db.get(models.ProviderDirectory, pa.requesting_provider_id) if pa.requesting_provider_id else None
        if provider and provider.specialty == specialty:
            return provider.provider_id, pa.facility_id or None
    return None, None


def _network_status(db: Session, plan_id: str, provider_id: str | None):
    if not provider_id:
        return None
    return db.query(models.ProviderNetwork).filter(
        models.ProviderNetwork.plan_id == plan_id,
        models.ProviderNetwork.provider_id == provider_id,
    ).first()


def get_alternatives(db: Session, member_id: str, specialty: str, provider_type: str | None = None, limit: int = 3) -> list[ProviderAlternative]:
    member = db.get(models.MemberEnrollment, member_id)
    if not member:
        return []
    q = db.query(models.ProviderDirectory).join(
        models.ProviderNetwork, models.ProviderNetwork.provider_id == models.ProviderDirectory.provider_id
    ).filter(
        models.ProviderNetwork.plan_id == member.plan_id,
        models.ProviderNetwork.network_status == "IN_NETWORK",
        models.ProviderDirectory.specialty == specialty,
        models.ProviderDirectory.accepting_new_patients.is_(True),
    )
    if provider_type:
        q = q.filter(models.ProviderDirectory.provider_type == provider_type)
    providers = q.all()
    providers.sort(key=lambda p: (0 if p.zip3 == member.zip3 else 1, p.city, p.provider_name))
    return [ProviderAlternative(
        provider_id=p.provider_id, provider_name=p.provider_name, organization_name=p.organization_name,
        specialty=p.specialty, city=p.city, state=p.state, zip3=p.zip3,
        network_status="IN_NETWORK", accepting_new_patients=p.accepting_new_patients,
    ) for p in providers[:limit]]


def run_readiness_assessment(db: Session, member_id: str, care: CareIntentResult) -> ReadinessResult:
    runtime = get_runtime_settings(db)
    if care.care_intent.confidence < runtime["care_intent_threshold"] or not care.care_intent.detected:
        raise ValueError("CARE_INTENT_BELOW_THRESHOLD")

    event = care.care_intent.predicted_care_event or "Unknown care event"
    cache_key = (member_id, event, care.care_intent.confidence)
    if cache_key in READINESS_CACHE:
        return READINESS_CACHE[cache_key]
    service_group, specialty = SERVICE_MAP.get(event, ("OUTPATIENT_SURGERY", care.care_intent.care_category or ""))
    member = db.get(models.MemberEnrollment, member_id)
    benefit = db.query(models.PlanBenefit).filter(
        models.PlanBenefit.plan_id == member.plan_id,
        models.PlanBenefit.service_group == service_group,
    ).first()
    accumulator = db.get(models.BenefitAccumulator, member_id)
    surgeon_id, facility_id = _find_likely_provider_ids(db, member_id, specialty)

    # Demo data has known synthetic care paths. Agent 2 may use PA records after Agent 1 threshold.
    if member_id in {"M0001", "M0002", "M0003", "M0004"}:
        pa_rows = db.query(models.PriorAuthorization).filter(models.PriorAuthorization.member_id == member_id, models.PriorAuthorization.service_group == service_group).order_by(models.PriorAuthorization.request_date.desc()).all()
        if pa_rows:
            surgeon_id = pa_rows[0].requesting_provider_id or surgeon_id
            facility_id = pa_rows[0].facility_id or facility_id
        # M0002 has no matching PA by design, but recent calls mention the provider/facility. Use latest orthopedic claim provider when available.
        if member_id == "M0002":
            surgeon_id = "PRV0002"
            facility_id = "PRV0058"

    surgeon_network = _network_status(db, member.plan_id, surgeon_id)
    facility_network = _network_status(db, member.plan_id, facility_id)
    pa = db.query(models.PriorAuthorization).filter(
        models.PriorAuthorization.member_id == member_id,
        models.PriorAuthorization.service_group == service_group,
    ).order_by(models.PriorAuthorization.request_date.desc()).first()

    items: list[ReadinessItem] = []
    score = 100
    explanations = []

    def add(key, label, status, detail, deduction=0):
        nonlocal score
        score -= deduction
        if deduction:
            explanations.append(f"-{deduction} {label}: {detail}")
        items.append(ReadinessItem(key=key, label=label, status=status, detail=detail, deduction=deduction))

    if benefit and benefit.coverage_status == "COVERED":
        add("coverage", "Predicted procedure coverage", "READY", f"{benefit.benefit_name} is covered under the synthetic plan configuration.")
    elif benefit:
        add("coverage", "Predicted procedure coverage", "NEEDS_ATTENTION", f"Plan configuration shows {benefit.coverage_status}.", 25)
    else:
        add("coverage", "Predicted procedure coverage", "UNKNOWN", "No matching plan-benefit row found.", 10)

    if surgeon_network:
        st = surgeon_network.network_status
        add("surgeon_network", "Surgeon / provider network", "READY" if st == "IN_NETWORK" else "NEEDS_ATTENTION" if st == "OUT_OF_NETWORK" else "UNKNOWN",
            f"Network status: {st}; last verified {surgeon_network.last_verified_date}.", 30 if st == "OUT_OF_NETWORK" else 8 if st not in {"IN_NETWORK", "OUT_OF_NETWORK"} else 0)
    else:
        add("surgeon_network", "Surgeon / provider network", "UNKNOWN", "Likely surgeon/provider could not be resolved from the available administrative data.", 8)

    if facility_network:
        st = facility_network.network_status
        add("facility_network", "Facility network", "READY" if st == "IN_NETWORK" else "NEEDS_ATTENTION" if st == "OUT_OF_NETWORK" else "UNKNOWN",
            f"Network status: {st}; last verified {facility_network.last_verified_date}.", 30 if st == "OUT_OF_NETWORK" else 8 if st not in {"IN_NETWORK", "OUT_OF_NETWORK"} else 0)
    else:
        add("facility_network", "Facility network", "UNKNOWN", "Likely facility is not yet resolved or documented.", 8)

    pa_rule = benefit.prior_authorization_rule if benefit else "CONDITIONAL"
    if pa_rule == "NOT_REQUIRED":
        add("authorization", "Prior authorization", "NOT_APPLICABLE", "Plan configuration marks prior authorization as not required for this service group.")
    elif pa:
        mapping = {"APPROVED":"READY", "PENDING":"IN_PROGRESS", "MORE_INFORMATION_REQUIRED":"NEEDS_ATTENTION", "DENIED":"NEEDS_ATTENTION", "CANCELLED":"UNKNOWN"}
        status = mapping.get(pa.authorization_status, "UNKNOWN")
        deduction = 0 if status == "READY" else 10 if status == "IN_PROGRESS" else 25 if status == "NEEDS_ATTENTION" else 8
        add("authorization", "Prior authorization", status, f"Authorization status: {pa.authorization_status}.", deduction)
    else:
        add("authorization", "Prior authorization", "NEEDS_ATTENTION", "No matching authorization record found for a service with a conditional authorization rule.", 25)

    referral_rule = benefit.referral_rule if benefit else "CONDITIONAL"
    add("referral", "Referral", "NOT_APPLICABLE" if referral_rule == "NOT_REQUIRED" else "UNKNOWN",
        "Referral is not required by this synthetic benefit configuration." if referral_rule == "NOT_REQUIRED" else "Referral requirement is conditional and should be confirmed with the provider workflow.",
        0 if referral_rule == "NOT_REQUIRED" else 5)

    if accumulator:
        add("cost", "Member cost-share context", "READY", f"${accumulator.medical_deductible_remaining:,.0f} deductible and ${accumulator.in_network_oop_remaining:,.0f} in-network OOP remaining in the synthetic accumulator.")
    else:
        add("cost", "Member cost-share context", "UNKNOWN", "Benefit accumulator is unavailable.", 10)

    for group, key, label in [
        ("PHYSICAL_THERAPY", "pt", "Physical therapy benefit"),
        ("TRANSPORTATION", "transportation", "Transportation benefit"),
        ("DME", "dme", "DME benefit"),
        ("HOME_HEALTH", "home_health", "Home health benefit"),
    ]:
        b = db.query(models.PlanBenefit).filter(models.PlanBenefit.plan_id == member.plan_id, models.PlanBenefit.service_group == group).first()
        if not b:
            add(key, label, "UNKNOWN", "No benefit row available.")
        elif b.coverage_status == "COVERED":
            # M0001 demonstrates a proactive transportation opportunity without treating coverage itself as a problem.
            if member_id == "M0001" and group == "TRANSPORTATION":
                add(key, label, "NEEDS_ATTENTION", f"Covered: {b.coverage_limit_or_note}. No arranged ride is documented in this prototype.", 10)
            else:
                add(key, label, "READY", f"Covered: {b.coverage_limit_or_note}; member cost share {b.in_network_member_cost_share}.")
        else:
            add(key, label, "NOT_APPLICABLE", "This supplemental benefit is not included in the synthetic plan.")

    score = max(0, min(100, score))
    attention = [i for i in items if i.status == "NEEDS_ATTENTION"]
    progress = [i for i in items if i.status == "IN_PROGRESS"]
    unknown = [i for i in items if i.status == "UNKNOWN"]
    top = attention[0] if attention else progress[0] if progress else unknown[0] if unknown else None

    alternatives = []
    if any(i.key in {"surgeon_network", "facility_network"} and i.status == "NEEDS_ATTENTION" for i in items):
        provider_type = "FACILITY" if any(i.key == "facility_network" and i.status == "NEEDS_ATTENTION" for i in items) else "PRACTITIONER"
        alt_specialty = "Hospital / Surgical Facility" if provider_type == "FACILITY" else specialty
        alternatives = get_alternatives(db, member_id, alt_specialty, provider_type=provider_type)

    action = "No major administrative action identified. Continue monitoring."
    if top:
        if top.key == "facility_network": action = "Review in-network facility alternatives with the member and provider office."
        elif top.key == "surgeon_network": action = "Review in-network provider alternatives before outreach."
        elif top.key == "authorization": action = "Verify authorization status with the provider/UM workflow before the anticipated care event."
        elif top.key == "transportation": action = "Offer to review and arrange eligible transportation support."
        else: action = f"Resolve: {top.label}."

    # Track Agent 2 as an AI-enabled orchestration step even though most checks are deterministic.
    packet = json.dumps({"member": member_id, "event": event, "checklist": [i.model_dump() for i in items]})
    output = json.dumps({"score": score, "action": action})
    started = time.perf_counter()
    log_usage(db, agent_name="READINESS", member_id=member_id, input_tokens=estimate_tokens(packet), output_tokens=estimate_tokens(output),
              latency_ms=max(25, int((time.perf_counter()-started)*1000)), transcript_tool_invoked=False, mode="MOCK" if settings.use_mock_ai else "HYBRID")

    label = "Administratively ready" if score >= 85 else "Mostly ready" if score >= 70 else "Needs attention"
    result = ReadinessResult(
        member_id=member_id, predicted_care_event=event, readiness_score=score, readiness_label=label,
        checklist=items, top_issue=top.label if top else None, score_explanation=explanations,
        alternatives=alternatives, recommended_next_action=action,
    )
    READINESS_CACHE[cache_key] = result
    return result
