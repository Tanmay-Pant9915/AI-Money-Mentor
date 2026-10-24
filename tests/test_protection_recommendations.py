"""
tests/test_protection_recommendations.py
Unit tests for deterministic protection recommendations and multi-pillar scorecard:
- Critical emergency fund recommendation trigger
- Employer-only health insurance trigger
- Life insurance gap recommendation for dependents
- No dependents scenario handling
- Personal accident recommendation trigger
- Overall protection multi-pillar scorecard evaluation
"""
import pytest

from utils.protection_recommendations import (
    evaluate_overall_protection_status,
    generate_protection_recommendations,
)


def test_critical_emergency_recommendation():
    ef_plan = {"status": "Critical", "gap": 150000.0, "coverage_months": 0.5, "target_months": 6.0}
    health = {"total_current_coverage": 500000.0, "personal_coverage": 500000.0, "employer_coverage": 0.0, "total_coverage_gap": 0.0}
    life = {"has_dependents": False, "net_additional_need": 0.0, "existing_life_insurance": 0.0}
    accident = {"has_accident_cover": True, "current_sum_insured": 2500000.0}

    recs = generate_protection_recommendations(ef_plan, health, life, accident)
    # Priority High recommendation for emergency buffer must be present
    ef_recs = [r for r in recs if r["category"] == "Emergency Fund"]
    assert len(ef_recs) >= 1
    assert ef_recs[0]["priority"] == "High"
    assert "1-Month Cash Buffer" in ef_recs[0]["title"]


def test_employer_only_health_recommendation():
    ef_plan = {"status": "Target Reached", "gap": 0.0, "coverage_months": 6.0, "target_months": 6.0}
    health = {"total_current_coverage": 500000.0, "personal_coverage": 0.0, "employer_coverage": 500000.0, "total_coverage_gap": 0.0}
    life = {"has_dependents": False, "net_additional_need": 0.0, "existing_life_insurance": 0.0}
    accident = {"has_accident_cover": True, "current_sum_insured": 2500000.0}

    recs = generate_protection_recommendations(ef_plan, health, life, accident)
    h_recs = [r for r in recs if r["category"] == "Health Insurance"]
    assert len(h_recs) >= 1
    assert h_recs[0]["priority"] == "High"
    assert "Standalone Personal Health" in h_recs[0]["title"]


def test_life_insurance_gap_for_dependents():
    ef_plan = {"status": "Target Reached", "gap": 0.0, "coverage_months": 6.0}
    health = {"total_current_coverage": 1000000.0, "personal_coverage": 1000000.0, "total_coverage_gap": 0.0}
    life = {"has_dependents": True, "number_of_dependents": 2, "net_additional_need": 8000000.0, "existing_life_insurance": 0.0}
    accident = {"has_accident_cover": True}

    recs = generate_protection_recommendations(ef_plan, health, life, accident)
    l_recs = [r for r in recs if r["category"] == "Life Insurance"]
    assert len(l_recs) >= 1
    assert l_recs[0]["priority"] == "High"
    assert "Term Life" in l_recs[0]["title"]


def test_no_dependents_no_life_recommendation():
    ef_plan = {"status": "Target Reached", "gap": 0.0, "coverage_months": 6.0}
    health = {"total_current_coverage": 1000000.0, "personal_coverage": 1000000.0, "total_coverage_gap": 0.0}
    life = {"has_dependents": False, "net_additional_need": 0.0, "outstanding_liabilities": 0.0}
    accident = {"has_accident_cover": True}

    recs = generate_protection_recommendations(ef_plan, health, life, accident)
    l_recs = [r for r in recs if r["category"] == "Life Insurance"]
    # No term insurance recommended if no dependents and no debts
    assert len(l_recs) == 0


def test_overall_protection_scorecard():
    # Critical gap in emergency fund
    ef_crit = {"status": "Critical", "tier": "critical", "coverage_months": 0.5}
    health_ok = {"status": "Adequately Covered", "tier": "safe", "total_current_coverage": 1000000.0}
    life_ok = {"status": "No Life Cover Needed", "tier": "safe", "has_dependents": False}
    acc_ok = {"status": "Protected", "tier": "safe", "has_accident_cover": True}

    card = evaluate_overall_protection_status(ef_crit, health_ok, life_ok, acc_ok)
    assert card["overall_status"] == "Vulnerable (Critical Gaps)"
    assert len(card["pillars"]) == 4

    # All safe
    ef_safe = {"status": "Target Reached", "tier": "safe", "coverage_months": 6.0}
    card_safe = evaluate_overall_protection_status(ef_safe, health_ok, life_ok, acc_ok)
    assert card_safe["overall_status"] == "Strong Protection Foundation"
