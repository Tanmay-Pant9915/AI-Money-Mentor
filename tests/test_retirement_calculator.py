"""
tests/test_retirement_calculator.py
Unit tests for deterministic retirement calculations:
- Inflation-adjusted retirement expenses
- Retirement corpus estimation (simplified SWR and detailed growing annuity)
- Pension income adjustments (nominal and inflation-linked)
- Accumulation modeling with effective monthly compounding
- Required monthly contribution calculations
"""
import pytest

from utils.retirement_calculator import (
    calculate_inflation_adjusted_expenses,
    calculate_monthly_effective_rate,
    calculate_required_monthly_contribution,
    calculate_retirement_accumulation,
    calculate_retirement_corpus,
)


# ==============================================================================
# 1. Inflation Calculations Tests
# ==============================================================================

def test_inflation_expenses_zero_inflation():
    res = calculate_inflation_adjusted_expenses(
        monthly_expenses_today=50000.0,
        annual_inflation_rate=0.0,
        years_until_retirement=20.0,
    )
    assert res["monthly_expenses_today"] == 50000.0
    assert res["monthly_expenses_at_retirement"] == 50000.0
    assert res["annual_expenses_at_retirement"] == 600000.0
    assert res["inflation_multiplier"] == 1.0


def test_inflation_expenses_positive_inflation():
    # 50,000 at 6% for 10 years: 50000 * (1.06^10) = 50000 * 1.7908477 = 89542.39
    res = calculate_inflation_adjusted_expenses(
        monthly_expenses_today=50000.0,
        annual_inflation_rate=6.0,
        years_until_retirement=10.0,
    )
    assert abs(res["monthly_expenses_at_retirement"] - 89542.38) < 0.05
    assert abs(res["annual_expenses_at_retirement"] - (89542.38 * 12.0)) < 0.5
    assert round(res["inflation_multiplier"], 4) == 1.7908


def test_inflation_expenses_zero_years():
    # 0 years until retirement -> multiplier = 1.0
    res = calculate_inflation_adjusted_expenses(
        monthly_expenses_today=60000.0,
        annual_inflation_rate=7.0,
        years_until_retirement=0.0,
    )
    assert res["monthly_expenses_at_retirement"] == 60000.0
    assert res["inflation_multiplier"] == 1.0


def test_inflation_expenses_already_future_rupees():
    res = calculate_inflation_adjusted_expenses(
        monthly_expenses_today=120000.0,
        annual_inflation_rate=6.0,
        years_until_retirement=15.0,
        is_already_future_rupees=True,
    )
    assert res["monthly_expenses_at_retirement"] == 120000.0
    assert res["inflation_multiplier"] == 1.0


def test_inflation_expenses_invalid_negative_values():
    res = calculate_inflation_adjusted_expenses(
        monthly_expenses_today=-5000.0,
        annual_inflation_rate=-2.0,
        years_until_retirement=-10.0,
    )
    assert res["monthly_expenses_today"] == 0.0
    assert res["monthly_expenses_at_retirement"] == 0.0


# ==============================================================================
# 2. Retirement Corpus Calculations Tests
# ==============================================================================

def test_retirement_corpus_simplified_baseline():
    # Annual expenses 12,00,000, 4% SWR -> 12,00,000 / 0.04 = 3,00,00,000 (3 Crore)
    res = calculate_retirement_corpus(
        annual_expenses_at_retirement=1200000.0,
        retirement_duration_years=25,
        post_retirement_annual_return=7.0,
        annual_inflation_rate=6.0,
        safe_withdrawal_rate=4.0,
    )
    assert res["simplified_corpus"] == 30000000.0
    assert res["detailed_corpus"] > 0.0


def test_retirement_corpus_zero_expenses():
    res = calculate_retirement_corpus(
        annual_expenses_at_retirement=0.0,
        retirement_duration_years=30,
    )
    assert res["simplified_corpus"] == 0.0
    assert res["detailed_corpus"] == 0.0


