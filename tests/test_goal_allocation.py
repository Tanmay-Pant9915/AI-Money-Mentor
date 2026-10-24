"""
tests/test_goal_allocation.py
Automated unit tests for risk-aware, horizon-aligned category asset allocations,
guardrails separating capacity from tolerance, and 100% normalization.
"""
import pytest

from utils.goal_allocation import (
    ASSET_CLASSES,
    determine_horizon_category,
    generate_goal_asset_allocation,
)


def _sum_allocations(alloc_dict):
    return sum(v["percentage"] for v in alloc_dict.values())


def test_determine_horizon_category():
    assert determine_horizon_category(12) == "Short-Term (< 3 Years)"
    assert determine_horizon_category(36) == "Short-Term (< 3 Years)"
    assert determine_horizon_category(48) == "Medium-Term (3–5 Years)"
    assert determine_horizon_category(60) == "Medium-Term (3–5 Years)"
    assert determine_horizon_category(72) == "Long-Term (5+ Years)"


def test_allocation_ultra_short_horizon():
    # <= 12 months: must have zero equity exposure for capital preservation
    res = generate_goal_asset_allocation(
        remaining_months=10,
        risk_classification="Aggressive",
    )
    alloc = res["allocations"]
    assert _sum_allocations(alloc) == 100.0
    assert alloc["equity_funds"]["percentage"] == 0.0
    assert alloc["hybrid_funds"]["percentage"] == 0.0
    assert alloc["liquid_savings"]["percentage"] >= 40.0


def test_allocation_short_term():
    res = generate_goal_asset_allocation(
        remaining_months=24,
        risk_classification="Moderate",
    )
    alloc = res["allocations"]
    assert _sum_allocations(alloc) == 100.0
    assert all(v["percentage"] >= 0 for v in alloc.values())


def test_allocation_medium_term_profiles():
    # 48 months: compare Conservative vs Moderate vs Aggressive
    c_res = generate_goal_asset_allocation(48, risk_classification="Conservative")
    m_res = generate_goal_asset_allocation(48, risk_classification="Moderate")
    a_res = generate_goal_asset_allocation(48, risk_classification="Aggressive", goal_priority="Medium")

    assert _sum_allocations(c_res["allocations"]) == 100.0
    assert _sum_allocations(m_res["allocations"]) == 100.0
    assert _sum_allocations(a_res["allocations"]) == 100.0

    # Equity share increases from Conservative to Aggressive
    c_eq = c_res["allocations"]["equity_funds"]["percentage"]
    m_eq = m_res["allocations"]["equity_funds"]["percentage"]
    a_eq = a_res["allocations"]["equity_funds"]["percentage"]
    assert c_eq < m_eq <= a_eq


def test_allocation_long_term_aggressive():
    # 120 months (10 years), Aggressive
    res = generate_goal_asset_allocation(
        remaining_months=120,
        risk_classification="Aggressive",
        capacity_score=80.0,
    )
    alloc = res["allocations"]
    assert _sum_allocations(alloc) == 100.0
    assert alloc["equity_funds"]["percentage"] >= 60.0
    assert res["effective_risk"] == "Aggressive"


def test_capacity_guardrail_low_capacity():
    # User is classified as Aggressive psychologically, but has objective capacity_score = 30 (< 40)
    res = generate_goal_asset_allocation(
        remaining_months=84,
        risk_classification="Aggressive",
        capacity_score=30.0,
        tolerance_score=85.0,
    )
    assert res["effective_risk"] == "Moderate"
    assert any("Capacity Guardrail" in g for g in res["guardrails_applied"])
    assert _sum_allocations(res["allocations"]) == 100.0


def test_deficit_guardrail():
    # User is Aggressive, but currently operates in a monthly cash flow deficit
    res = generate_goal_asset_allocation(
        remaining_months=84,
        risk_classification="Aggressive",
        is_deficit=True,
    )
    assert res["effective_risk"] == "Conservative"
    assert any("Cash-Flow Deficit" in g for g in res["guardrails_applied"])
    assert _sum_allocations(res["allocations"]) == 100.0


def test_high_priority_near_term_protection():
    # High priority goal due in 36 months under Aggressive risk profile
    res = generate_goal_asset_allocation(
        remaining_months=36,
        risk_classification="Aggressive",
        goal_priority="High",
    )
    assert res["effective_risk"] == "Moderate"
    assert any("Priority Protection" in g for g in res["guardrails_applied"])


def test_missing_risk_profile_defaults_to_moderate():
    res = generate_goal_asset_allocation(
        remaining_months=60,
        risk_classification=None,
    )
    assert res["effective_risk"] == "Moderate"
    assert _sum_allocations(res["allocations"]) == 100.0
