"""
tests/test_investment_projection.py
Automated unit tests for deterministic investment growth projection,
monthly compounding, timing conventions, inflation adjustments, and target contribution calculations.
"""
import pytest

from utils.investment_projection import (
    calculate_required_contribution_for_target,
    project_investment_growth,
)


def test_project_investment_growth_zero_duration():
    res = project_investment_growth(
        current_savings=50000.0,
        monthly_contribution=5000.0,
        remaining_months=0,
        assumed_annual_return=10.0,
    )
    assert res["future_value"] == 50000.0
    assert res["total_principal_invested"] == 50000.0
    assert res["projected_growth"] == 0.0
    assert res["total_contributions_paid"] == 0.0


def test_project_investment_growth_zero_return():
    # 12 months with 10,000 savings and 2,000 monthly contribution at 0% return
    res = project_investment_growth(
        current_savings=10000.0,
        monthly_contribution=2000.0,
        remaining_months=12,
        assumed_annual_return=0.0,
    )
    expected_principal = 10000.0 + (2000.0 * 12)  # 34,000
    assert res["future_value"] == expected_principal
    assert res["total_principal_invested"] == expected_principal
    assert res["projected_growth"] == 0.0
    assert res["baseline_no_return_fv"] == expected_principal


def test_project_investment_growth_positive_return_end_of_period():
    # PMT = 1,000, n = 12, r = 12% p.a. -> monthly r = 0.01
    # FV of ordinary annuity = 1000 * ((1.01^12 - 1) / 0.01) = 12682.503
    res = project_investment_growth(
        current_savings=0.0,
        monthly_contribution=1000.0,
        remaining_months=12,
        assumed_annual_return=12.0,
        contribution_timing="end_of_period",
    )
    assert res["total_principal_invested"] == 12000.0
    assert round(res["future_value"], 2) == 12682.50
    assert round(res["projected_growth"], 2) == 682.50
    assert res["baseline_no_return_fv"] == 12000.0


def test_project_investment_growth_beginning_of_period():
    # Beginning of period (annuity due) = ordinary annuity * (1 + r)
    # 12682.503 * 1.01 = 12809.328
    res = project_investment_growth(
        current_savings=0.0,
        monthly_contribution=1000.0,
        remaining_months=12,
        assumed_annual_return=12.0,
        contribution_timing="beginning_of_period",
    )
    assert round(res["future_value"], 2) == 12809.33
    assert res["future_value"] > 12682.50


def test_project_investment_growth_lump_sum_and_sip():
    # Current savings PV = 10,000 at 12% for 12 months = 10000 * (1.01)^12 = 11268.25
    # Contributions = 12682.50
    # Total FV = 11268.25 + 12682.50 = 23950.75
    res = project_investment_growth(
        current_savings=10000.0,
        monthly_contribution=1000.0,
        remaining_months=12,
        assumed_annual_return=12.0,
        contribution_timing="end_of_period",
    )
    assert round(res["fv_current_savings"], 2) == 11268.25
    assert round(res["fv_contributions"], 2) == 12682.50
    assert round(res["future_value"], 2) == 23950.75
    assert res["total_principal_invested"] == 22000.0
    assert round(res["projected_growth"], 2) == 1950.75


def test_project_investment_growth_negative_return():
    # Safely handles bear market / drawdown assumptions (-6% p.a.)
    res = project_investment_growth(
        current_savings=50000.0,
        monthly_contribution=5000.0,
        remaining_months=24,
        assumed_annual_return=-6.0,
    )
    assert res["future_value"] < res["total_principal_invested"]
    assert res["projected_growth"] < 0.0


def test_project_investment_growth_inflation_deflation():
    # Inflation deflates nominal FV to real purchasing power
    res = project_investment_growth(
        current_savings=100000.0,
        monthly_contribution=10000.0,
        remaining_months=36,
        assumed_annual_return=10.0,
        annual_inflation_rate=6.0,
    )
    assert res["real_purchasing_power"] < res["future_value"]
    assert res["real_purchasing_power"] > 0.0


def test_calculate_required_contribution_for_target():
    # Target: 5,00,000 in 36 months with 50,000 initial savings and 10% return
    calc = calculate_required_contribution_for_target(
        target_amount=500000.0,
        current_savings=50000.0,
        remaining_months=36,
        assumed_annual_return=10.0,
        contribution_timing="end_of_period",
    )
    req_pmt = calc["required_monthly_contribution"]
    assert req_pmt > 0.0

    # Verify that investing req_pmt reaches ~5,00,000
    verify_proj = project_investment_growth(
        current_savings=50000.0,
        monthly_contribution=req_pmt,
        remaining_months=36,
        assumed_annual_return=10.0,
        contribution_timing="end_of_period",
    )
    assert abs(verify_proj["future_value"] - 500000.0) < 50.0  # within rounding tolerance


def test_project_investment_growth_invalid_inputs():
    # Negative contributions and savings should be safely clamped to 0.0
    res = project_investment_growth(
        current_savings=-10000.0,
        monthly_contribution=-500.0,
        remaining_months=12,
        assumed_annual_return=10.0,
    )
    assert res["future_value"] == 0.0
    assert res["total_principal_invested"] == 0.0

    calc = calculate_required_contribution_for_target(
        target_amount=-50000.0,
        current_savings=10000.0,
        remaining_months=12,
    )
    assert calc["required_monthly_contribution"] == 0.0

