"""
tests/test_tax_scenarios.py
Unit tests for what-if tax scenario simulator.
"""
from utils.tax_calculator import DeductionBreakdown, IncomeBreakdown
from utils.tax_scenario_calculator import (
    PRESET_TAX_SAVING_MOVES,
    ProposedTaxMove,
    simulate_tax_scenario,
)


def test_simulate_tax_scenario_elss_and_nps():
    # Salaried ₹12,00,000, currently 80C is ₹50,000
    income = IncomeBreakdown(salary_gross=1200000.0)
    deductions = DeductionBreakdown(sec_80c=50000.0)

    # Propose additional 50,000 in ELSS (80C) and 50,000 in NPS (80CCD_1B)
    moves = [
        ProposedTaxMove(
            category="80C",
            description="Invest ₹50k in ELSS",
            proposed_amount=50000.0,
            lock_in_years=3,
            lock_in_note="3-year lock-in",
        ),
        ProposedTaxMove(
            category="80CCD_1B",
            description="Contribute ₹50k to NPS",
            proposed_amount=50000.0,
            lock_in_years=None,
            lock_in_note="Locked till age 60",
        ),
    ]

    res = simulate_tax_scenario(
        scenario_name="Test Maximize Deductions",
        baseline_income=income,
        baseline_deductions=deductions,
        proposed_moves=moves,
        financial_year="2024-25",
        monthly_surplus=30000.0,
        emergency_fund_months=6.0,
    )

    assert res.total_proposed_outflow == 100000.0
    assert res.old_regime_tax_saved > 0
    assert len(res.lock_in_warnings) == 2
    assert res.affordability_warning is None


def test_simulate_tax_scenario_deficit_warning():
    income = IncomeBreakdown(salary_gross=800000.0)
    deductions = DeductionBreakdown()

    moves = [PRESET_TAX_SAVING_MOVES["ELSS_MAX"]]

    res = simulate_tax_scenario(
        scenario_name="Deficit Check",
        baseline_income=income,
        baseline_deductions=deductions,
        proposed_moves=moves,
        financial_year="2024-25",
        monthly_surplus=-5000.0,  # Deficit
        emergency_fund_months=1.0,
    )

    assert res.affordability_warning is not None
    assert "deficit" in res.affordability_warning.lower()


def test_preset_tax_saving_moves():
    assert "ELSS_MAX" in PRESET_TAX_SAVING_MOVES
    assert "PPF_MAX" in PRESET_TAX_SAVING_MOVES
    assert "NPS_80CCD_1B" in PRESET_TAX_SAVING_MOVES
    assert "EMPLOYER_NPS_80CCD_2" in PRESET_TAX_SAVING_MOVES
