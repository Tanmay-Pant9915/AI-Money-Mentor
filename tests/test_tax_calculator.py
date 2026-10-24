"""
tests/test_tax_calculator.py
Unit tests for deterministic tax calculator, slabs, rebates, marginal relief, and regime comparisons.
"""
import pytest
from utils.tax_calculator import (
    IncomeBreakdown,
    DeductionBreakdown,
    calculate_hra_exemption,
    calculate_regime_tax,
    compare_tax_regimes,
    compute_slab_tax,
    round_to_nearest_ten,
)
from data.tax_rules import get_tax_rules


def test_round_to_nearest_ten():
    assert round_to_nearest_ten(1234.0) == 1230.0
    assert round_to_nearest_ten(1235.0) == 1240.0
    assert round_to_nearest_ten(1238.0) == 1240.0
    assert round_to_nearest_ten(0.0) == 0.0
    assert round_to_nearest_ten(-50.0) == 0.0


def test_calculate_hra_exemption():
    # Metro city: basic = 50,000, actual HRA = 20,000, rent = 25,000
    # 1. actual HRA = 20,000
    # 2. rent - 10% basic = 25,000 - 5,000 = 20,000
    # 3. 50% basic = 25,000
    # Min = 20,000
    res = calculate_hra_exemption(
        actual_hra_received=20000.0,
        basic_salary=50000.0,
        rent_paid=25000.0,
        is_metro_city=True,
    )
    assert res["eligible_exemption"] == 20000.0
    assert res["taxable_hra"] == 0.0

    # Non-metro with lower rent
    # rent = 10,000. rent - 10% basic = 10,000 - 5,000 = 5,000
    res2 = calculate_hra_exemption(
        actual_hra_received=20000.0,
        basic_salary=50000.0,
        rent_paid=10000.0,
        is_metro_city=False,
    )
    assert res2["eligible_exemption"] == 5000.0
    assert res2["taxable_hra"] == 15000.0


def test_new_regime_zero_tax_up_to_7_75_lakhs():
    """
    In FY 2024-25 New Regime, salaried person earning ₹7,75,000 pays ₹0 tax
    due to ₹75,000 standard deduction and Section 87A rebate up to ₹7,00,000.
    """
    rules = get_tax_rules("2024-25")
    income = IncomeBreakdown(salary_gross=775000.0)
    deductions = DeductionBreakdown()

    res = calculate_regime_tax(
        income=income,
        deductions=deductions,
        regime_rules=rules["new_regime"],
        financial_year="2024-25",
    )
    assert res.standard_deduction == 75000.0
    assert res.taxable_income == 700000.0
    assert res.tax_at_slab_rates == 20000.0  # 5% of 4L (3L to 7L)
    assert res.sec_87a_rebate == 20000.0
    assert res.total_tax_liability == 0.0


def test_new_regime_marginal_relief_section_87a():
    """
    Test marginal relief under Section 87A for income slightly above ₹7L in New Regime.
    Taxable income ₹7,10,000:
    Slab tax = 20,000 + 1,000 = 21,000.
    Excess over 7L = 10,000.
    Tax cannot exceed ₹10,000.
    With 4% cess, total tax = ₹10,400.
    """
    rules = get_tax_rules("2024-25")
    # Gross salary 7,85,000 - 75,000 std deduction = 7,10,000 taxable
    income = IncomeBreakdown(salary_gross=785000.0)
    deductions = DeductionBreakdown()

    res = calculate_regime_tax(
        income=income,
        deductions=deductions,
        regime_rules=rules["new_regime"],
        financial_year="2024-25",
    )
    assert res.taxable_income == 710000.0
    assert res.tax_at_slab_rates == 21000.0
    assert res.marginal_relief_87a == 11000.0
    assert res.tax_after_rebate == 10000.0
    assert res.health_education_cess == 400.0
    assert res.total_tax_liability == 10400.0


