"""Evaluation.

The central problem is that the outcome label lags: on the day this ships, no
member has had their surgery yet. Waiting ninety days for claims is not an
acceptable answer for an AI product, so this module provides evaluation that
works on day one, in four layers.

1. LABEL DERIVATION (labels_from_authorizations)
   Prior-authorization records are a held-out label source, because Agent 1 is
   explicitly forbidden by its system prompt from seeing them. A surgical
   authorization with a requested service date after the index date is strong
   evidence a procedure was genuinely planned.

   Known limitation, stated rather than hidden: a member can have a real
   procedure with no authorization on file, and that population is precisely
   what this product exists to find. So a flagged member without an
   authorization is not necessarily a false positive. Measured precision is
   therefore a LOWER BOUND, and recall is measured against
   authorization-confirmed procedures rather than all procedures.

2. BACKTEST (build_backtest_context)
   Pick an index date in the past, hide every claim and call after it, and score
   against outcomes that are already in the data. This yields real precision and
   recall today, with no pilot and no waiting.

3. LABEL-FREE CHECKS (groundedness, self-consistency)
   Groundedness verifies that every piece of evidence the model cites actually
   appears in the payload it was given. This catches fabrication, which is the
   failure mode that does real damage, and it needs no outcome label at all.

4. PERTURBATION (perturbation_cases)
   Remove the sentence where a member mentions a procedure and confidence should
   fall. Add an explicit denial and it should fall further. If confidence does
   not move, the model is anchoring rather than reasoning - which is exactly the
   diagnosis for identical scores across different members.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app import models
from app.config import settings

SURGICAL_GROUPS = {"KNEE_ARTHROPLASTY", "HIP_ARTHROPLASTY", "CATARACT_SURGERY"}
PLANNED_STATUSES = {"APPROVED", "PENDING", "MORE_INFORMATION_REQUIRED"}

GROUP_TO_EVENT = {
    "KNEE_ARTHROPLASTY": "Total knee replacement",
    "HIP_ARTHROPLASTY": "Total hip replacement",
    "CATARACT_SURGERY": "Cataract surgery",
}


def as_of() -> date:
    return date.fromisoformat(settings.data_as_of)


# --------------------------------------------------------------------------
# 1. Label derivation
# --------------------------------------------------------------------------

def labels_from_authorizations(db: Session, index_date: date | None = None,
                              horizon_days: int | None = None) -> list[dict]:
    """Derive held-out labels. Never called from the assessment path."""
    index_date = index_date or as_of()
    horizon = horizon_days or settings.eval_horizon_days
    window_end = index_date + timedelta(days=horizon)

    auths = db.query(models.PriorAuthorization).all()
    by_member: dict[str, list[models.PriorAuthorization]] = {}
    for a in auths:
        by_member.setdefault(a.member_id, []).append(a)

    labels: list[dict] = []
    for member in db.query(models.MemberEnrollment).all():
        mid = member.member_id
        member_auths = by_member.get(mid, [])

        upcoming = []
        for a in member_auths:
            if a.service_group not in SURGICAL_GROUPS:
                continue
            if a.authorization_status not in PLANNED_STATUSES:
                continue
            if not a.requested_service_date:
                continue
            try:
                svc = date.fromisoformat(a.requested_service_date[:10])
            except ValueError:
                continue
            if index_date < svc <= window_end:
                upcoming.append((svc, a))

        if upcoming:
            svc, a = sorted(upcoming)[0]
            labels.append({
                "member_id": mid,
                "label": "UPCOMING_PROCEDURE",
                "actual_procedure": GROUP_TO_EVENT.get(a.service_group, a.procedure_description or ""),
                "actual_service_date": svc.isoformat(),
                "days_from_index": (svc - index_date).days,
                "label_source": "PRIOR_AUTHORIZATION",
                "index_date": index_date.isoformat(),
            })
        elif not member_auths:
            # No authorization of any kind. Treated as a negative, with the
            # lower-bound caveat documented in the module docstring.
            labels.append({
                "member_id": mid, "label": "NO_EVIDENCE",
                "actual_procedure": "", "actual_service_date": "",
                "days_from_index": 0, "label_source": "NO_AUTHORIZATION_ON_FILE",
                "index_date": index_date.isoformat(),
            })
        else:
            # Has authorizations, but nothing surgical and upcoming. Too
            # ambiguous to score either way, so excluded rather than guessed.
            labels.append({
                "member_id": mid, "label": "AMBIGUOUS",
                "actual_procedure": "", "actual_service_date": "",
                "days_from_index": 0, "label_source": "NON_SURGICAL_AUTH_ONLY",
                "index_date": index_date.isoformat(),
            })
    return labels


def rebuild_labels(db: Session, index_date: date | None = None) -> dict:
    rows = labels_from_authorizations(db, index_date)
    db.query(models.EvalLabel).delete()
    for r in rows:
        db.add(models.EvalLabel(**r))
    db.commit()
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["label"]] = counts.get(r["label"], 0) + 1
    return {"total": len(rows), "by_label": counts,
            "index_date": (index_date or as_of()).isoformat()}


def get_labels(db: Session) -> dict[str, models.EvalLabel]:
    return {r.member_id: r for r in db.query(models.EvalLabel).all()}


# --------------------------------------------------------------------------
# 2. Scoring
# --------------------------------------------------------------------------

def score_predictions(db: Session, predictions: list[dict], threshold: float) -> dict:
    """predictions: [{member_id, confidence, predicted_care_event}]"""
    labels = get_labels(db)
    tp = fp = fn = tn = 0
    procedure_right = 0
    scored = skipped = 0
    misses: list[dict] = []
    false_alarms: list[dict] = []

    for p in predictions:
        label = labels.get(p["member_id"])
        if not label or label.label == "AMBIGUOUS":
            skipped += 1
            continue
        scored += 1
        positive = label.label == "UPCOMING_PROCEDURE"
        flagged = (p.get("confidence") or 0) >= threshold

        if flagged and positive:
            tp += 1
            predicted = (p.get("predicted_care_event") or "").lower()
            actual = (label.actual_procedure or "").lower()
            keywords = [w for w in actual.split() if len(w) > 4]
            if keywords and any(w in predicted for w in keywords):
                procedure_right += 1
        elif flagged and not positive:
            fp += 1
            false_alarms.append({"member_id": p["member_id"],
                                 "predicted": p.get("predicted_care_event"),
                                 "confidence": p.get("confidence")})
        elif not flagged and positive:
            fn += 1
            misses.append({"member_id": p["member_id"],
                           "actual": label.actual_procedure,
                           "confidence": p.get("confidence"),
                           "days_out": label.days_from_index})
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {
        "threshold": round(threshold, 3),
        "scored_members": scored,
        "excluded_ambiguous": skipped,
        "true_positives": tp, "false_positives": fp,
        "false_negatives": fn, "true_negatives": tn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "procedure_named_correctly": procedure_right,
        "procedure_accuracy": round(procedure_right / tp, 3) if tp else 0.0,
        "misses": misses[:10],
        "false_alarms": false_alarms[:10],
        "interpretation": (
            "Recall is measured against authorization-confirmed procedures. "
            "Precision is a lower bound: a flagged member with no authorization "
            "on file may still have a real procedure, and that population is "
            "exactly what this product exists to surface."
        ),
    }


def threshold_sweep(db: Session, predictions: list[dict],
                    points: tuple[float, ...] = (0.4, 0.5, 0.6, 0.7, 0.8, 0.9)) -> list[dict]:
    out = []
    for t in points:
        s = score_predictions(db, predictions, t)
        out.append({k: s[k] for k in
                    ("threshold", "precision", "recall", "f1",
                     "true_positives", "false_positives", "false_negatives")})
    return out


# --------------------------------------------------------------------------
# 3. Label-free checks
# --------------------------------------------------------------------------

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall((text or "").lower()))


def groundedness(evidence: list[dict], packet: dict) -> dict:
    """Fraction of cited evidence whose content words appear in the input packet.

    Needs no outcome label. Catches fabrication, which is the failure mode that
    does real damage in a member-facing workflow.
    """
    haystack = _tokens(json.dumps(packet, default=str))
    if not evidence:
        return {"items": 0, "grounded": 0, "score": 1.0, "ungrounded_examples": []}

    grounded = 0
    ungrounded: list[str] = []
    for item in evidence:
        desc = item.get("description") or ""
        content = {w for w in _tokens(desc) if len(w) > 4}
        if not content:
            grounded += 1
            continue
        overlap = len(content & haystack) / len(content)
        if overlap >= 0.5:
            grounded += 1
        else:
            ungrounded.append(desc[:160])

    return {
        "items": len(evidence),
        "grounded": grounded,
        "score": round(grounded / len(evidence), 3),
        "ungrounded_examples": ungrounded[:5],
    }


def consistency(confidences: list[float]) -> dict:
    """Spread across repeated runs of the same member. High spread argues for
    temperature zero and undermines any single reported number."""
    if len(confidences) < 2:
        return {"runs": len(confidences), "spread": 0.0, "mean": confidences[0] if confidences else 0.0}
    mean = sum(confidences) / len(confidences)
    return {
        "runs": len(confidences),
        "mean": round(mean, 3),
        "min": round(min(confidences), 3),
        "max": round(max(confidences), 3),
        "spread": round(max(confidences) - min(confidences), 3),
    }


# --------------------------------------------------------------------------
# 4. Perturbation
# --------------------------------------------------------------------------

PROCEDURE_WORDS = re.compile(
    r"knee|hip|cataract|replacement|arthroplasty|surger|procedure|operat|orthoped",
    re.I,
)

DENIAL_SENTENCE = (
    "Member stated explicitly that no surgery is scheduled and that they are "
    "continuing conservative treatment for now."
)


def perturbation_cases(packet: dict) -> dict[str, dict]:
    """Build three variants of one member's payload.

    baseline    - unchanged
    stripped    - summary sentences naming a procedure removed
    contradicted- an explicit denial appended

    Expected behaviour: confidence(baseline) > confidence(stripped) and
    confidence(baseline) > confidence(contradicted). Flat confidence across all
    three is evidence of anchoring rather than reasoning.
    """
    baseline = json.loads(json.dumps(packet, default=str))

    stripped = json.loads(json.dumps(packet, default=str))
    for call in stripped.get("recent_agent_assist_summaries", []):
        for field in ("summary", "member_need", "follow_up_note"):
            text = call.get(field)
            if not text:
                continue
            kept = [s for s in re.split(r"(?<=[.;])\s+", text) if not PROCEDURE_WORDS.search(s)]
            call[field] = " ".join(kept).strip()

    contradicted = json.loads(json.dumps(packet, default=str))
    calls = contradicted.get("recent_agent_assist_summaries")
    if calls:
        last = calls[-1]
        last["summary"] = ((last.get("summary") or "") + " " + DENIAL_SENTENCE).strip()

    return {"baseline": baseline, "stripped": stripped, "contradicted": contradicted}


def perturbation_verdict(baseline: float, stripped: float, contradicted: float,
                         tolerance: float = 0.05) -> dict:
    drop_stripped = baseline - stripped
    drop_contradicted = baseline - contradicted
    passed = drop_stripped > tolerance and drop_contradicted > tolerance
    return {
        "baseline_confidence": round(baseline, 3),
        "stripped_confidence": round(stripped, 3),
        "contradicted_confidence": round(contradicted, 3),
        "drop_when_evidence_removed": round(drop_stripped, 3),
        "drop_when_contradicted": round(drop_contradicted, 3),
        "passed": passed,
        "interpretation": (
            "Confidence responds to evidence as expected."
            if passed else
            "Confidence did not move materially when evidence was removed or "
            "contradicted. This indicates anchoring rather than reasoning, and "
            "is the strongest argument for reporting bands rather than a "
            "two-significant-figure percentage."
        ),
    }


# --------------------------------------------------------------------------
# Run bookkeeping
# --------------------------------------------------------------------------

def new_run(db: Session, kind: str, index_date: str, threshold: float, total: int) -> str:
    run_id = uuid.uuid4().hex[:12]
    db.add(models.EvalRun(
        run_id=run_id, kind=kind, index_date=index_date, threshold=threshold,
        model=settings.openai_model, prompt_version=settings.prompt_version,
        status="running", total=total, completed=0,
    ))
    db.commit()
    return run_id


def finish_run(db: Session, run_id: str, result: dict) -> None:
    run = db.get(models.EvalRun, run_id)
    if run:
        run.status = "complete"
        run.completed = run.total
        run.result_json = json.dumps(result, default=str)
        db.commit()


def fail_run(db: Session, run_id: str, error: str) -> None:
    run = db.get(models.EvalRun, run_id)
    if run:
        run.status = "error"
        run.error = error[:900]
        db.commit()
