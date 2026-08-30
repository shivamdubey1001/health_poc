from sqlalchemy.orm import Session
from app import models
from app.schemas import CareIntentResult, ReadinessResult, OutreachDraft


def build_outreach_draft(db: Session, member_id: str, care: CareIntentResult, readiness: ReadinessResult) -> OutreachDraft:
    member = db.get(models.MemberEnrollment, member_id)
    first = member.synthetic_first_name
    channel = member.preferred_contact_channel
    issue = readiness.top_issue
    if issue == "Facility network":
        body = f"Hi {first}, we're helping you prepare for your upcoming care. We found a facility-network item that may need attention. A Member Advocate can review in-network options with you."
    elif issue == "Transportation benefit":
        body = f"Hi {first}, we're helping you prepare for your upcoming care. Most plan-related items look ready. You may have transportation support available. Would you like help reviewing this benefit?"
    elif issue == "Prior authorization":
        body = f"Hi {first}, we're helping you prepare for your upcoming care. One administrative item is still being reviewed. A Member Advocate can help you understand the current status."
    else:
        body = f"Hi {first}, we're helping you prepare for your upcoming care. A Member Advocate can review your plan-related readiness and any open administrative items with you."
    return OutreachDraft(member_id=member_id, channel=channel, message=body, human_approval_required=True)


def record_decision(db: Session, member_id: str, action: str, message: str) -> dict:
    db.add(models.OutreachDecision(member_id=member_id, action=action, message_text=message))
    db.commit()
    return {
        "member_id": member_id,
        "status": "APPROVED_FOR_SEND" if action == "APPROVE" else "SAVED_FOR_REVIEW" if action == "SAVE_FOR_REVIEW" else "DO_NOT_CONTACT",
        "prototype_mode": True,
        "message": "No real communication was sent. Prototype Mode is always on for outbound actions.",
    }
