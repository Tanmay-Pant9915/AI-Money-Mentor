"""
tests/test_tax_planning_service.py
Integration tests for tax planning service, context loading, persistence, and scenarios.
"""
import os
import tempfile
import pytest

from services.profile_service import save_profile
from services.tax_planning_service import (
    delete_tax_scenario,
    get_latest_tax_assessment,
    get_saved_tax_scenarios,
    get_tax_profile,
    get_user_tax_context,
    save_tax_assessment,
    save_tax_profile,
    save_tax_scenario,
)
from utils.tax_calculator import (
    DeductionBreakdown,
    IncomeBreakdown,
    compare_tax_regimes,
)
from utils.tax_recommendations import generate_tax_recommendations
from utils.tax_scenario_calculator import ProposedTaxMove, simulate_tax_scenario


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


def test_tax_context_integration(temp_db):
    save_profile(
        {
            "name": "Tax Test User",
            "age": 32,
            "employment_status": "Salaried Employee",
            "monthly_income": 100000.0,
            "essential_expenses": 40000.0,
            "discretionary_expenses": 20000.0,
            "other_expenses": 5000.0,
            "savings_liquid": 240000.0,
            "outstanding_debt": 0.0,
            "monthly_debt_repayment": 0.0,
        },
        user_id="user_tax_ctx",
        db_path=temp_db,
    )

    ctx = get_user_tax_context(user_id="user_tax_ctx", db_path=temp_db)
    assert ctx["has_profile"] is True
    assert ctx["age"] == 32
    assert ctx["annual_salary"] == 1200000.0
    assert ctx["monthly_surplus"] == 35000.0
    assert ctx["emergency_runway_months"] == 6.0  # 240k / 40k = 6


def test_save_and_get_tax_profile(temp_db):
    income = IncomeBreakdown(salary_gross=1500000.0, other_sources_interest=25000.0)
    deductions = DeductionBreakdown(sec_80c=150000.0, sec_80d_self=25000.0)

    save_tax_profile(
        user_id="user_prof_test",
        financial_year="2024-25",
        age=35,
        income=income,
        deductions=deductions,
        taxes_paid=75000.0,
        db_path=temp_db,
    )

    prof = get_tax_profile(user_id="user_prof_test", financial_year="2024-25", db_path=temp_db)
    assert prof is not None
    assert prof["salary_gross"] == 1500000.0
    assert prof["other_sources_interest"] == 25000.0
    assert prof["taxes_paid"] == 75000.0
    assert prof["deductions"]["sec_80c"] == 150000.0


def test_save_and_retrieve_assessment(temp_db):
    income = IncomeBreakdown(salary_gross=1200000.0)
    deductions = DeductionBreakdown(sec_80c=100000.0)
    comp = compare_tax_regimes(income, deductions, "2024-25")
    recs = generate_tax_recommendations(comp, income, deductions)

    plan_id = save_tax_assessment("user_assess_test", comp, recs, db_path=temp_db)
    assert plan_id > 0

    latest = get_latest_tax_assessment("user_assess_test", "2024-25", db_path=temp_db)
    assert latest is not None
    assert latest["recommended_regime"] == comp.recommended_regime
    assert "old_regime" in latest["details"]
    assert "new_regime" in latest["details"]


def test_save_and_delete_tax_scenario(temp_db):
    income = IncomeBreakdown(salary_gross=1000000.0)
    deductions = DeductionBreakdown()
    move = ProposedTaxMove(category="80C", description="ELSS ₹50k", proposed_amount=50000.0)
    sim = simulate_tax_scenario("Save Test Scenario", income, deductions, [move], "2024-25")

    scen_id = save_tax_scenario("user_scen_test", sim, db_path=temp_db)
    assert scen_id > 0

    scenarios = get_saved_tax_scenarios("user_scen_test", "2024-25", db_path=temp_db)
    assert len(scenarios) == 1
    assert scenarios[0]["scenario_name"] == "Save Test Scenario"

    delete_tax_scenario(scen_id, "user_scen_test", db_path=temp_db)
    scenarios_after = get_saved_tax_scenarios("user_scen_test", "2024-25", db_path=temp_db)
    assert len(scenarios_after) == 0
