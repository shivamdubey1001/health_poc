import math
from sqlalchemy import func
from sqlalchemy.orm import Session
from app import models
from app.config import settings


def estimate_tokens(text: str) -> int:
    # Simple deterministic estimate for mock mode. Real mode uses API-provided usage when available.
    return max(1, math.ceil(len(text) / 4))


def estimated_cost(input_tokens: int, output_tokens: int) -> float:
    return round(
        input_tokens / 1_000_000 * settings.input_cost_per_m_tokens +
        output_tokens / 1_000_000 * settings.output_cost_per_m_tokens,
        6,
    )


def log_usage(db: Session, *, agent_name: str, member_id: str, input_tokens: int,
              output_tokens: int, latency_ms: int, transcript_tool_invoked: bool, mode: str) -> None:
    db.add(models.AIUsageLog(
        agent_name=agent_name,
        member_id=member_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost=estimated_cost(input_tokens, output_tokens),
        latency_ms=latency_ms,
        transcript_tool_invoked=transcript_tool_invoked,
        mode=mode,
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
        "pricing_note": "Prototype assumptions from environment settings; not Humana or vendor actuals.",
    }
