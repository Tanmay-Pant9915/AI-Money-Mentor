"""
tests/test_retirement_planning_service.py
Integration tests for the Retirement & FIRE planning service layer:
- Profile and budget surplus reuse
- Input validation and deterministic evaluation
- SQLite persistence of retirement plans and history preservation
- Scenario analysis isolation (unsaved changes do not alter profile or saved plans)
"""
import os
import tempfile
import pytest

from services.profile_service import get_profile, save_profile
from services.retirement_planning_service import (
    delete_saved_plan,
    evaluate_retirement_and_fire_plan,
    get_latest_saved_plan,
    get_saved_plans_history,
    get_user_retirement_context,
    save_retirement_plan,
)


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_get_user_retirement_context_reuse(temp_db):
    user_id = "test_user_ret_ctx"
    # Seed financial profile
    profile_data = {
        "name": "Siddharth Sharma",
        "age": 32,
        "employment_status": "Salaried Employee",
        "monthly_income": 120000.0,
        "essential_expenses": 45000.0,
        "discretionary_expenses": 20000.0,
        "other_expenses": 5000.0,
        "savings_liquid": 200000.0,
        "outstanding_debt": 0.0,
        "monthly_debt_repayment": 0.0,
        "existing_investments": 800000.0,
        "dependents": 1,
    }
    save_profile(profile_data, user_id=user_id, db_path=temp_db)

    ctx = get_user_retirement_context(user_id=user_id, db_path=temp_db)
    assert ctx["has_profile"] is True
    assert ctx["current_age"] == 32
    assert ctx["current_corpus"] == 1000000.0  # 800k investments + 200k liquid
    assert ctx["available_monthly_surplus"] == 50000.0  # 120k - 70k
    assert ctx["monthly_expenses_today"] > 0


def test_evaluate_retirement_and_fire_plan_validation():
    # Target retirement age <= current age
    bad_inputs = {
        "current_age": 40,
        "target_retirement_age": 35,
        "planning_age": 85,
        "monthly_expenses_today": 50000.0,
    }
    res = evaluate_retirement_and_fire_plan(bad_inputs)
    assert res["is_valid"] is False
    assert len(res["errors"]) >= 1


def test_evaluate_retirement_and_fire_plan_execution(temp_db):
    user_id = "test_user_plan_exec"
    inputs = {
        "current_age": 30,
        "target_retirement_age": 60,
        "planning_age": 85,
        "monthly_expenses_today": 50000.0,
        "current_corpus": 500000.0,
        "monthly_contribution": 25000.0,
        "annual_inflation_rate": 6.0,
        "pre_retirement_return": 10.0,
        "post_retirement_return": 7.0,
        "safe_withdrawal_rate": 4.0,
        "monthly_pension": 0.0,
        "available_monthly_surplus": 35000.0,
    }
    plan = evaluate_retirement_and_fire_plan(inputs, user_id=user_id, db_path=temp_db)
    assert plan["is_valid"] is True
    assert plan["target_corpus"] > 0
    assert plan["projected_corpus"] > 0
    assert plan["required_monthly_contribution"] > 0
    assert "fire_timeline" in plan
    assert "alerts" in plan


def test_save_and_retrieve_latest_plan(temp_db):
    user_id = "test_user_save"
    inputs = {
        "plan_name": "My Master Retirement Plan",
        "current_age": 28,
        "target_retirement_age": 58,
        "planning_age": 85,
        "monthly_expenses_today": 40000.0,
        "current_corpus": 300000.0,
        "monthly_contribution": 20000.0,
        "annual_inflation_rate": 6.0,
        "pre_retirement_return": 10.0,
        "post_retirement_return": 7.0,
        "safe_withdrawal_rate": 4.0,
    }
    evaluated = evaluate_retirement_and_fire_plan(inputs, user_id=user_id, db_path=temp_db)
    success, new_id, errors = save_retirement_plan(evaluated, user_id=user_id, db_path=temp_db)

    assert success is True
    assert new_id is not None
    assert errors == []

    # Retrieve latest plan
    latest = get_latest_saved_plan(user_id=user_id, db_path=temp_db)
    assert latest is not None
    assert latest["plan_name"] == "My Master Retirement Plan"
    assert latest["current_age"] == 28
    assert latest["target_retirement_age"] == 58
    assert latest["target_corpus"] == evaluated["target_corpus"]
    assert latest["is_latest"] == 1


