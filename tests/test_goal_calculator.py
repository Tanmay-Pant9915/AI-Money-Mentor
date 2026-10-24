"""
tests/test_goal_calculator.py
Automated unit tests for deterministic goal feasibility, remaining time,
required monthly contributions, and portfolio-level surplus allocation.
"""
from datetime import date, timedelta
import pytest

from utils.goal_calculator import (
    evaluate_goal_feasibility,
    evaluate_goals_portfolio,
    parse_goal_target_date,
)


def test_parse_goal_target_date_future():
    today = date(2026, 1, 15)
    # Target date 24 months later
    is_valid, months, is_expired = parse_goal_target_date("2028-01-15", current_date=today)
    assert is_valid is True
    assert months == 24
    assert is_expired is False


def test_parse_goal_target_date_expired():
    today = date(2026, 5, 15)
    is_valid, months, is_expired = parse_goal_target_date("2025-12-01", current_date=today)
    assert is_valid is True
    assert months == 0
    assert is_expired is True


def test_parse_goal_target_date_invalid():
    is_valid, months, is_expired = parse_goal_target_date("invalid-date")
    assert is_valid is False
    assert months == 0
    assert is_expired is False

    is_valid, months, is_expired = parse_goal_target_date("")
    assert is_valid is False


def test_evaluate_goal_feasibility_no_savings():
    today = date(2026, 1, 1)
    goal = {
        "name": "Emergency Cushion",
        "category": "Emergency savings",
        "target_amount": 120000.0,
        "current_amount": 0.0,
        "target_date": "2027-01-01",  # 12 months away
        "priority": "High",
    }
    res = evaluate_goal_feasibility(goal, available_surplus=20000.0, current_date=today)
    assert res["target_amount"] == 120000.0
    assert res["current_amount"] == 0.0
    assert res["remaining_amount"] == 120000.0
    assert res["remaining_months"] == 12
    assert res["required_monthly"] == 10000.0
    assert res["is_completed"] is False
    assert res["affordability"] == "Affordable"
    assert res["required_monthly"] <= 20000.0


def test_evaluate_goal_feasibility_existing_savings():
    today = date(2026, 1, 1)
    goal = {
        "name": "New Car",
        "category": "Vehicle",
        "target_amount": 500000.0,
        "current_amount": 200000.0,
        "target_date": "2028-07-01",  # 30 months away
        "priority": "Medium",
    }
    res = evaluate_goal_feasibility(goal, current_date=today)
    assert res["remaining_amount"] == 300000.0
    assert res["remaining_months"] == 30
    assert res["required_monthly"] == 10000.0
    assert res["is_completed"] is False


def test_evaluate_goal_feasibility_already_completed():
    goal = {
        "name": "Laptop",
        "category": "Other",
        "target_amount": 80000.0,
        "current_amount": 85000.0,
        "target_date": "2026-12-31",
    }
    res = evaluate_goal_feasibility(goal)
    assert res["is_completed"] is True
    assert res["remaining_amount"] == 0.0
    assert res["required_monthly"] == 0.0
    assert res["status"] == "Completed"


def test_evaluate_goal_feasibility_zero_remaining_months():
    today = date(2026, 6, 1)
    goal = {
        "name": "Due Today",
        "target_amount": 50000.0,
        "current_amount": 10000.0,
        "target_date": "2026-06-25",
    }
    res = evaluate_goal_feasibility(goal, current_date=today)
    assert res["remaining_months"] == 0
    assert res["is_expired"] is False
    assert res["required_monthly"] == 40000.0
    assert res["status"] == "Due Immediately"


def test_evaluate_goal_feasibility_expired_incomplete():
    today = date(2026, 6, 1)
    goal = {
        "name": "Past Goal",
        "target_amount": 100000.0,
        "current_amount": 20000.0,
        "target_date": "2025-10-01",
    }
    res = evaluate_goal_feasibility(goal, current_date=today)
    assert res["is_expired"] is True
    assert res["status"] == "Target Date Passed"
    assert res["required_monthly"] == 0.0
    assert any("passed" in a["message"].lower() for a in res["alerts"])


