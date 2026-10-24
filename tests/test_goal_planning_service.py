"""
tests/test_goal_planning_service.py
Automated tests for Goal-Based Investment Planning service layer:
CRUD operations, database persistence across restarts, validation,
and portfolio integration with budget surplus and risk profiles.
"""
import os
import tempfile
import pytest

from services.goal_planning_service import (
    create_goal,
    delete_goal,
    evaluate_goal_planning_overview,
    get_goal_by_id,
    get_user_goals,
    mark_goal_completed,
    update_goal,
)
from services.profile_service import save_profile
from services.risk_profile_service import submit_risk_assessment


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_create_and_get_goal(temp_db):
    user_id = "test_user_1"
    goal_data = {
        "name": "Higher Education",
        "category": "Education",
        "target_amount": 500000.0,
        "target_date": "2028-06-30",
        "current_amount": 50000.0,
        "monthly_contribution": 10000.0,
        "priority": "High",
    }
    success, created, errors = create_goal(goal_data, user_id=user_id, db_path=temp_db)
    assert success is True
    assert errors == []
    assert created is not None
    assert created["name"] == "Higher Education"
    assert created["category"] == "Education"
    assert created["target_amount"] == 500000.0
    assert created["priority"] == "High"
    assert created["is_completed"] == 0

    goals = get_user_goals(user_id=user_id, db_path=temp_db)
    assert len(goals) == 1
    assert goals[0]["id"] == created["id"]


def test_create_goal_validation_errors(temp_db):
    user_id = "test_user_val"
    # Empty name and non-positive target amount
    bad_data = {
        "name": "",
        "target_amount": -1000.0,
        "target_date": "invalid-date",
        "current_amount": -50.0,
    }
    success, created, errors = create_goal(bad_data, user_id=user_id, db_path=temp_db)
    assert success is False
    assert created is None
    assert len(errors) >= 3


def test_update_goal(temp_db):
    user_id = "test_user_update"
    goal_data = {
        "name": "Vehicle Fund",
        "category": "Vehicle",
        "target_amount": 400000.0,
        "target_date": "2027-12-31",
        "current_amount": 100000.0,
        "priority": "Medium",
    }
    _, created, _ = create_goal(goal_data, user_id=user_id, db_path=temp_db)
    g_id = created["id"]

    # Update target amount and current savings
    update_data = {
        "name": "Upgraded Vehicle Fund",
        "category": "Vehicle",
        "target_amount": 600000.0,
        "target_date": "2028-12-31",
        "current_amount": 150000.0,
        "monthly_contribution": 12000.0,
        "priority": "High",
    }
    success, updated, errors = update_goal(g_id, update_data, user_id=user_id, db_path=temp_db)
    assert success is True
    assert updated["target_amount"] == 600000.0
    assert updated["current_amount"] == 150000.0
    assert updated["priority"] == "High"
    assert updated["name"] == "Upgraded Vehicle Fund"


def test_mark_goal_completed(temp_db):
    user_id = "test_user_complete"
    goal_data = {
        "name": "Small Milestone",
        "category": "Other",
        "target_amount": 50000.0,
        "target_date": "2026-10-01",
    }
    _, created, _ = create_goal(goal_data, user_id=user_id, db_path=temp_db)
    g_id = created["id"]

    res = mark_goal_completed(g_id, True, user_id=user_id, db_path=temp_db)
    assert res["is_completed"] == 1

    # Re-open
    res2 = mark_goal_completed(g_id, False, user_id=user_id, db_path=temp_db)
    assert res2["is_completed"] == 0


def test_delete_goal(temp_db):
    user_id = "test_user_del"
    goal_data = {
        "name": "Goal To Delete",
        "category": "Other",
        "target_amount": 20000.0,
        "target_date": "2027-01-01",
    }
    _, created, _ = create_goal(goal_data, user_id=user_id, db_path=temp_db)
    g_id = created["id"]

    # Delete goal
    deleted = delete_goal(g_id, user_id=user_id, db_path=temp_db)
    assert deleted is True

    # Verify gone
    assert get_goal_by_id(g_id, user_id=user_id, db_path=temp_db) is None
    assert len(get_user_goals(user_id=user_id, db_path=temp_db)) == 0


def test_persistence_across_restarts(temp_db):
    user_id = "test_user_restart"
    goal_data = {
        "name": "Retirement Corpus Milestone",
        "category": "Retirement",
        "target_amount": 2500000.0,
        "target_date": "2035-01-01",
        "current_amount": 500000.0,
        "monthly_contribution": 25000.0,
        "priority": "High",
    }
    _, created, _ = create_goal(goal_data, user_id=user_id, db_path=temp_db)

    # Re-fetch from the same database file (simulating application restart)
    loaded = get_goal_by_id(created["id"], user_id=user_id, db_path=temp_db)
    assert loaded is not None
    assert loaded["name"] == "Retirement Corpus Milestone"
    assert loaded["target_amount"] == 2500000.0
    assert loaded["priority"] == "High"


