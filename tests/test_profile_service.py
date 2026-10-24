"""
tests/test_profile_service.py
Unit and integration tests for financial profile management, validation, and storage.
"""
from datetime import date, timedelta
import os
import tempfile
import pytest

from services.profile_service import (
    calculate_profile_metrics,
    format_inr,
    get_profile,
    save_profile,
    validate_goal_data,
    validate_profile_data,
)


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


SAMPLE_VALID_PROFILE = {
    "name": "Aarav Sharma",
    "age": 30,
    "employment_status": "Salaried Employee",
    "monthly_income": 120000.0,
    "essential_expenses": 45000.0,
    "discretionary_expenses": 20000.0,
    "other_expenses": 5000.0,
    "savings_liquid": 300000.0,
    "outstanding_debt": 500000.0,
    "monthly_debt_repayment": 15000.0,
    "existing_investments": 400000.0,
    "dependents": 2,
}

SAMPLE_GOALS = [
    {
        "name": "Emergency Fund Booster",
        "target_amount": 200000.0,
        "target_date": (date.today() + timedelta(days=365)).strftime("%Y-%m-%d"),
        "current_amount": 50000.0,
    },
    {
        "name": "New Car Downpayment",
        "target_amount": 500000.0,
        "target_date": (date.today() + timedelta(days=730)).strftime("%Y-%m-%d"),
        "current_amount": 100000.0,
    },
]


class TestProfileValidation:

    def test_valid_profile(self):
        is_valid, errors, warnings = validate_profile_data(SAMPLE_VALID_PROFILE)
        assert is_valid is True
        assert len(errors) == 0

    def test_missing_name(self):
        data = {**SAMPLE_VALID_PROFILE, "name": "  "}
        is_valid, errors, _ = validate_profile_data(data)
        assert is_valid is False
        assert any("Name" in e for e in errors)

    def test_invalid_age(self):
        data_young = {**SAMPLE_VALID_PROFILE, "age": 16}
        is_valid, errors, _ = validate_profile_data(data_young)
        assert is_valid is False
        assert any("Age" in e for e in errors)

        data_old = {**SAMPLE_VALID_PROFILE, "age": 130}
        is_valid, errors, _ = validate_profile_data(data_old)
        assert is_valid is False

    def test_negative_financial_values(self):
        data = {
            **SAMPLE_VALID_PROFILE,
            "monthly_income": -5000.0,
            "essential_expenses": -1000.0,
            "savings_liquid": -200.0,
        }
        is_valid, errors, _ = validate_profile_data(data)
        assert is_valid is False
        assert len(errors) >= 3

    def test_invalid_employment_status(self):
        data = {**SAMPLE_VALID_PROFILE, "employment_status": "Astronaut"}
        is_valid, errors, _ = validate_profile_data(data)
        assert is_valid is False
        assert any("Employment status" in e for e in errors)

    def test_expenses_exceeding_income_triggers_warning_not_error(self):
        data = {
            **SAMPLE_VALID_PROFILE,
            "monthly_income": 50000.0,
            "essential_expenses": 40000.0,
            "discretionary_expenses": 20000.0,  # Total 60000 > 50000
        }
        is_valid, errors, warnings = validate_profile_data(data)
        # Must NOT block saving (is_valid is True)
        assert is_valid is True
        assert len(errors) == 0
        assert len(warnings) > 0
        assert any("exceed monthly income" in w for w in warnings)


class TestGoalValidation:

    def test_valid_goal(self):
        goal = {
            "name": "House Downpayment",
            "target_amount": 1500000.0,
            "target_date": (date.today() + timedelta(days=365)).strftime("%Y-%m-%d"),
            "current_amount": 200000.0,
        }
        is_valid, errors = validate_goal_data(goal)
        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_goal_amount(self):
        goal = {
            "name": "Trip",
            "target_amount": -1000.0,
            "target_date": (date.today() + timedelta(days=100)).strftime("%Y-%m-%d"),
        }
        is_valid, errors = validate_goal_data(goal)
        assert is_valid is False
        assert any("Target amount" in e for e in errors)

    def test_past_target_date(self):
        goal = {
            "name": "Past Goal",
            "target_amount": 50000.0,
            "target_date": (date.today() - timedelta(days=10)).strftime("%Y-%m-%d"),
        }
        is_valid, errors = validate_goal_data(goal)
        assert is_valid is False
        assert any("past" in e for e in errors)


class TestFinancialCalculations:

    def test_surplus_and_deficit_calculation(self):
        # Surplus case
        metrics = calculate_profile_metrics(SAMPLE_VALID_PROFILE, SAMPLE_GOALS)
        # Total expenses: 45000 + 20000 + 5000 + 15000 = 85000
        # Income: 120000 -> Surplus = 35000
        assert metrics["total_monthly_expenses"] == 85000.0
        assert metrics["monthly_surplus"] == 35000.0
        assert metrics["is_deficit"] is False
        assert metrics["surplus_label"] == "Monthly Surplus"
        assert metrics["num_goals"] == 2

        # Deficit case
        deficit_data = {
            **SAMPLE_VALID_PROFILE,
            "monthly_income": 70000.0,
            "essential_expenses": 60000.0,
            "discretionary_expenses": 20000.0,
            "other_expenses": 0.0,
            "monthly_debt_repayment": 0.0,
        }
        def_metrics = calculate_profile_metrics(deficit_data)
        assert def_metrics["total_monthly_expenses"] == 80000.0
        assert def_metrics["monthly_surplus"] == -10000.0
        assert def_metrics["is_deficit"] is True
        assert def_metrics["surplus_label"] == "Monthly Deficit"

    def test_format_inr(self):
        assert format_inr(0) == "₹0"
        assert format_inr(500) == "₹500"
        assert format_inr(15000) == "₹15,000"
        assert format_inr(150000) == "₹1,50,000"
        assert format_inr(1500000) == "₹15,00,000"
        assert format_inr(-25000) == "-₹25,000"


class TestProfilePersistence:

    def test_save_and_retrieve_profile(self, temp_db):
        saved = save_profile(SAMPLE_VALID_PROFILE, SAMPLE_GOALS, user_id="user_1", db_path=temp_db)
        assert saved is not None
        assert saved["name"] == "Aarav Sharma"
        assert len(saved["goals"]) == 2

        retrieved = get_profile(user_id="user_1", db_path=temp_db)
        assert retrieved is not None
        assert retrieved["name"] == "Aarav Sharma"
        assert retrieved["age"] == 30
        assert len(retrieved["goals"]) == 2

    def test_profile_update_does_not_duplicate(self, temp_db):
        save_profile(SAMPLE_VALID_PROFILE, SAMPLE_GOALS, user_id="user_1", db_path=temp_db)

        # Update name and income
        updated_data = {
            **SAMPLE_VALID_PROFILE,
            "name": "Aarav S. Updated",
            "monthly_income": 150000.0,
        }
        save_profile(updated_data, SAMPLE_GOALS, user_id="user_1", db_path=temp_db)

        retrieved = get_profile(user_id="user_1", db_path=temp_db)
        assert retrieved["name"] == "Aarav S. Updated"
        assert retrieved["monthly_income"] == 150000.0

    def test_get_nonexistent_profile(self, temp_db):
        assert get_profile(user_id="ghost_user", db_path=temp_db) is None
