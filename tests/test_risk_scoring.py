"""
tests/test_risk_scoring.py
Unit tests for deterministic risk questionnaire scoring, normalization,
boundary thresholds, and financial capacity guardrails.
"""
import pytest

from utils.risk_scoring import (
    CAPACITY_Q_IDS,
    RISK_QUESTIONS,
    TOLERANCE_Q_IDS,
    calculate_risk_profile,
    classify_score,
    normalize_score,
)


def make_uniform_answers(score: int):
    return {q["id"]: score for q in RISK_QUESTIONS}


class TestRiskScoreCalculations:

    def test_minimum_possible_score(self):
        """All 1s should give normalized score 0.0 and Conservative classification."""
        answers = make_uniform_answers(1)
        res = calculate_risk_profile(answers)
        assert res["score"] == 0.0
        assert res["capacity_score"] == 0.0
        assert res["tolerance_score"] == 0.0
        assert res["classification"] == "Conservative"
        assert res["guardrail_applied"] is False

    def test_maximum_possible_score(self):
        """All 4s should give normalized score 100.0 and Aggressive classification."""
        answers = make_uniform_answers(4)
        res = calculate_risk_profile(answers)
        assert res["score"] == 100.0
        assert res["capacity_score"] == 100.0
        assert res["tolerance_score"] == 100.0
        assert res["classification"] == "Aggressive"
        assert res["guardrail_applied"] is False

    def test_moderate_score(self):
        """A balanced pattern (mix of 2s and 3s) produces a Moderate classification."""
        answers = {q["id"]: (2 if i % 2 == 0 else 3) for i, q in enumerate(RISK_QUESTIONS)}
        res = calculate_risk_profile(answers)
        assert res["classification"] == "Moderate"
        assert 34.0 <= res["score"] <= 66.0

    def test_score_determinism(self):
        """Identical answers must produce identical outputs."""
        answers = {q["id"]: ((i % 4) + 1) for i, q in enumerate(RISK_QUESTIONS)}
        res_a = calculate_risk_profile(answers)
        res_b = calculate_risk_profile(answers)
        assert res_a == res_b

    def test_missing_or_invalid_answers_raise_error(self):
        # Missing one answer
        incomplete = {q["id"]: 2 for q in RISK_QUESTIONS[:-1]}
        with pytest.raises(ValueError, match="Missing or invalid"):
            calculate_risk_profile(incomplete)

        # Invalid answer value (e.g. 5 or -1)
        invalid = make_uniform_answers(2)
        invalid["q1_life_stage"] = 5
        with pytest.raises(ValueError, match="Missing or invalid"):
            calculate_risk_profile(invalid)


class TestThresholdBoundaries:

    def test_classify_score_boundaries(self):
        # 0 to 33: Conservative
        assert classify_score(0.0) == "Conservative"
        assert classify_score(20.0) == "Conservative"
        assert classify_score(33.0) == "Conservative"

        # 34 to 66: Moderate
        assert classify_score(34.0) == "Moderate"
        assert classify_score(50.0) == "Moderate"
        assert classify_score(66.0) == "Moderate"

        # 67 to 100: Aggressive
        assert classify_score(67.0) == "Aggressive"
        assert classify_score(80.0) == "Aggressive"
        assert classify_score(100.0) == "Aggressive"

    def test_normalization(self):
        assert normalize_score(12, 12, 48) == 0.0
        assert normalize_score(48, 12, 48) == 100.0
        assert normalize_score(30, 12, 48) == 50.0


class TestCapacityGuardrails:

    def test_high_tolerance_with_low_capacity_is_capped_at_moderate(self):
        """
        User selects all 4s (aggressive) on psychological tolerance questions (q5-q8, q11-q12),
        but has low capacity (score 1 or 2, capacity_score <= 33).
        Guardrail must cap classification at Moderate.
        """
        answers = {}
        # Low capacity (all 1s or 2s)
        for qid in CAPACITY_Q_IDS:
            answers[qid] = 2  # capacity score: 33.3%
        # High tolerance (all 4s)
        for qid in TOLERANCE_Q_IDS:
            answers[qid] = 4  # tolerance score: 100.0%

        res = calculate_risk_profile(answers)
        assert res["tolerance_score"] == 100.0
        assert res["capacity_score"] <= 33.4
        # Even if overall normalized score would be > 66.0:
        assert res["preliminary_classification"] == "Aggressive"
        assert res["classification"] == "Moderate"
        assert res["guardrail_applied"] is True
        assert len(res["guardrail_reasons"]) > 0

    def test_critical_capacity_is_capped_at_conservative(self):
        """
        User has critically low capacity (score 1 on all capacity questions, capacity_score = 0.0),
        even with moderate or high tolerance, classification is capped at Conservative.
        """
        answers = {}
        for qid in CAPACITY_Q_IDS:
            answers[qid] = 1  # 0.0% capacity
        for qid in TOLERANCE_Q_IDS:
            answers[qid] = 4  # high tolerance (preliminary score 50% -> Moderate)

        res = calculate_risk_profile(answers)
        assert res["capacity_score"] == 0.0
        assert res["preliminary_classification"] == "Moderate"
        assert res["classification"] == "Conservative"
        assert res["guardrail_applied"] is True

    def test_constraints_detection(self):
        answers = make_uniform_answers(3)
        answers["q3_emergency_fund"] = 1  # less than 1 month
        answers["q4_time_horizon"] = 1   # 1-2 years
        res = calculate_risk_profile(answers)
        assert any("Emergency cash reserve" in c for c in res["constraints"])
        assert any("1–2 years" in c for c in res["constraints"])
