"""Unit tests for the deterministic layer.

This is the layer the product asks a reviewer to trust when it claims the model
does not touch the facts, so it is the first thing that should be tested. It is
pure and side-effect free, which makes it trivially testable.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.care_intent import _canonicalize_event, confidence_band  # noqa: E402
from app.services import eval_service  # noqa: E402
from app.services.readiness import SCORE_WEIGHTS, _mentions  # noqa: E402


# --------------------------------------------------------- provider matching
@pytest.mark.parametrize("name,text,expected", [
    ("Lee", "i believe the claim was processed", False),      # substring false positive
    ("Park", "i had trouble with parking at the clinic", False),
    ("Maya Chen", "asked whether dr maya chen is in network", True),
    ("North Valley Medical Center", "network status for north valley medical center", True),
    ("Ross", "the crossroads facility", False),
    ("", "anything at all", False),
    (None, "anything at all", False),
])
def test_word_boundary_matching(name, text, expected):
    assert _mentions(name, text) is expected


def test_short_names_never_match():
    """A length floor prevents two- and three-letter names matching inside words."""
    assert _mentions("Ng", "eating") is False
    assert _mentions("Abe", "abetted") is False


# ------------------------------------------------------------ score weights
def test_weights_sum_within_range():
    assert all(0 < v <= 30 for v in SCORE_WEIGHTS.values())


def test_out_of_network_is_the_heaviest_deduction():
    """Documented rationale: largest member cost exposure, longest lead time."""
    assert SCORE_WEIGHTS["network_out_of_network"] == max(SCORE_WEIGHTS.values())


# ----------------------------------------------------------- canonicalisation
@pytest.mark.parametrize("raw,expected", [
    ("total knee arthroplasty", "Total knee replacement"),
    ("Knee Replacement (left)", "Total knee replacement"),
    ("total hip arthroplasty", "Total hip replacement"),
    ("cataract extraction", "Cataract surgery"),
    ("coronary bypass", "coronary bypass"),
    (None, None),
])
def test_event_canonicalisation(raw, expected):
    assert _canonicalize_event(raw) == expected


# ------------------------------------------------------------------- banding
@pytest.mark.parametrize("confidence,band", [
    (0.95, "HIGH"), (0.85, "HIGH"), (0.84, "MODERATE_HIGH"), (0.70, "MODERATE_HIGH"),
    (0.69, "MODERATE"), (0.45, "MODERATE"), (0.44, "LOW"), (0.20, "LOW"), (0.05, "MINIMAL"),
])
def test_confidence_bands(confidence, band):
    assert confidence_band(confidence) == band


# ---------------------------------------------------------------- groundedness
def test_groundedness_flags_fabrication():
    packet = {"recent_agent_assist_summaries": [
        {"summary": "Member asked about orthopedic claim cost share."}]}
    evidence = [
        {"description": "Member asked about orthopedic claim cost share"},
        {"description": "Member reported scheduling cardiac catheterization angioplasty next Tuesday"},
    ]
    result = eval_service.groundedness(evidence, packet)
    assert result["items"] == 2
    assert result["grounded"] == 1
    assert result["score"] == 0.5
    assert result["ungrounded_examples"]


def test_groundedness_perfect_when_all_cited_content_present():
    packet = {"recent_claims": [{"procedure_description": "orthopedic consultation"}]}
    evidence = [{"description": "orthopedic consultation on file"}]
    assert eval_service.groundedness(evidence, packet)["score"] == 1.0


# ----------------------------------------------------------------- perturbation
def test_perturbation_strips_procedure_sentences():
    packet = {"recent_agent_assist_summaries": [
        {"summary": "Member asked about a bill. Member said the orthopedist "
                    "discussed knee replacement as a next step."}]}
    cases = eval_service.perturbation_cases(packet)
    stripped = cases["stripped"]["recent_agent_assist_summaries"][0]["summary"]
    assert "knee replacement" not in stripped.lower()
    assert "bill" in stripped.lower()
    # The baseline must not be mutated by building the variants.
    assert "knee replacement" in cases["baseline"]["recent_agent_assist_summaries"][0]["summary"].lower()


def test_perturbation_appends_a_denial():
    packet = {"recent_agent_assist_summaries": [{"summary": "Member asked about coverage."}]}
    cases = eval_service.perturbation_cases(packet)
    assert "no surgery is scheduled" in cases["contradicted"]["recent_agent_assist_summaries"][0]["summary"].lower()


def test_perturbation_verdict_detects_anchoring():
    flat = eval_service.perturbation_verdict(0.84, 0.84, 0.83)
    assert flat["passed"] is False
    assert "anchoring" in flat["interpretation"]

    responsive = eval_service.perturbation_verdict(0.88, 0.42, 0.21)
    assert responsive["passed"] is True


# --------------------------------------------------------------------- scoring
class _FakeLabel:
    def __init__(self, label, procedure=""):
        self.label = label
        self.actual_procedure = procedure
        self.days_from_index = 30


def test_scoring_excludes_ambiguous(monkeypatch):
    labels = {
        "M1": _FakeLabel("UPCOMING_PROCEDURE", "Total knee replacement"),
        "M2": _FakeLabel("NO_EVIDENCE"),
        "M3": _FakeLabel("AMBIGUOUS"),
    }
    monkeypatch.setattr(eval_service, "get_labels", lambda db: labels)
    predictions = [
        {"member_id": "M1", "confidence": 0.9, "predicted_care_event": "Total knee replacement"},
        {"member_id": "M2", "confidence": 0.1, "predicted_care_event": None},
        {"member_id": "M3", "confidence": 0.9, "predicted_care_event": "Cataract surgery"},
    ]
    result = eval_service.score_predictions(None, predictions, 0.7)
    assert result["scored_members"] == 2
    assert result["excluded_ambiguous"] == 1
    assert result["true_positives"] == 1
    assert result["true_negatives"] == 1
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["procedure_named_correctly"] == 1


def test_scoring_counts_misses(monkeypatch):
    labels = {"M1": _FakeLabel("UPCOMING_PROCEDURE", "Total hip replacement")}
    monkeypatch.setattr(eval_service, "get_labels", lambda db: labels)
    result = eval_service.score_predictions(
        None, [{"member_id": "M1", "confidence": 0.3, "predicted_care_event": None}], 0.7)
    assert result["false_negatives"] == 1
    assert result["recall"] == 0.0
