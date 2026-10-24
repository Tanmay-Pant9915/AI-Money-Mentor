"""
tests/test_financial_planning_service.py
Integration tests for financial planning service layer, SQLite plan persistence,
historical snapshots, and user scenario customization.
"""
import os
import tempfile
import pytest

from services.financial_planning_service import (
    generate_active_plan,
    get_financial_plan_inputs,
    get_latest_saved_plan,
    get_saved_plan_history,
    save_financial_plan,
)
from services.profile_service import save_profile


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


SAMPLE_PROFILE = {
    "name": "Arjun Sharma",
    "age": 32,
    "employment_status": "Salaried Employee",
    "monthly_income": 120000.0,
    "essential_expenses": 45000.0,
    "discretionary_expenses": 25000.0,
    "other_expenses": 5000.0,
    "savings_liquid": 150000.0,
    "outstanding_debt": 300000.0,
    "monthly_debt_repayment": 15000.0,
    "existing_investments": 400000.0,
    "dependents": 2,
}

SAMPLE_GOALS = [
    {"name": "Home Down Payment", "target_amount": 1000000.0, "current_amount": 200000.0, "target_date": "2028-12-31"},
    {"name": "Child Education", "target_amount": 500000.0, "current_amount": 50000.0, "target_date": "2029-06-30"},
]


class TestFinancialPlanningService:

    def test_generate_active_plan_with_profile(self, temp_db):
        save_profile(SAMPLE_PROFILE, SAMPLE_GOALS, user_id="user_plan", db_path=temp_db)

        plan = generate_active_plan(user_id="user_plan", db_path=temp_db)
        assert plan["has_profile"] is True
        assert plan["summary"]["monthly_income"] == 120000.0
        # 45k + 25k + 5k = 75k living + 15k debt = 90k total outflows
        assert plan["summary"]["total_monthly_outflows"] == 90000.0
        assert plan["summary"]["monthly_surplus"] == 30000.0
        assert "recommended_categories" in plan["budget"]
        assert len(plan["actions"]) > 0

    def test_generate_plan_without_profile_returns_safe_incomplete_state(self, temp_db):
        plan = generate_active_plan(user_id="ghost_user", db_path=temp_db)
        assert plan["has_profile"] is False
        assert "missing" in plan["message"].lower()

    def test_save_financial_plan_and_retrieve_latest(self, temp_db):
        save_profile(SAMPLE_PROFILE, SAMPLE_GOALS, user_id="user_save", db_path=temp_db)
        plan = generate_active_plan(user_id="user_save", db_path=temp_db)

        plan_id = save_financial_plan(
            plan_data=plan,
            user_id="user_save",
            plan_name="Q1 Financial Roadmap",
            ai_explanation="Test AI summary",
            db_path=temp_db,
        )
        assert plan_id is not None
        assert plan_id > 0

        latest = get_latest_saved_plan(user_id="user_save", db_path=temp_db)
        assert latest is not None
        assert latest["id"] == plan_id
        assert latest["plan_name"] == "Q1 Financial Roadmap"
        assert latest["summary"]["monthly_income"] == 120000.0
        assert latest["ai_explanation"] == "Test AI summary"

    def test_save_plan_preserves_historical_snapshots(self, temp_db):
        save_profile(SAMPLE_PROFILE, SAMPLE_GOALS, user_id="user_hist", db_path=temp_db)
        plan_1 = generate_active_plan(user_id="user_hist", db_path=temp_db)
        save_financial_plan(plan_1, user_id="user_hist", plan_name="Plan 1", db_path=temp_db)

        plan_2 = generate_active_plan(user_id="user_hist", db_path=temp_db)
        save_financial_plan(plan_2, user_id="user_hist", plan_name="Plan 2", db_path=temp_db)

        history = get_saved_plan_history(user_id="user_hist", db_path=temp_db)
        assert len(history) == 2
        # Exactly one is latest
        assert sum(1 for h in history if h["is_latest"] == 1) == 1
        assert history[0]["is_latest"] == 1
        assert history[0]["plan_name"] == "Plan 2"

    def test_user_custom_overrides_flow(self, temp_db):
        save_profile(SAMPLE_PROFILE, SAMPLE_GOALS, user_id="user_custom", db_path=temp_db)

        overrides = {
            "Discretionary Living": 15000.0,  # User voluntarily cuts from 25k to 15k
            "Emergency Savings": 10000.0,
        }
        custom_plan = generate_active_plan(
            user_id="user_custom",
            custom_overrides=overrides,
            db_path=temp_db,
        )
        adj_disc = custom_plan["adjusted_categories"]["Discretionary Living"]["adjusted"]
        assert adj_disc == 15000.0

        # Verify underlying profile in SQLite is NOT altered
        inputs = get_financial_plan_inputs(user_id="user_custom", db_path=temp_db)
        assert inputs["profile"]["discretionary_expenses"] == 25000.0

    def test_profile_changes_do_not_rewrite_historical_plan_snapshot(self, temp_db):
        # 1. Save initial profile and generate/save plan
        save_profile(SAMPLE_PROFILE, SAMPLE_GOALS, user_id="user_iso", db_path=temp_db)
        plan_1 = generate_active_plan(user_id="user_iso", db_path=temp_db)
        plan_id = save_financial_plan(plan_1, user_id="user_iso", plan_name="Historical Baseline", db_path=temp_db)

        # 2. Update user profile with higher salary and higher expenses
        modified_profile = dict(SAMPLE_PROFILE)
        modified_profile["monthly_income"] = 200000.0
        modified_profile["essential_expenses"] = 80000.0
        save_profile(modified_profile, SAMPLE_GOALS, user_id="user_iso", db_path=temp_db)

        # 3. Retrieve saved historical plan
        saved = get_latest_saved_plan(user_id="user_iso", db_path=temp_db)
        assert saved["id"] == plan_id
        # Snapshot in historical plan must remain 120,000, NOT silently updated to 200,000!
        assert saved["input_snapshot"]["profile"]["monthly_income"] == 120000.0
        assert saved["summary"]["monthly_income"] == 120000.0

    def test_plan_with_debt_already_in_expenses_avoids_double_counting(self, temp_db):
        profile_debt_in_exp = dict(SAMPLE_PROFILE)
        profile_debt_in_exp["debt_included_in_expenses"] = True
        save_profile(profile_debt_in_exp, SAMPLE_GOALS, user_id="user_debt_in", db_path=temp_db)

        plan = generate_active_plan(user_id="user_debt_in", debt_already_in_expenses=True, db_path=temp_db)
        summary = plan["summary"]
        # Living expenses: 45k + 25k + 5k = 75k (which already includes 15k debt)
        # Total outflows must be 75k, NOT 75k + 15k = 90k
        assert summary["total_monthly_outflows"] == 75000.0
        assert summary["monthly_surplus"] == 45000.0
