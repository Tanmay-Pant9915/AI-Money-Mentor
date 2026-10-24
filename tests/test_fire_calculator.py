"""
tests/test_fire_calculator.py
Unit tests for deterministic FIRE (Financial Independence, Retire Early) calculations:
- FIRE corpus estimation using SWR multiples
- Nominal vs. real inflation adjustments
- Month-by-month timeline and FIRE age solver
- Infeasible and already-FIRE edge cases
- Savings rate matrix and impact analysis
"""
import pytest

from utils.fire_calculator import (
    calculate_fire_corpus,
    calculate_fire_timeline,
    calculate_savings_rate_table,
    calculate_target_fire_age_analysis,
)


def test_fire_corpus_calculation():
    # 6,00,000 annual expenses (50,000/mo) at 4% SWR -> 25x = 1,50,00,000 (1.5 Crore)
    res_4 = calculate_fire_corpus(
        annual_expenses_today=600000.0,
        safe_withdrawal_rate=4.0,
        years_to_fire=0.0,
    )
    assert res_4["real_fire_corpus_today"] == 15000000.0
    assert res_4["corpus_multiple"] == 25.0

    # At 3.33% SWR -> 30x = 1,80,00,000 (1.8 Crore)
    res_33 = calculate_fire_corpus(
        annual_expenses_today=600000.0,
        safe_withdrawal_rate=3.33333333,
        years_to_fire=0.0,
    )
    assert abs(res_33["real_fire_corpus_today"] - 18000000.0) < 100.0


def test_fire_corpus_nominal_inflation():
    # 10 years at 6% inflation -> multiplier = 1.06^10 = 1.7908
    res = calculate_fire_corpus(
        annual_expenses_today=600000.0,
        safe_withdrawal_rate=3.5,
        years_to_fire=10.0,
        annual_inflation_rate=6.0,
    )
    assert res["nominal_fire_corpus_at_fire"] > res["real_fire_corpus_today"]
    assert res["inflation_multiplier"] > 1.7


def test_fire_timeline_already_at_target():
    # Target at 4% SWR for 4,00,000 expenses is 1 Crore.
    # Current assets: 1.2 Crore
    res = calculate_fire_timeline(
        current_age=35,
        current_invested_assets=12000000.0,
        monthly_investment_contribution=50000.0,
        annual_expenses_today=400000.0,
        safe_withdrawal_rate=4.0,
    )
    assert res["is_feasible"] is True
    assert res["is_already_fire"] is True
    assert res["years_to_fire"] == 0.0
    assert res["fire_age"] == 35


def test_fire_timeline_achievable():
    # Age 30, starting with 10 Lakhs, investing 40,000/mo, annual expenses 4.8 Lakhs (40,000/mo)
    # Expected return 12%, inflation 6%, SWR 3.5%
    res = calculate_fire_timeline(
        current_age=30,
        current_invested_assets=1000000.0,
        monthly_investment_contribution=40000.0,
        annual_expenses_today=480000.0,
        assumed_annual_return=12.0,
        annual_inflation_rate=6.0,
        safe_withdrawal_rate=3.5,
    )
    assert res["is_feasible"] is True
    assert res["is_already_fire"] is False
    assert res["years_to_fire"] is not None
    assert 5.0 < res["years_to_fire"] < 25.0
    assert res["fire_age"] == round(30 + res["years_to_fire"], 1)
    assert len(res["trajectory"]) > 0


def test_fire_timeline_infeasible():
    # Age 40, zero current corpus, 1,000/mo investment, but 12,00,000 annual expenses (1 Lakh/mo)
    res = calculate_fire_timeline(
        current_age=40,
        current_invested_assets=0.0,
        monthly_investment_contribution=1000.0,
        annual_expenses_today=1200000.0,
        assumed_annual_return=8.0,
        annual_inflation_rate=6.0,
        safe_withdrawal_rate=3.5,
    )
    assert res["is_feasible"] is False
    assert res["years_to_fire"] is None
    assert res["projected_shortfall"] > 0