def test_retirement_corpus_with_pension():
    # Gross expenses 10,00,000, fixed pension 3,00,000 -> net starting withdrawal = 7,00,000
    res_fixed = calculate_retirement_corpus(
        annual_expenses_at_retirement=1000000.0,
        retirement_duration_years=20,
        post_retirement_annual_return=7.0,
        annual_inflation_rate=6.0,
        annual_pension_at_retirement=300000.0,
        is_pension_inflation_indexed=False,
    )
    # Inflation indexed pension
    res_indexed = calculate_retirement_corpus(
        annual_expenses_at_retirement=1000000.0,
        retirement_duration_years=20,
        post_retirement_annual_return=7.0,
        annual_inflation_rate=6.0,
        annual_pension_at_retirement=300000.0,
        is_pension_inflation_indexed=True,
    )
    assert res_fixed["net_annual_withdrawal_year_1"] == 700000.0
    # An indexed pension covers more real expenses over time, so required corpus is lower
    assert res_indexed["detailed_corpus"] < res_fixed["detailed_corpus"]


def test_retirement_corpus_zero_return():
    # 0% post-retirement return with 0% inflation: corpus must equal duration * expenses
    res = calculate_retirement_corpus(
        annual_expenses_at_retirement=500000.0,
        retirement_duration_years=20,
        post_retirement_annual_return=0.0,
        annual_inflation_rate=0.0,
    )
    # 20 years * 500,000 = 1,00,00,000 (1 Crore)
    assert res["detailed_corpus"] == 10000000.0


# ==============================================================================
# 3. Accumulation Calculator Tests
# ==============================================================================

def test_accumulation_zero_duration():
    res = calculate_retirement_accumulation(
        current_corpus=500000.0,
        monthly_contribution=20000.0,
        years_until_retirement=0.0,
        assumed_annual_return=10.0,
    )
    assert res["future_value"] == 500000.0
    assert res["total_principal_invested"] == 500000.0
    assert res["projected_growth"] == 0.0


def test_accumulation_zero_return():
    # 10 years (120 months) with 10,000 monthly SIP and 1,00,000 initial corpus
    res = calculate_retirement_accumulation(
        current_corpus=100000.0,
        monthly_contribution=10000.0,
        years_until_retirement=10.0,
        assumed_annual_return=0.0,
    )
    expected_principal = 100000.0 + (10000.0 * 120)  # 13,00,000
    assert res["future_value"] == expected_principal
    assert res["total_principal_invested"] == expected_principal
    assert res["projected_growth"] == 0.0


def test_accumulation_positive_return_and_timing():
    res_end = calculate_retirement_accumulation(
        current_corpus=0.0,
        monthly_contribution=5000.0,
        years_until_retirement=5.0,
        assumed_annual_return=12.0,
        contribution_timing="end_of_period",
    )
    res_beg = calculate_retirement_accumulation(
        current_corpus=0.0,
        monthly_contribution=5000.0,
        years_until_retirement=5.0,
        assumed_annual_return=12.0,
        contribution_timing="beginning_of_period",
    )
    assert res_end["future_value"] > res_end["total_principal_invested"]
    assert res_beg["future_value"] > res_end["future_value"]
    assert res_end["total_contributions_paid"] == 5000.0 * 60


def test_accumulation_supported_negative_return():
    res = calculate_retirement_accumulation(
        current_corpus=1000000.0,
        monthly_contribution=10000.0,
        years_until_retirement=5.0,
        assumed_annual_return=-5.0,
    )
    assert res["future_value"] < res["total_principal_invested"]
    assert res["projected_growth"] < 0.0


# ==============================================================================
# 4. Required Monthly Contribution Tests
# ==============================================================================

def test_required_monthly_target_exceeded_by_current_corpus():
    # Target 50,00,000, current corpus 60,00,000 -> required monthly 0
    res = calculate_required_monthly_contribution(
        target_corpus=5000000.0,
        current_corpus=6000000.0,
        years_until_retirement=10.0,
        assumed_annual_return=10.0,
    )
    assert res["required_monthly_contribution"] == 0.0
    assert res["target_gap_to_fund"] == 0.0


def test_required_monthly_zero_horizon():
    # Horizon 0 years -> gap is required immediately
    res = calculate_required_monthly_contribution(
        target_corpus=5000000.0,
        current_corpus=2000000.0,
        years_until_retirement=0.0,
        assumed_annual_return=10.0,
    )
    assert res["required_monthly_contribution"] == 3000000.0
    assert res["is_horizon_zero"] is True


