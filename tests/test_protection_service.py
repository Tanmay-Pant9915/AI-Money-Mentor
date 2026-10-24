"""
tests/test_protection_service.py
Integration tests for Emergency Fund and Insurance Planning service layers:
- Profile context reuse and budget surplus integration
- Emergency fund evaluation and SQLite persistence
- Insurance assessment evaluation and SQLite persistence
- History preservation and plan deletion
- Profile isolation (scenario adjustments do not mutate saved profile)
"""
import os
import tempfile
import pytest

from services.emergency_fund_service import (
    delete_emergency_fund_plan,
    evaluate_emergency_fund_plan,
    get_emergency_fund_history,
    get_latest_emergency_fund_plan,
    get_user_emergency_fund_context,
    save_emergency_fund_plan,
)
from services.insurance_planning_service import (
    delete_insurance_assessment,
    evaluate_insurance_assessment,
    get_insurance_assessment_history,
    get_latest_insurance_assessment,
    get_user_insurance_context,
    save_insurance_assessment,
)
from services.profile_service import get_profile, save_profile


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_emergency_fund_context_reuse(temp_db):
    user_id = "test_user_ef_ctx"
    profile_data = {
        "name": "Kavita Rao",
        "age": 31,
        "employment_status": "Salaried Employee",
        "monthly_income": 90000.0,
        "essential_expenses": 35000.0,
        "discretionary_expenses": 15000.0,
        "other_expenses": 0.0,
        "savings_liquid": 140000.0,
        "outstanding_debt": 0.0,
        "monthly_debt_repayment": 0.0,
        "existing_investments": 300000.0,
        "dependents": 1,
    }
    save_profile(profile_data, user_id=user_id, db_path=temp_db)

    ctx = get_user_emergency_fund_context(user_id=user_id, db_path=temp_db)
    assert ctx["has_profile"] is True
    assert ctx["essential_expenses"] == 35000.0
    assert ctx["current_liquid_savings"] == 140000.0
    assert ctx["available_monthly_surplus"] == 40000.0  # 90k - 50k
    assert ctx["target_months"] == 6.0


def test_emergency_fund_plan_evaluation_and_saving(temp_db):
    user_id = "test_user_ef_save"
    inputs = {
        "plan_name": "My 6-Month Emergency Fund",
        "essential_expenses": 40000.0,
        "target_months": 6.0,
        "current_liquid_savings": 120000.0,
        "monthly_contribution": 15000.0,
        "available_monthly_surplus": 25000.0,
    }
    evaluated = evaluate_emergency_fund_plan(inputs, user_id=user_id, db_path=temp_db)
    assert evaluated["is_valid"] is True
    assert evaluated["target_amount"] == 240000.0
    assert evaluated["coverage_months"] == 3.0
    assert evaluated["fund_gap"] == 120000.0
    assert evaluated["months_to_target"] == 8

    # Save to SQLite
    succ, new_id, errs = save_emergency_fund_plan(evaluated, user_id=user_id, db_path=temp_db)
    assert succ is True
    assert new_id is not None
    assert errs == []

    # Retrieve latest
    latest = get_latest_emergency_fund_plan(user_id=user_id, db_path=temp_db)
    assert latest is not None
    assert latest["plan_name"] == "My 6-Month Emergency Fund"
    assert latest["target_amount"] == 240000.0
    assert latest["is_latest"] == 1


def test_emergency_fund_history_and_deletion(temp_db):
    user_id = "test_user_ef_hist"
    inputs1 = {"plan_name": "Plan 1", "essential_expenses": 30000.0, "target_months": 3.0, "current_liquid_savings": 50000.0}
    p1 = evaluate_emergency_fund_plan(inputs1, user_id=user_id, db_path=temp_db)
    save_emergency_fund_plan(p1, user_id=user_id, db_path=temp_db)

    inputs2 = {"plan_name": "Plan 2", "essential_expenses": 30000.0, "target_months": 6.0, "current_liquid_savings": 50000.0}
    p2 = evaluate_emergency_fund_plan(inputs2, user_id=user_id, db_path=temp_db)
    save_emergency_fund_plan(p2, user_id=user_id, db_path=temp_db)

    history = get_emergency_fund_history(user_id=user_id, db_path=temp_db)
    assert len(history) == 2
    assert history[0]["plan_name"] == "Plan 2"
    assert history[0]["is_latest"] == 1
    assert history[1]["is_latest"] == 0

    # Delete
    del_succ = delete_emergency_fund_plan(history[0]["id"], user_id=user_id, db_path=temp_db)
    assert del_succ is True
    assert len(get_emergency_fund_history(user_id=user_id, db_path=temp_db)) == 1


