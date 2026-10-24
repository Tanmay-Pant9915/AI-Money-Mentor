"""
tests/test_emergency_fund_calculator.py
Unit tests for deterministic emergency fund calculations:
- Target amount calculation
- Coverage in months
- Remaining target gap
- Progress percentage (capped and uncapped)
- Target already achieved scenarios
- Zero essential expenses edge cases
- Zero monthly contribution handling
- Monthly deficit scenarios
- Contribution greater than the gap
- Estimated completion months and calendar date
- Missing data handling
- Contribution scenario affordability
"""
from datetime import date
import pytest

from utils.emergency_fund_calculator import (
    calculate_completion_date,
    calculate_emergency_fund_coverage,
    calculate_emergency_fund_gap,
    calculate_emergency_fund_progress,
    calculate_emergency_fund_target,
    calculate_months_to_target,
    evaluate_contribution_scenarios,
    get_emergency_fund_status,
    recommend_monthly_contribution,
)


def test_target_calculation():
    # 40,000 essential expenses * 6 months = 2,40,000
    tgt = calculate_emergency_fund_target(essential_expenses=40000.0, target_months=6.0)
    assert tgt == 240000.0

    # 50,000 * 3 months = 1,50,000
    tgt3 = calculate_emergency_fund_target(essential_expenses=50000.0, target_months=3.0)
    assert tgt3 == 150000.0

    # Custom 9 months
    tgt9 = calculate_emergency_fund_target(essential_expenses=30000.0, target_months=9.0)
    assert tgt9 == 270000.0


def test_coverage_in_months():
    # 1,20,000 savings / 40,000 essential = 3.0 months
    cov = calculate_emergency_fund_coverage(current_savings=120000.0, essential_expenses=40000.0)
    assert cov == 3.0

    # 60,000 / 40,000 = 1.5 months
    cov15 = calculate_emergency_fund_coverage(current_savings=60000.0, essential_expenses=40000.0)
    assert cov15 == 1.5


def test_zero_essential_expenses():
    # Essential expenses = 0: coverage must be safely 0.0 (no division by zero)
    cov = calculate_emergency_fund_coverage(current_savings=100000.0, essential_expenses=0.0)
    assert cov == 0.0

    tgt = calculate_emergency_fund_target(essential_expenses=0.0, target_months=6.0)
    assert tgt == 0.0


def test_remaining_target_gap():
    # Target 3,00,000, current savings 1,00,000 -> Gap = 2,00,000
    gap = calculate_emergency_fund_gap(target_amount=300000.0, current_savings=100000.0)
    assert gap == 200000.0

    # Savings exceed target -> Gap is strictly 0.0 (no negative gap)
    gap_surplus = calculate_emergency_fund_gap(target_amount=300000.0, current_savings=450000.0)
    assert gap_surplus == 0.0


def test_progress_percentage():
    # 1,50,000 savings against 3,00,000 target = 50.0%
    prog = calculate_emergency_fund_progress(current_savings=150000.0, target_amount=300000.0)
    assert prog["progress_pct"] == 50.0
    assert prog["actual_pct"] == 50.0
    assert prog["is_target_reached"] is False

    # 4,00,000 savings against 3,00,000 target -> display capped at 100%, actual is 133.3%
    prog_surplus = calculate_emergency_fund_progress(current_savings=400000.0, target_amount=300000.0)
    assert prog_surplus["progress_pct"] == 100.0
    assert prog_surplus["actual_pct"] == 133.3
    assert prog_surplus["is_target_reached"] is True
    assert prog_surplus["surplus_amount"] == 100000.0


def test_target_already_achieved():
    timing = calculate_months_to_target(gap=0.0, monthly_contribution=10000.0)
    assert timing["months"] == 0
    assert timing["is_reachable"] is True

    comp_date = calculate_completion_date(months=0, start_date=date(2026, 1, 15))
    assert comp_date == date(2026, 1, 15)


def test_zero_monthly_contribution():
    # Gap exists, but monthly contribution is 0: not reachable via contribution
    timing = calculate_months_to_target(gap=150000.0, monthly_contribution=0.0)
    assert timing["months"] is None
    assert timing["is_reachable"] is False


def test_contribution_greater_than_gap():
    # Gap 5,000, contribution 20,000 -> 1 month
    timing = calculate_months_to_target(gap=5000.0, monthly_contribution=20000.0)
    assert timing["months"] == 1
    assert timing["is_reachable"] is True


def test_estimated_completion_months_and_date():
    # Gap 1,25,000, contribution 10,000 -> ceil(12.5) = 13 months
    timing = calculate_months_to_target(gap=125000.0, monthly_contribution=10000.0)
    assert timing["months"] == 13

    start = date(2026, 3, 10)
    completion = calculate_completion_date(months=13, start_date=start)
    assert completion == date(2027, 4, 10)


def test_emergency_fund_status_categories():
    # Critical: < 1 month
    crit = get_emergency_fund_status(coverage_months=0.5, target_months=6.0)
    assert crit["status"] == "Critical"
    assert crit["tier"] == "critical"

    # Low: 1 to < 3 months
    low = get_emergency_fund_status(coverage_months=2.0, target_months=6.0)
    assert low["status"] == "Low"
    assert low["tier"] == "warning"

    # Building: 3 to < target
    bld = get_emergency_fund_status(coverage_months=4.5, target_months=6.0)
    assert bld["status"] == "Building"
    assert bld["tier"] == "info"

    # Target reached
    rch = get_emergency_fund_status(coverage_months=6.5, target_months=6.0)
    assert rch["status"] == "Target Reached"
    assert rch["tier"] == "safe"


def test_recommend_monthly_contribution_with_surplus_and_deficit():
    # Positive surplus: 30,000 surplus, gap 1,20,000 -> suggests up to 50% or ideal pace
    rec = recommend_monthly_contribution(available_surplus=30000.0, gap=120000.0)
    assert rec["is_affordable"] is True
    assert rec["recommended_monthly"] > 0
    assert rec["recommended_monthly"] <= 30000.0

    # Monthly deficit: -5,000 surplus -> cannot invent money
    rec_def = recommend_monthly_contribution(available_surplus=-5000.0, gap=120000.0)
    assert rec_def["is_affordable"] is False
    assert rec_def["recommended_monthly"] == 0.0
    assert rec_def["status"] == "Cash Flow Deficit"


def test_contribution_scenario_affordability():
    # Gap 1,00,000, surplus 7,000
    scenarios = evaluate_contribution_scenarios(
        gap=100000.0,
        available_surplus=7000.0,
        scenarios=[2000.0, 5000.0, 10000.0],
        start_date=date(2026, 1, 1),
    )
    assert len(scenarios) == 3

    # ₹2,000 and ₹5,000 are affordable (<= 7,000)
    assert scenarios[0]["monthly_amount"] == 2000.0
    assert scenarios[0]["is_affordable"] is True
    assert scenarios[0]["months_to_target"] == 50

    assert scenarios[1]["monthly_amount"] == 5000.0
    assert scenarios[1]["is_affordable"] is True
    assert scenarios[1]["months_to_target"] == 20

    # ₹10,000 exceeds surplus of 7,000 -> not affordable
    assert scenarios[2]["monthly_amount"] == 10000.0
    assert scenarios[2]["is_affordable"] is False
    assert scenarios[2]["affordability_status"] == "Exceeds Surplus"
