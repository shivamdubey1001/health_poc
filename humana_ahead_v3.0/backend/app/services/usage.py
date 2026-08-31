import math
import re

from sqlalchemy.orm import Session

from app import models
from app.agents.openai_provider import COUNTERS
from app.config import settings

# Rough token estimator used only when the API does not report usage. Counts
# words and punctuation rather than dividing character length by four, which
# badly understates JSON payloads dense with braces, quotes and short keys.
_TOKEN_RE = re.compile(r"[A-Za-z]+|\d+|[^\sA-Za-z\d]")


def estimate_tokens(text: str) -> int:
    if not text:
        return 1
    pieces = _TOKEN_RE.findall(text)
    # Long words split into multiple tokens; add a correction for those.
    extra = sum(max(0, math.ceil(len(p) / 5) - 1) for p in pieces if p.isalpha() and len(p) > 5)
    return max(1, len(pieces) + extra)


def estimated_cost(input_tokens: int, output_tokens: int) -> float:
    return round(
        input_tokens / 1_000_000 * settings.input_cost_per_m_tokens
        + output_tokens / 1_000_000 * settings.output_cost_per_m_tokens,
        6,
    )


def log_usage(db: Session, *, agent_name: str, member_id: str, input_tokens: int,
              output_tokens: int, latency_ms: int, transcript_tool_invoked: bool,
              mode: str, correlation_id: str = "", prompt_version: str = "",
              token_source: str = "API") -> None:
    db.add(models.AIUsageLog(
        agent_name=agent_name,
        member_id=member_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost=estimated_cost(input_tokens, output_tokens),
        latency_ms=latency_ms,
        transcript_tool_invoked=transcript_tool_invoked,
        mode=mode,
        correlation_id=correlation_id,
        prompt_version=prompt_version,
        token_source=token_source,
    ))
    db.commit()


def aggregate_usage(db: Session) -> dict:
    rows = db.query(models.AIUsageLog).all()
    total_cost = sum(r.estimated_cost for r in rows)
    total_input = sum(r.input_tokens for r in rows)
    total_output = sum(r.output_tokens for r in rows)
    member_ids = {r.member_id for r in rows}
    agent1_members = {r.member_id for r in rows if r.agent_name == "CARE_INTENT"}
    agent2_members = {r.member_id for r in rows if r.agent_name == "READINESS"}
    transcript_calls = sum(1 for r in rows if r.transcript_tool_invoked)
    estimated_rows = sum(1 for r in rows if r.token_source == "ESTIMATED")
    avg_latency = round(sum(r.latency_ms for r in rows) / len(rows), 1) if rows else 0
    return {
        "total_ai_calls": len(rows),
        "agent1_calls": sum(1 for r in rows if r.agent_name == "CARE_INTENT"),
        "agent2_calls": sum(1 for r in rows if r.agent_name == "READINESS"),
        "unique_members_evaluated": len(member_ids),
        "agent1_unique_members": len(agent1_members),
        "agent2_unique_members": len(agent2_members),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "average_tokens_per_call": round((total_input + total_output) / len(rows), 1) if rows else 0,
        "estimated_ai_cost": round(total_cost, 4),
        "cost_per_member_evaluated": round(total_cost / len(member_ids), 4) if member_ids else 0,
        "transcript_tool_invocations": transcript_calls,
        "average_latency_ms": avg_latency,
        # Reliability counters. Zero is a meaningful reading; no counter is not.
        "parse_repairs": COUNTERS["parse_repairs"],
        "transport_retries": COUNTERS["transport_retries"],
        "schema_rejections": COUNTERS["schema_rejections"],
        "rows_with_estimated_tokens": estimated_rows,
        "pricing_note": (
            f"Estimated from API-reported token usage and configured rates for "
            f"{settings.openai_model}; update environment pricing if the model changes."
        ),
    }


def outreach_decision_stats(db: Session) -> dict:
    """The learning loop.

    Approve, edit and reject rates by message class are what eventually justify
    relaxing the human gate on the lowest-risk classes. Without this the human
    review queue - the largest cost line in the product - can never shrink.
    """
    rows = db.query(models.OutreachDecision).all()
    if not rows:
        return {
            "total_decisions": 0, "approved": 0, "saved": 0, "rejected": 0,
            "edited": 0, "approval_rate": 0.0, "edit_rate": 0.0,
            "by_message_class": [], "by_top_issue": [],
            "note": "No advocate decisions recorded yet. Approve, edit or reject a "
                    "draft to start building override data.",
        }

    approved = sum(1 for r in rows if r.action == "APPROVE")
    saved = sum(1 for r in rows if r.action == "SAVE_FOR_REVIEW")
    rejected = sum(1 for r in rows if r.action == "REJECT")
    edited = sum(1 for r in rows if r.was_edited)

    def group(attr: str) -> list[dict]:
        buckets: dict[str, dict] = {}
        for r in rows:
            key = getattr(r, attr) or "UNSPECIFIED"
            b = buckets.setdefault(key, {"key": key, "total": 0, "approved": 0, "edited": 0, "rejected": 0})
            b["total"] += 1
            if r.action == "APPROVE":
                b["approved"] += 1
            if r.action == "REJECT":
                b["rejected"] += 1
            if r.was_edited:
                b["edited"] += 1
        for b in buckets.values():
            b["approval_rate"] = round(b["approved"] / b["total"], 3)
            b["edit_rate"] = round(b["edited"] / b["total"], 3)
        return sorted(buckets.values(), key=lambda x: -x["total"])

    return {
        "total_decisions": len(rows),
        "approved": approved, "saved": saved, "rejected": rejected, "edited": edited,
        "approval_rate": round(approved / len(rows), 3),
        "edit_rate": round(edited / len(rows), 3),
        "by_message_class": group("message_class"),
        "by_top_issue": group("top_issue"),
        "note": "Override rate by message class is the evidence that would justify "
                "auto-sending the lowest-risk classes without advocate review.",
    }