def test_required_monthly_accuracy():
    # If we calculate required monthly for target 1 Crore in 20 years at 10%
    calc = calculate_required_monthly_contribution(
        target_corpus=10000000.0,
        current_corpus=500000.0,
        years_until_retirement=20.0,
        assumed_annual_return=10.0,
        contribution_timing="end_of_period",
    )
    req_pmt = calc["required_monthly_contribution"]
    assert req_pmt > 0.0

    # Accumulation at req_pmt must hit ~1 Crore
    verify = calculate_retirement_accumulation(
        current_corpus=500000.0,
        monthly_contribution=req_pmt,
        years_until_retirement=20.0,
        assumed_annual_return=10.0,
        contribution_timing="end_of_period",
    )
    assert abs(verify["future_value"] - 10000000.0) < 500.0  # within 0.005% rounding


def test_inflation_expenses_multiple_horizons():
    # Verify inflation compounding monotonically across 5, 10, 20, 30 years
    horizons = [5.0, 10.0, 20.0, 30.0]
    multipliers = []
    for h in horizons:
        res = calculate_inflation_adjusted_expenses(
            monthly_expenses_today=50000.0,
            annual_inflation_rate=6.0,
            years_until_retirement=h,
        )
        multipliers.append(res["inflation_multiplier"])

    # Multipliers must strictly increase over time
    for i in range(len(multipliers) - 1):
        assert multipliers[i] < multipliers[i + 1]


def test_retirement_corpus_different_durations():
    # Longer retirement duration must require a strictly higher corpus
    durations = [15, 25, 35]
    corpuses = []
    for d in durations:
        res = calculate_retirement_corpus(
            annual_expenses_at_retirement=1000000.0,
            retirement_duration_years=d,
            post_retirement_annual_return=7.0,
            annual_inflation_rate=6.0,
        )
        corpuses.append(res["detailed_corpus"])

    for i in range(len(corpuses) - 1):
        assert corpuses[i] < corpuses[i + 1]


def test_retirement_corpus_negative_return_and_extreme():
    # Negative post-retirement return (-3%) requires higher corpus due to capital erosion
    res_neg = calculate_retirement_corpus(
        annual_expenses_at_retirement=600000.0,
        retirement_duration_years=20,
        post_retirement_annual_return=-3.0,
        annual_inflation_rate=0.0,
    )
    # Zero return benchmark (20 * 600,000 = 1,20,00,000)
    res_zero = calculate_retirement_corpus(
        annual_expenses_at_retirement=600000.0,
        retirement_duration_years=20,
        post_retirement_annual_return=0.0,
        annual_inflation_rate=0.0,
    )
    assert res_neg["detailed_corpus"] > res_zero["detailed_corpus"]


def test_accumulation_zero_contribution():
    # With 0 monthly contribution, corpus grows purely from initial lump sum
    res = calculate_retirement_accumulation(
        current_corpus=1000000.0,
        monthly_contribution=0.0,
        years_until_retirement=10.0,
        assumed_annual_return=10.0,
    )
    assert res["total_contributions_paid"] == 0.0
    assert res["total_principal_invested"] == 1000000.0
    assert res["future_value"] > 1000000.0
    assert res["projected_growth"] == round(res["future_value"] - 1000000.0, 2)


def test_required_monthly_zero_return():
    # Target 60,00,000, current corpus 0, 10 years (120 months) at 0% return
    # Required monthly = 60,00,000 / 120 = 50,000
    res = calculate_required_monthly_contribution(
        target_corpus=6000000.0,
        current_corpus=0.0,
        years_until_retirement=10.0,
        assumed_annual_return=0.0,
    )
    assert res["required_monthly_contribution"] == 50000.0
    assert res["zero_return_required_monthly"] == 50000.0


def test_required_monthly_invalid_negative_inputs():
    # Negative inputs should be normalized safely to 0
    res = calculate_required_monthly_contribution(
        target_corpus=-1000000.0,
        current_corpus=-50000.0,
        years_until_retirement=-5.0,
        assumed_annual_return=10.0,
    )
    assert res["required_monthly_contribution"] == 0.0
    assert res["target_gap_to_fund"] == 0.0