def test_evaluate_goal_planning_overview_integration(temp_db):
    user_id = "test_user_overview"

    # 1. Setup profile with surplus
    profile_data = {
        "name": "Alice Investor",
        "age": 32,
        "employment_status": "Salaried Employee",
        "monthly_income": 100000.0,
        "essential_expenses": 40000.0,
        "discretionary_expenses": 20000.0,
        "other_expenses": 5000.0,
        "savings_liquid": 150000.0,
        "outstanding_debt": 0.0,
        "monthly_debt_repayment": 0.0,
        "existing_investments": 300000.0,
        "dependents": 1,
    }
    save_profile(profile_data, user_id=user_id, db_path=temp_db)

    # 2. Setup risk assessment
    from utils.risk_scoring import RISK_QUESTIONS
    answers = {q["id"]: 3 for q in RISK_QUESTIONS}
    submit_risk_assessment(answers, user_id=user_id, db_path=temp_db)

    # 3. Create goals
    create_goal(
        {
            "name": "Child Education",
            "category": "Education",
            "target_amount": 1000000.0,
            "target_date": "2032-01-01",
            "current_amount": 100000.0,
            "monthly_contribution": 15000.0,
            "priority": "High",
        },
        user_id=user_id,
        db_path=temp_db,
    )

    overview = evaluate_goal_planning_overview(user_id=user_id, db_path=temp_db)

    assert overview["has_surplus_data"] is True
    # Surplus: 100000 - 65000 = 35000
    assert overview["available_monthly_surplus"] == 35000.0
    assert overview["risk_classification"] in ["Conservative", "Moderate", "Aggressive"]

    goals = overview["goals"]
    assert len(goals) == 1
    g = goals[0]
    assert g["name"] == "Child Education"
    assert g["allocated_from_surplus"] > 0
    assert "asset_allocation" in g
    assert "projection" in g
    assert g["projected_future_value"] > 0


def test_scenario_analysis_leaves_saved_goal_untouched(temp_db):
    user_id = "test_user_scenario"
    goal_data = {
        "name": "Dream House",
        "category": "Home purchase",
        "target_amount": 2000000.0,
        "target_date": "2030-01-01",
        "current_amount": 200000.0,
        "monthly_contribution": 20000.0,
        "priority": "High",
    }
    _, created, _ = create_goal(goal_data, user_id=user_id, db_path=temp_db)
    g_id = created["id"]

    # Run scenario calculation (adjusting contribution, horizon, assumed return)
    from utils.investment_projection import project_investment_growth
    scenario_res = project_investment_growth(
        current_savings=created["current_amount"],
        monthly_contribution=35000.0,  # hypothetical adjustment
        remaining_months=48,           # hypothetical adjustment
        assumed_annual_return=12.0,    # hypothetical adjustment
    )
    assert scenario_res["future_value"] > 0.0

    # Ensure saved goal in database remains 100% untouched
    saved_goal = get_goal_by_id(g_id, user_id=user_id, db_path=temp_db)
    assert saved_goal["target_amount"] == 2000000.0
    assert saved_goal["monthly_contribution"] == 20000.0
    assert saved_goal["target_date"] == "2030-01-01"


def test_overview_emergency_and_debt_alerts(temp_db):
    user_id = "test_user_alerts"

    # Profile with low liquid savings and unserviced debt
    profile_data = {
        "name": "Bob Alert",
        "age": 28,
        "employment_status": "Salaried Employee",
        "monthly_income": 80000.0,
        "essential_expenses": 30000.0,
        "discretionary_expenses": 10000.0,
        "other_expenses": 0.0,
        "savings_liquid": 20000.0,  # Less than 3 months of essential (90,000)
        "outstanding_debt": 150000.0,  # Unserviced debt
        "monthly_debt_repayment": 0.0,
        "existing_investments": 0.0,
        "dependents": 0,
    }
    save_profile(profile_data, user_id=user_id, db_path=temp_db)

    create_goal(
        {
            "name": "Vacation Fund",
            "category": "Other",
            "target_amount": 100000.0,
            "target_date": "2027-06-01",
            "current_amount": 5000.0,
            "monthly_contribution": 5000.0,
            "priority": "Medium",
        },
        user_id=user_id,
        db_path=temp_db,
    )

    overview = evaluate_goal_planning_overview(user_id=user_id, db_path=temp_db)
    p_alerts = overview["portfolio_alerts"]

    assert any(a.get("title") == "Emergency Savings Adequacy" for a in p_alerts)
    assert any(a.get("title") == "Unserviced Outstanding Debt" for a in p_alerts)


def test_individual_goal_alerts_integration(temp_db):
    user_id = "test_user_goal_alerts"

    # Goal 1: High priority goal relying on market returns (planned 4000 < req ~5700, but 12% compounding reaches target)
    create_goal(
        {
            "name": "House Downpayment",
            "category": "Home purchase",
            "target_amount": 500000.0,
            "target_date": "2034-01-01",
            "current_amount": 0.0,
            "monthly_contribution": 4000.0,
            "priority": "High",
        },
        user_id=user_id,
        db_path=temp_db,
    )

    # Goal 2: Short horizon (< 3 years) with high assumed return
    create_goal(
        {
            "name": "Used Bike",
            "category": "Vehicle",
            "target_amount": 80000.0,
            "target_date": "2027-01-01",
            "current_amount": 10000.0,
            "monthly_contribution": 1000.0,
            "priority": "Medium",
        },
        user_id=user_id,
        db_path=temp_db,
    )

    overview = evaluate_goal_planning_overview(user_id=user_id, assumed_annual_return=12.0, db_path=temp_db)
    goals = overview["goals"]

    g_house = next(g for g in goals if g["name"] == "House Downpayment")
    g_bike = next(g for g in goals if g["name"] == "Used Bike")

    # House alerts should include Market Reliance
    assert any("Market Reliance" in a.get("title", "") for a in g_house["alerts"])

    # Bike alerts should include Short-Horizon and Projected Shortfall (planned 1000 will fall short of 70k needed)
    assert any("Short-Horizon" in a.get("title", "") for a in g_bike["alerts"])
    assert any("Projected Growth Shortfall" in a.get("title", "") for a in g_bike["alerts"])