def test_savings_rate_table():
    # Monthly income 1,00,000. As savings rate increases from 20% to 70%,
    # years to FIRE must strictly decrease.
    table = calculate_savings_rate_table(
        monthly_income=100000.0,
        current_age=28,
        current_invested_assets=500000.0,
        assumed_annual_return=11.0,
        annual_inflation_rate=6.0,
        safe_withdrawal_rate=3.5,
    )
    assert len(table) == 7

    feasible_rows = [r for r in table if r["is_feasible"] and r["years_to_fire"] is not None]
    assert len(feasible_rows) >= 3

    # Check monotonicity: higher savings rate leads to fewer years to FIRE
    for i in range(len(feasible_rows) - 1):
        assert feasible_rows[i]["years_to_fire"] >= feasible_rows[i + 1]["years_to_fire"]


def test_fire_conservative_assumptions():
    # Conservative return 8%, higher inflation 7%, low SWR 3.0%
    res = calculate_fire_timeline(
        current_age=32,
        current_invested_assets=1500000.0,
        monthly_investment_contribution=35000.0,
        annual_expenses_today=600000.0,
        assumed_annual_return=8.0,
        annual_inflation_rate=7.0,
        safe_withdrawal_rate=3.0,
    )
    assert res["real_fire_corpus"] == 20000000.0  # 600k / 0.03 = 2 Crore


def test_fire_moderate_assumptions():
    # Moderate return 10%, inflation 6%, SWR 3.5%
    res = calculate_fire_timeline(
        current_age=30,
        current_invested_assets=1000000.0,
        monthly_investment_contribution=40000.0,
        annual_expenses_today=500000.0,
        assumed_annual_return=10.0,
        annual_inflation_rate=6.0,
        safe_withdrawal_rate=3.5,
    )
    assert res["is_feasible"] is True
    assert res["years_to_fire"] is not None


def test_fire_higher_contribution_scenarios():
    # Doubling contribution from 30,000 to 60,000 must strictly accelerate FIRE date
    res_base = calculate_fire_timeline(
        current_age=30,
        current_invested_assets=500000.0,
        monthly_investment_contribution=30000.0,
        annual_expenses_today=480000.0,
        assumed_annual_return=10.0,
        annual_inflation_rate=6.0,
        safe_withdrawal_rate=3.5,
    )
    res_high = calculate_fire_timeline(
        current_age=30,
        current_invested_assets=500000.0,
        monthly_investment_contribution=60000.0,
        annual_expenses_today=480000.0,
        assumed_annual_return=10.0,
        annual_inflation_rate=6.0,
        safe_withdrawal_rate=3.5,
    )
    assert res_base["is_feasible"] is True
    assert res_high["is_feasible"] is True
    assert res_high["years_to_fire"] < res_base["years_to_fire"]


def test_fire_zero_savings_and_corpus():
    # Starting from 0 corpus, with positive monthly contribution
    res = calculate_fire_timeline(
        current_age=25,
        current_invested_assets=0.0,
        monthly_investment_contribution=50000.0,
        annual_expenses_today=400000.0,
        assumed_annual_return=11.0,
        annual_inflation_rate=6.0,
        safe_withdrawal_rate=3.5,
    )
    assert res["is_feasible"] is True
    assert res["years_to_fire"] is not None
    assert res["years_to_fire"] > 0


def test_fire_different_expense_assumptions():
    # Trimming annual expenses from 8 Lakhs to 4 Lakhs reduces real FIRE target by 50%
    c_high = calculate_fire_corpus(annual_expenses_today=800000.0, safe_withdrawal_rate=3.5)
    c_low = calculate_fire_corpus(annual_expenses_today=400000.0, safe_withdrawal_rate=3.5)
    assert c_low["real_fire_corpus_today"] == round(c_high["real_fire_corpus_today"] / 2.0, 2)


def test_target_fire_age_analysis():
    # Test specific target FIRE age analysis at age 45
    res = calculate_target_fire_age_analysis(
        current_age=30,
        current_invested_assets=1000000.0,
        monthly_investment_contribution=40000.0,
        annual_expenses_today=480000.0,
        target_fire_age=45,
        assumed_annual_return=10.0,
        annual_inflation_rate=6.0,
        safe_withdrawal_rate=3.5,
    )
    assert res["target_fire_age"] == 45
    assert res["years_to_target_fire"] == 15.0
    assert res["nominal_fire_target"] > res["real_fire_target"]
    assert res["projected_corpus_at_target_age"] > 0
    assert res["required_monthly_contribution"] > 0

