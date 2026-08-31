"""Outreach drafting and advocate decisions.

DESIGN PRINCIPLE: the notification resolves, it does not refer.

The premise of this product is to get ahead of the call. A message whose answer
is "contact a Member Advocate" is a better way of generating that call, not a
way of preventing it. So the notification carries the whole readiness picture,
and where the plan already knows the answer it presents the member with a
choice they can act on directly. An advocate is offered only where the item
genuinely cannot be self-resolved.

Four resolution modes, decided from the deterministic checklist rather than by
the model:

  CHOOSE_OPTION   The plan can offer alternatives - in-network facilities or
                  providers. The member picks one and the record is updated.
  CONFIRM         A single yes/no the member can answer, such as booking a
                  covered ride.
  NO_ACTION       We are handling it with the provider. Nothing is asked of the
                  member; they are told so explicitly.
  ADVOCATE        Genuinely needs a human. Used only when nothing above applies.

Governance is applied per MESSAGE CLASS, not per prediction confidence. Those
are independent axes: a reassurance message is low consequence at any
confidence, while one asking a member to change facility is high consequence at
any confidence. Every class currently requires advocate approval before it
reaches a member; automation is earned per class from override data.
"""

from sqlalchemy.orm import Session

from app import models
from app.schemas import CareIntentResult, OutreachDraft, ReadinessResult

# Internal status -> what the member sees. NEEDS_ATTENTION and UNKNOWN are
# operational vocabulary and are never shown to a member.
MEMBER_STATUS = {
    "READY": "Ready",
    "IN_PROGRESS": "We're on it",
    "NEEDS_ATTENTION": "Needs your choice",
    "UNKNOWN": "We're confirming",
    "NOT_APPLICABLE": "Not applicable",
}

# Which checklist items the plan can resolve for the member, and how.
NETWORK_ISSUES = {"Facility network", "Surgeon / provider network"}
PLAN_HANDLES = {"Prior authorization", "Referral", "Predicted procedure coverage"}
CONFIRMABLE = {"Transportation benefit", "Home health benefit",
               "Physical therapy benefit", "DME benefit"}


def _member_checklist(readiness: ReadinessResult) -> list[dict]:
    return [
        {
            "key": item.key,
            "label": item.label,
            "status": item.status,
            "member_status": MEMBER_STATUS.get(item.status, "We're confirming"),
            "detail": item.detail,
            "is_top_issue": bool(readiness.top_issue) and item.label == readiness.top_issue,
        }
        for item in readiness.checklist
    ]


def _resolution(readiness: ReadinessResult, event: str, first: str) -> dict:
    """Decide what the notification asks of the member.

    Everything here is derived from deterministic checklist facts. The model
    does not choose the resolution path, only the wording of the top-issue
    sentence upstream.
    """
    issue = readiness.top_issue
    alternatives = [a.model_dump() for a in readiness.alternatives]
    lower_event = (event or "your procedure").lower()

    # --- the plan can offer a concrete choice -------------------------------
    if issue in NETWORK_ISSUES and alternatives:
        what = "facility" if issue == "Facility network" else "provider"
        plural = "facilities" if what == "facility" else "providers"
        return {
            "resolution_mode": "CHOOSE_OPTION",
            "message_class": "CARE_REDIRECTION",
            "advocate_required": False,
            "advocate_reason": "",
            "lead_line": (
                f"The {what} currently planned for your {lower_event} isn't in your "
                f"plan's network, which would cost you significantly more. "
                f"{len(alternatives)} in-network {plural} near you are available for "
                f"this procedure. Choose the one that works best and we'll update "
                f"your records and let your care team know."
            ),
            "call_to_action": f"Choose your {what}",
            "member_options": [
                {
                    "option_id": a["provider_id"],
                    "label": a["provider_name"],
                    "sublabel": f'{a["city"]}, {a["state"]} · in network',
                    "kind": "PROVIDER_CHOICE",
                }
                for a in alternatives
            ],
        }

    # --- a single yes/no the member can answer ------------------------------
    if issue in CONFIRMABLE:
        return {
            "resolution_mode": "CONFIRM",
            "message_class": "BENEFIT_SURFACING",
            "advocate_required": False,
            "advocate_reason": "",
            "lead_line": (
                f"Your plan includes {issue.replace(' benefit', '').lower()} support for "
                f"this procedure, and it hasn't been set up yet. Let us know if you'd "
                f"like it arranged and we'll take care of it."
            ),
            "call_to_action": "Would you like us to arrange this?",
            "member_options": [
                {"option_id": "YES", "label": "Yes, please arrange it",
                 "sublabel": "We'll set it up and confirm the details", "kind": "CONFIRM"},
                {"option_id": "NO", "label": "No thanks",
                 "sublabel": "You can change your mind later", "kind": "CONFIRM"},
            ],
        }

    # --- we are handling it; nothing is asked of the member -----------------
    if issue in PLAN_HANDLES:
        return {
            "resolution_mode": "NO_ACTION",
            "message_class": "INFORMATIONAL",
            "advocate_required": False,
            "advocate_reason": "",
            "lead_line": (
                f"One item is still being confirmed with your provider's office, and "
                f"we're following up on it directly. There's nothing you need to do - "
                f"we'll let you know as soon as it's settled."
            ),
            "call_to_action": "",
            "member_options": [],
        }

    # --- everything is ready ------------------------------------------------
    if not issue:
        return {
            "resolution_mode": "NO_ACTION",
            "message_class": "INFORMATIONAL",
            "advocate_required": False,
            "advocate_reason": "",
            "lead_line": (
                "Everything on your plan is in order for this procedure. Your full "
                "checklist is below so you know exactly what's covered."
            ),
            "call_to_action": "",
            "member_options": [],
        }

    # --- genuinely needs a human -------------------------------------------
    return {
        "resolution_mode": "ADVOCATE",
        "message_class": "COST_DISCLOSURE" if issue == "Member cost-share context" else "INFORMATIONAL",
        "advocate_required": True,
        "advocate_reason": (
            f"'{issue}' has no self-service resolution path available. No in-network "
            f"alternatives were found and it is not an item the plan can settle "
            f"directly, so a Member Advocate is genuinely required."
        ),
        "lead_line": (
            f"One item needs a short conversation before your {lower_event}. "
            f"We'll reach out at a time that suits you - just let us know when."
        ),
        "call_to_action": "When would you like us to call?",
        "member_options": [
            {"option_id": "MORNING", "label": "Weekday morning", "sublabel": "8am - 12pm", "kind": "CALLBACK"},
            {"option_id": "AFTERNOON", "label": "Weekday afternoon", "sublabel": "12pm - 5pm", "kind": "CALLBACK"},
            {"option_id": "NO_CALL", "label": "I'd rather not be called", "sublabel": "We'll write to you instead", "kind": "CALLBACK"},
        ],
    }


