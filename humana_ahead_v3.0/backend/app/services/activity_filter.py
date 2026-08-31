from datetime import date, timedelta
from sqlalchemy.orm import Session
from app import models
from app.config import settings

# Single source of truth. This was previously hardcoded here while the rest of
# the application read settings.data_as_of, so changing the environment variable
# silently desynchronised the candidate filter from every window calculation.
AS_OF = date.fromisoformat(settings.data_as_of)


def get_candidate_member_ids(db: Session) -> list[str]:
    """Cheap deterministic Tier-0 filter: no LLM.

    A member becomes a candidate if they have a call within 45 days, a claim within 45 days,
    or any recent call requiring follow-up. This intentionally over-selects; Agent 1 is the next gate.
    """
    cutoff = (AS_OF - timedelta(days=45)).isoformat()
    call_members = {
        r.member_id for r in db.query(models.MemberAdvocateCall.member_id)
        .filter(models.MemberAdvocateCall.call_start_timestamp >= cutoff).all()
    }
    claim_members = {
        r.member_id for r in db.query(models.ClaimHistory.member_id)
        .filter(models.ClaimHistory.service_from_date >= cutoff).all()
    }
    followup_members = {
        r.member_id for r in db.query(models.AgentAssistSummary.member_id)
        .filter(models.AgentAssistSummary.follow_up_required.is_(True)).all()
    }
    return sorted(call_members | claim_members | followup_members)