def test_old_regime_salaried_with_80c_and_80d():
    """
    Gross salary 10,00,000, 80C 1.5L, 80D 25k.
    Std deduction 50k. Total deductions = 2.25L.
    Taxable = 7.75L. Tax = 67,500 + 4% cess = 70,200.
    """
    rules = get_tax_rules("2024-25")
    income = IncomeBreakdown(salary_gross=1000000.0)
    deductions = DeductionBreakdown(
        sec_80c=150000.0,
        sec_80d_self=25000.0,
    )

    res = calculate_regime_tax(
        income=income,
        deductions=deductions,
        regime_rules=rules["old_regime"],
        financial_year="2024-25",
    )
    assert res.standard_deduction == 50000.0
    assert res.total_deductions_exemptions == 225000.0
    assert res.taxable_income == 775000.0
    assert res.tax_at_slab_rates == 67500.0
    assert res.sec_87a_rebate == 0.0
    assert res.total_tax_liability == 70200.0


def test_deduction_capping():
    """
    Verify statutory caps:
    80C entered 2,00,000 -> eligible capped at 1,50,000.
    80CCD(1B) entered 80,000 -> eligible capped at 50,000.
    """
    rules = get_tax_rules("2024-25")
    income = IncomeBreakdown(salary_gross=1500000.0)
    deductions = DeductionBreakdown(
        sec_80c=200000.0,
        sec_80ccd_1b=80000.0,
    )
    res = calculate_regime_tax(
        income=income,
        deductions=deductions,
        regime_rules=rules["old_regime"],
        financial_year="2024-25",
    )
    assert res.deduction_details["80c"]["eligible"] == 150000.0
    assert res.deduction_details["80c"]["disallowed"] == 50000.0
    assert res.deduction_details["80ccd_1b"]["eligible"] == 50000.0
    assert res.deduction_details["80ccd_1b"]["disallowed"] == 30000.0


def test_compare_regimes_recommends_correctly():
    """
    With moderate deductions, New Regime should win on lower slabs.
    With very high deductions (e.g. 80C + 80D + 24b + HRA), Old Regime may win.
    """
    income = IncomeBreakdown(salary_gross=1200000.0)

    # Low deduction case -> New Regime wins
    comp_new = compare_tax_regimes(
        income=income,
        deductions=DeductionBreakdown(sec_80c=50000.0),
        financial_year="2024-25",
    )
    assert comp_new.recommended_regime == "New Regime"
    assert comp_new.new_regime.total_tax_liability < comp_new.old_regime.total_tax_liability

    # High deduction case (80C 1.5L + 80D 50k + 24b 2L + NPS 50k = 4.5L) -> Old Regime wins
    comp_old = compare_tax_regimes(
        income=income,
        deductions=DeductionBreakdown(
            sec_80c=150000.0,
            sec_80d_self=25000.0,
            sec_80d_parents=25000.0,
            sec_24b=200000.0,
            sec_80ccd_1b=50000.0,
        ),
        financial_year="2024-25",
    )
    assert comp_old.recommended_regime == "Old Regime"
    assert comp_old.old_regime.total_tax_liability < comp_old.new_regime.total_tax_liability


def test_taxes_paid_and_refund_calculation():
    rules = get_tax_rules("2024-25")
    income = IncomeBreakdown(salary_gross=1000000.0)
    deductions = DeductionBreakdown()

    # Tax is calculated, user has paid TDS 50,000
    res = calculate_regime_tax(
        income=income,
        deductions=deductions,
        regime_rules=rules["new_regime"],
        financial_year="2024-25",
        taxes_paid=50000.0,
    )
    if res.total_tax_liability > 50000.0:
        assert res.net_tax_payable == res.total_tax_liability - 50000.0
        assert res.potential_refund == 0.0
    else:
        assert res.potential_refund == 50000.0 - res.total_tax_liability
        assert res.net_tax_payable == 0.0