def test_evaluate_goal_feasibility_negative_or_zero_target():
    goal = {
        "name": "Zero Goal",
        "target_amount": 0.0,
        "target_date": "2027-01-01",
    }
    res = evaluate_goal_feasibility(goal)
    assert res["required_monthly"] == 0.0
    assert res["status"] == "Invalid Target Amount"


def test_evaluate_goals_portfolio_surplus_allocation():
    today = date(2026, 1, 1)
    goals = [
        {
            "id": 1,
            "name": "Emergency Fund",
            "priority": "High",
            "target_amount": 120000.0,
            "current_amount": 0.0,
            "target_date": "2027-01-01",  # Req: 10,000/mo
        },
        {
            "id": 2,
            "name": "Vacation",
            "priority": "Low",
            "target_amount": 60000.0,
            "current_amount": 0.0,
            "target_date": "2027-01-01",  # Req: 5,000/mo
        },
    ]

    # Surplus is 12,000/mo (High gets 10,000, Low gets 2,000 -> shortfall of 3,000)
    res = evaluate_goals_portfolio(goals, available_surplus=12000.0, current_date=today)
    summary = res["summary"]
    assert summary["total_required_monthly"] == 15000.0
    assert summary["affordable_goals_count"] == 1
    assert summary["shortfall_goals_count"] == 1
    assert summary["affordability_status"] == "Partially Affordable"

    g1 = next(g for g in res["evaluated_goals"] if g["id"] == 1)
    g2 = next(g for g in res["evaluated_goals"] if g["id"] == 2)
    assert g1["allocated_from_surplus"] == 10000.0
    assert g1["affordability"] == "Affordable"
    assert g2["allocated_from_surplus"] == 2000.0
    assert g2["affordability"] == "Partially Funded"


def test_evaluate_goals_portfolio_deficit_handling():
    goals = [
        {
            "name": "Goal A",
            "priority": "Medium",
            "target_amount": 50000.0,
            "target_date": "2027-01-01",
        }
    ]
    # Negative surplus (deficit)
    res = evaluate_goals_portfolio(goals, available_surplus=-5000.0)
    summary = res["summary"]
    assert summary["affordability_status"] == "Cash Flow Deficit"
    assert summary["affordable_goals_count"] == 0
    assert any("deficit" in a["message"].lower() for a in res["portfolio_alerts"])


def test_evaluate_goals_portfolio_unknown_surplus():
    goals = [
        {
            "name": "Goal A",
            "target_amount": 100000.0,
            "target_date": "2027-01-01",
        }
    ]
    res = evaluate_goals_portfolio(goals, available_surplus=None)
    summary = res["summary"]
    assert summary["affordability_status"] == "Surplus Unknown"
    assert any("unknown" in a["message"].lower() for a in res["portfolio_alerts"])


def test_evaluate_goal_feasibility_zero_surplus():
    today = date(2026, 1, 1)
    goal = {
        "name": "Goal Zero Surplus",
        "target_amount": 120000.0,
        "target_date": "2027-01-01",  # Req: 10,000/mo
    }
    # Exactly 0 surplus
    res = evaluate_goal_feasibility(goal, available_surplus=0.0, current_date=today)
    assert res["is_affordable"] is False
    assert res["affordability"] == "Cash Flow Deficit"
    assert res["surplus_shortfall"] == 10000.0
    assert res["coverage_pct"] == 0.0


def test_evaluate_goal_feasibility_partial_surplus():
    today = date(2026, 1, 1)
    goal = {
        "name": "Goal Partial Surplus",
        "target_amount": 120000.0,
        "target_date": "2027-01-01",  # Req: 10,000/mo
    }
    # Available surplus is 4,000/mo (< 10,000)
    res = evaluate_goal_feasibility(goal, available_surplus=4000.0, current_date=today)
    assert res["is_affordable"] is False
    assert res["affordability"] == "Shortfall"
    assert res["surplus_shortfall"] == 6000.0
    assert res["coverage_pct"] == 40.0