def test_insurance_context_and_evaluation(temp_db):
    user_id = "test_user_ins"
    profile_data = {
        "name": "Arjun Verma",
        "age": 34,
        "employment_status": "Salaried Employee",
        "monthly_income": 100000.0,
        "essential_expenses": 40000.0,
        "discretionary_expenses": 20000.0,
        "other_expenses": 0.0,
        "savings_liquid": 200000.0,
        "outstanding_debt": 1500000.0,
        "monthly_debt_repayment": 20000.0,
        "existing_investments": 500000.0,
        "dependents": 2,
    }
    save_profile(profile_data, user_id=user_id, db_path=temp_db)

    ctx = get_user_insurance_context(user_id=user_id, db_path=temp_db)
    assert ctx["annual_income"] == 1200000.0
    assert ctx["dependents"] == 2
    assert ctx["outstanding_debt"] == 1500000.0
    assert ctx["eligible_assets"] == 700000.0

    eval_inputs = {
        "annual_income": ctx["annual_income"],
        "dependents": ctx["dependents"],
        "outstanding_debt": ctx["outstanding_debt"],
        "future_family_obligations": 1000000.0,
        "eligible_assets": ctx["eligible_assets"],
        "health_personal_coverage": 500000.0,
        "health_employer_coverage": 500000.0,
        "health_target_coverage": 1500000.0,
        "life_existing_coverage": 5000000.0,
        "life_income_multiplier_years": 10.0,
        "has_accident_disability_cover": False,
    }
    assessment = evaluate_insurance_assessment(eval_inputs, user_id=user_id, db_path=temp_db)
    assert assessment["is_valid"] is True
    # Health gap: 15 Lakhs target - 10 Lakhs total = 5 Lakhs gap
    assert assessment["health_assessment"]["total_coverage_gap"] == 500000.0
    # Life need: 1.2 Crore income reserve + 15 Lakhs debt + 10 Lakhs obligations = 1.45 Crore
    # Resources: 7 Lakhs assets + 50 Lakhs life cover = 57 Lakhs
    # Gap: 1.45 Crore - 57 Lakhs = 88 Lakhs
    assert assessment["life_assessment"]["gross_protection_need"] == 14500000.0
    assert assessment["life_assessment"]["net_additional_need"] == 8800000.0
    assert assessment["accident_assessment"]["has_accident_cover"] is False

    # Save to SQLite
    succ, new_id, errs = save_insurance_assessment(assessment, user_id=user_id, db_path=temp_db)
    assert succ is True
    assert new_id is not None

    latest = get_latest_insurance_assessment(user_id=user_id, db_path=temp_db)
    assert latest is not None
    assert latest["health_gap"] == 500000.0
    assert latest["life_gap"] == 8800000.0


def test_profile_isolation(temp_db):
    user_id = "test_user_isolation"
    profile_data = {
        "name": "Pooja Hegde",
        "age": 28,
        "employment_status": "Self-Employed",
        "monthly_income": 75000.0,
        "essential_expenses": 30000.0,
        "discretionary_expenses": 15000.0,
        "other_expenses": 0.0,
        "savings_liquid": 90000.0,
        "outstanding_debt": 0.0,
        "monthly_debt_repayment": 0.0,
        "existing_investments": 200000.0,
        "dependents": 0,
    }
    save_profile(profile_data, user_id=user_id, db_path=temp_db)

    # Experiment with hypothetical inputs
    hypothetical_ef = {
        "essential_expenses": 60000.0,
        "target_months": 12.0,
        "current_liquid_savings": 500000.0,
        "monthly_contribution": 30000.0,
    }
    _ = evaluate_emergency_fund_plan(hypothetical_ef, user_id=user_id, db_path=temp_db)

    # Profile must remain unaltered
    profile = get_profile(user_id=user_id, db_path=temp_db)
    assert profile["essential_expenses"] == 30000.0
    assert profile["savings_liquid"] == 90000.0
