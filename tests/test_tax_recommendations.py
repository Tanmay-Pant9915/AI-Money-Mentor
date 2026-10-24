"""
tests/test_tax_recommendations.py
Unit tests for deterministic tax-planning recommendations engine.
"""
from utils.tax_calculator import (
    DeductionBreakdown,
    IncomeBreakdown,
    compare_tax_regimes,
)
from utils.tax_recommendations import generate_tax_recommendations


def test_recommendation_regime_choice():
    income = IncomeBreakdown(salary_gross=1200000.0)
    deductions = DeductionBreakdown(sec_80c=50000.0)
    comp = compare_tax_regimes(income, deductions, "2024-25")

    recs = generate_tax_recommendations(
        comparison=comp,
        income=income,
        deductions=deductions,
        taxes_paid=0.0,
        emergency_months=6.0,
        monthly_surplus=25000.0,
    )

    assert len(recs) > 0
    # Top recommendation should be Regime selection (CRITICAL)
    assert recs[0].priority == "CRITICAL"
    assert recs[0].category == "REGIME"
    assert "New Tax Regime" in recs[0].title


def test_recommendation_advance_tax_warning():
    income = IncomeBreakdown(salary_gross=1500000.0)
    deductions = DeductionBreakdown()
    comp = compare_tax_regimes(income, deductions, "2024-25")

    # TDS is 0, so remaining tax is > 10,000
    recs = generate_tax_recommendations(
        comparison=comp,
        income=income,
        deductions=deductions,
        taxes_paid=0.0,
        emergency_months=6.0,
        monthly_surplus=20000.0,
    )

    adv_tax_recs = [r for r in recs if r.category == "ADVANCE_TAX"]
    assert len(adv_tax_recs) == 1
    assert adv_tax_recs[0].priority == "HIGH"
    assert "Advance Tax" in adv_tax_recs[0].title


def test_recommendation_deficit_warning():
    income = IncomeBreakdown(salary_gross=800000.0)
    deductions = DeductionBreakdown()
    comp = compare_tax_regimes(income, deductions, "2024-25")

    recs = generate_tax_recommendations(
        comparison=comp,
        income=income,
        deductions=deductions,
        taxes_paid=20000.0,
        emergency_months=1.5,
        monthly_surplus=-5000.0,  # Cash-flow deficit
    )

    liquidity_recs = [r for r in recs if r.category == "LIQUIDITY"]
    assert len(liquidity_recs) >= 1
    assert "Deficit" in liquidity_recs[0].title or "Liquid" in liquidity_recs[0].title
