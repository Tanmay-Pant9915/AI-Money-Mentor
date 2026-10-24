"""
tests/test_financial_mentor_context.py
Unit tests for AI Financial Mentor context extraction layer across all modules.
"""
import os
import tempfile
import pytest

from services.profile_service import save_profile
from services.financial_mentor_context import (
    extract_budget_context,
    extract_emergency_fund_context,
    extract_goals_context,
    extract_health_score_context,
    extract_insurance_context,
    extract_portfolio_context,
    extract_profile_context,
    extract_retirement_context,
    extract_risk_context,
    extract_tax_context,
    get_focused_context,
)


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


def test_extract_profile_context_empty(temp_db):
    ctx = extract_profile_context(user_id="nonexistent_user", db_path=temp_db)
    assert ctx["status"] == "unavailable"


def test_extract_profile_context_populated(temp_db):
    save_profile(
        {
            "name": "Mentor Test User",
            "age": 30,
            "employment_status": "Salaried Employee",
            "monthly_income": 120000.0,
            "essential_expenses": 50000.0,
            "discretionary_expenses": 30000.0,
            "other_expenses": 0.0,
            "savings_liquid": 300000.0,
            "outstanding_debt": 200000.0,
            "monthly_debt_repayment": 15000.0,
            "existing_investments": 500000.0,
            "dependents": 1,
        },
        goals=[
            {
                "name": "Emergency Cushion",
                "category": "Emergency",
                "target_amount": 300000.0,
                "target_date": "2026-12-31",
                "current_amount": 100000.0,
                "monthly_contribution": 10000.0,
                "priority": "High",
            }
        ],
        user_id="user_mentor_ctx",
        db_path=temp_db,
    )

    ctx = extract_profile_context(user_id="user_mentor_ctx", db_path=temp_db)
    assert ctx["status"] == "available"
    assert ctx["name"] == "Mentor Test User"
    assert "₹1,20,000" in ctx["monthly_income"]
    assert "₹25,000" in ctx["monthly_surplus"]
    assert ctx["is_deficit"] is False
    assert ctx["goals_count"] == 1


def test_extract_portfolio_context():
    # Empty case
    empty_ctx = extract_portfolio_context(None)
    assert empty_ctx["status"] == "unavailable"

    # Populated case
    sample_funds = [
        {"scheme": "HDFC Top 100 Fund", "current_value": 200000.0, "xirr": 0.14, "expense_ratio": 0.95},
        {"scheme": "Parag Parikh Flexi Cap", "current_value": 300000.0, "xirr": 0.18, "expense_ratio": 0.65},
    ]
    p_ctx = extract_portfolio_context(sample_funds)
    assert p_ctx["status"] == "available"
    assert p_ctx["fund_count"] == 2
    assert "₹5,00,000" in p_ctx["total_valuation"]


def test_get_focused_context_routing(temp_db):
    save_profile(
        {
            "name": "Focused User",
            "age": 28,
            "employment_status": "Self-Employed",
            "monthly_income": 80000.0,
            "essential_expenses": 35000.0,
            "discretionary_expenses": 20000.0,
            "other_expenses": 5000.0,
            "savings_liquid": 100000.0,
            "outstanding_debt": 0.0,
            "monthly_debt_repayment": 0.0,
        },
        user_id="user_focused",
        db_path=temp_db,
    )

    ctx_tax = get_focused_context("TAX_PLANNING", user_id="user_focused", db_path=temp_db)
    assert "profile" in ctx_tax
    assert "tax" in ctx_tax
    assert "retirement" not in ctx_tax

    ctx_ef = get_focused_context("EMERGENCY_FUND", user_id="user_focused", db_path=temp_db)
    assert "emergency_fund" in ctx_ef
    assert "goals" not in ctx_ef