def build_outreach_draft(db: Session, member_id: str, care: CareIntentResult,
                         readiness: ReadinessResult) -> OutreachDraft:
    member = db.get(models.MemberEnrollment, member_id)
    first = member.synthetic_first_name
    event = readiness.predicted_care_event
    checklist = _member_checklist(readiness)
    ready_count = sum(1 for c in checklist if c["status"] == "READY")
    plan = _resolution(readiness, event, first)

    if plan["resolution_mode"] == "CHOOSE_OPTION":
        headline = f"One choice to make before your {event.lower()}"
    elif plan["resolution_mode"] == "CONFIRM":
        headline = f"A benefit you can use for your {event.lower()}"
    elif readiness.top_issue:
        headline = f"We're finishing one item for your {event.lower()}"
    else:
        headline = f"Your plan is ready for your {event.lower()}"

    summary = (f"{ready_count} of {len(checklist)} plan items are ready."
               if checklist else "Your plan details are being reviewed.")

    message = (
        f"Hi {first}, we're helping you get ready for your {event.lower()}. "
        f"{summary} {plan['lead_line']}"
    )

    return OutreachDraft(
        member_id=member_id,
        channel=member.preferred_contact_channel,
        message=message,
        human_approval_required=True,
        message_class=plan["message_class"],
        gating_policy="ADVOCATE_APPROVAL_REQUIRED",
        top_issue=readiness.top_issue,
        headline=headline,
        predicted_care_event=event,
        readiness_score=readiness.readiness_score,
        readiness_label=readiness.readiness_label,
        highlighted_action=readiness.recommended_next_action,
        checklist=checklist,
        ready_count=ready_count,
        total_items=len(checklist),
        # Resolution rather than referral.
        resolution_mode=plan["resolution_mode"],
        call_to_action=plan["call_to_action"],
        member_options=plan["member_options"],
        advocate_required=plan["advocate_required"],
        advocate_reason=plan["advocate_reason"],
        alternatives=[a.model_dump() for a in readiness.alternatives],
    )


def record_decision(db: Session, member_id: str, action: str, message: str,
                    original_message: str = "", message_class: str = "INFORMATIONAL",
                    top_issue: str = "") -> dict:
    was_edited = bool(original_message) and message.strip() != original_message.strip()
    db.add(models.OutreachDecision(
        member_id=member_id, action=action, message_text=message,
        original_message=original_message, was_edited=was_edited,
        message_class=message_class, top_issue=top_issue or "",
    ))
    db.commit()
    return {
        "member_id": member_id,
        "action": action,
        "was_edited": was_edited,
        "message_class": message_class,
        "status": ("APPROVED_FOR_SEND" if action == "APPROVE"
                   else "SAVED_FOR_REVIEW" if action == "SAVE_FOR_REVIEW"
                   else "DO_NOT_CONTACT"),
        "prototype_mode": True,
        "message": "No real communication was sent. Prototype Mode is always on for outbound actions.",
    }
