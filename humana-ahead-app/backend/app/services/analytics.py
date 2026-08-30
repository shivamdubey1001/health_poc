from sqlalchemy.orm import Session
from app import models
from app.services.activity_filter import get_candidate_member_ids
from app.services.usage import aggregate_usage


def dashboard_overview(db: Session) -> dict:
    total_members = db.query(models.MemberEnrollment).count()
    candidates = get_candidate_member_ids(db)
    # Stable demo approximations until users explicitly run queue analyses.
    high_confidence_demo = 4
    readiness_demo = 4
    open_issues_demo = 3
    pending_outreach = max(0, readiness_demo - db.query(models.OutreachDecision).count())
    usage = aggregate_usage(db)
    return {
        "kpis": {
            "active_members": total_members,
            "meaningful_activity": len(candidates),
            "members_evaluated": usage["agent1_unique_members"],
            "high_confidence_care_intent": high_confidence_demo,
            "readiness_assessments": max(readiness_demo, usage["agent2_unique_members"]),
            "administrative_issues_found": open_issues_demo,
            "outreach_awaiting_approval": pending_outreach,
            "estimated_ai_cost": usage["estimated_ai_cost"],
        },
        "funnel": [
            {"label":"Active members","value":total_members},
            {"label":"Meaningful new activity","value":len(candidates)},
            {"label":"Agent 1 evaluated","value":max(52, usage["agent1_unique_members"])},
            {"label":"High-confidence care intent","value":12},
            {"label":"Readiness assessments","value":12},
            {"label":"Advocate interventions","value":7},
        ],
        "recent_alerts": [
            {"member_id":"M0001","member_name":"Margaret Lewis","event":"Total knee replacement","confidence":0.86,"readiness":83,"issue":"Transportation support"},
            {"member_id":"M0002","member_name":"Robert Carter","event":"Total knee replacement","confidence":0.91,"readiness":61,"issue":"Facility network"},
            {"member_id":"M0003","member_name":"Linda Bennett","event":"Total hip replacement","confidence":0.84,"readiness":72,"issue":"Authorization pending"},
            {"member_id":"M0004","member_name":"James Turner","event":"Cataract surgery","confidence":0.82,"readiness":92,"issue":"No major issue"},
        ],
    }


def cost_analytics(db: Session) -> dict:
    usage = aggregate_usage(db)
    # Explicitly illustrative business assumptions for the product story.
    potential_calls_avoided = 18
    minutes_saved = 430
    advocate_cost_per_minute = 0.85
    time_value = round(minutes_saved * advocate_cost_per_minute, 2)
    net = round(time_value - usage["estimated_ai_cost"], 2)
    return {
        **usage,
        "funnel": [
            {"label":"Active members","value":250},
            {"label":"Meaningful activity","value":52},
            {"label":"Agent 1 evaluations","value":52},
            {"label":"High confidence","value":12},
            {"label":"Agent 2 assessments","value":12},
            {"label":"Advocate interventions","value":7},
        ],
        "potential_calls_avoided": potential_calls_avoided,
        "estimated_handle_time_minutes_saved": minutes_saved,
        "assumed_advocate_cost_per_minute": advocate_cost_per_minute,
        "estimated_advocate_time_value": time_value,
        "estimated_net_operational_value": net,
        "prototype_assumption": "Call-avoidance and handle-time values are illustrative prototype assumptions, not Humana actuals.",
    }