def test_plan_history_preservation(temp_db):
    user_id = "test_user_history"

    # Plan 1
    inputs1 = {
        "plan_name": "Conservative 60",
        "current_age": 30,
        "target_retirement_age": 60,
        "planning_age": 85,
        "monthly_expenses_today": 40000.0,
    }
    p1 = evaluate_retirement_and_fire_plan(inputs1, user_id=user_id, db_path=temp_db)
    save_retirement_plan(p1, user_id=user_id, db_path=temp_db)

    # Plan 2 (Alternative scenario)
    inputs2 = {
        "plan_name": "Early FIRE 50",
        "current_age": 30,
        "target_retirement_age": 50,
        "planning_age": 85,
        "monthly_expenses_today": 45000.0,
    }
    p2 = evaluate_retirement_and_fire_plan(inputs2, user_id=user_id, db_path=temp_db)
    save_retirement_plan(p2, user_id=user_id, db_path=temp_db)

    history = get_saved_plans_history(user_id=user_id, db_path=temp_db)
    assert len(history) == 2
    # Newest is latest
    assert history[0]["plan_name"] == "Early FIRE 50"
    assert history[0]["is_latest"] == 1
    assert history[1]["plan_name"] == "Conservative 60"
    assert history[1]["is_latest"] == 0

    # Delete Plan 2
    deleted = delete_saved_plan(history[0]["id"], user_id=user_id, db_path=temp_db)
    assert deleted is True
    updated_history = get_saved_plans_history(user_id=user_id, db_path=temp_db)
    assert len(updated_history) == 1


def test_scenario_changes_do_not_mutate_saved_profile(temp_db):
    user_id = "test_user_isolation"
    profile_data = {
        "name": "Ananya Sen",
        "age": 29,
        "employment_status": "Salaried Employee",
        "monthly_income": 90000.0,
        "essential_expenses": 35000.0,
        "discretionary_expenses": 15000.0,
        "other_expenses": 0.0,
        "savings_liquid": 100000.0,
        "outstanding_debt": 0.0,
        "monthly_debt_repayment": 0.0,
        "existing_investments": 400000.0,
        "dependents": 0,
    }
    save_profile(profile_data, user_id=user_id, db_path=temp_db)

    # User experiments with aggressive hypothetical scenario
    hypothetical_inputs = {
        "current_age": 29,
        "target_retirement_age": 45,  # extreme FIRE
        "planning_age": 85,
        "monthly_expenses_today": 80000.0,  # hypothetical jump
        "current_corpus": 2000000.0,
        "monthly_contribution": 60000.0,
    }
    _ = evaluate_retirement_and_fire_plan(hypothetical_inputs, user_id=user_id, db_path=temp_db)

    # Saved profile must remain unchanged
    profile = get_profile(user_id=user_id, db_path=temp_db)
    assert profile["age"] == 29
    assert profile["essential_expenses"] == 35000.0
    assert profile["existing_investments"] == 400000.0


def test_low_expense_evaluation(temp_db):
    user_id = "test_user_low_exp"
    inputs = {
        "current_age": 25,
        "target_retirement_age": 55,
        "planning_age": 85,
        "monthly_expenses_today": 2800.0,
        "current_corpus": 50000.0,
        "monthly_contribution": 5000.0,
        "annual_inflation_rate": 6.0,
        "pre_retirement_return": 10.0,
        "post_retirement_return": 7.0,
        "safe_withdrawal_rate": 4.0,
        "target_fire_age": 45,
    }
    plan = evaluate_retirement_and_fire_plan(inputs, user_id=user_id, db_path=temp_db)
    assert plan["is_valid"] is True
    assert plan["monthly_expenses_today"] == 2800.0
    assert plan["target_corpus"] > 0
    assert plan["target_fire_analysis"]["nominal_fire_target"] > 0

