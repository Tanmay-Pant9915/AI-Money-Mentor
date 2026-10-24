"""
tests/test_money_health_service.py
Integration tests for Money Health Score service, profile retrieval,
recalculation triggers on profile updates, persistence, and history.
"""
import os
import tempfile
import pytest

from services.money_health_service import (
    get_health_score_history,
    get_latest_health_score,
    get_or_calculate_health_score,
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
    "name": "Kavya Patel",
    "age": 28,
    "employment_status": "Salaried Employee",
    "monthly_income": 90000.0,
    "essential_expenses": 35000.0,
    "discretionary_expenses": 15000.0,
    "other_expenses": 5000.0,
    "savings_liquid": 180000.0,
    "outstanding_debt": 200000.0,
    "monthly_debt_repayment": 10000.0,
    "existing_investments": 300000.0,
    "dependents": 1,
}

SAMPLE_GOALS = [
    {"name": "Emergency Fund", "target_amount": 200000.0, "target_date": "2027-12-31", "current_amount": 100000.0}
]


class TestMoneyHealthService:

    def test_calculate_and_persist_health_score(self, temp_db):
        save_profile(SAMPLE_PROFILE, SAMPLE_GOALS, user_id="user_test", db_path=temp_db)

        result = get_or_calculate_health_score(user_id="user_test", db_path=temp_db)
        assert result is not None
        assert result["overall_score"] is not None
        assert result["is_sufficient_data"] is True
        assert result["data_completeness"] == 100.0

        latest = get_latest_health_score(user_id="user_test", db_path=temp_db)
        assert latest is not None
        assert latest["overall_score"] == result["overall_score"]
        assert latest["rating"] == result["rating"]

    def test_recalculation_triggered_on_profile_update(self, temp_db):
        # 1. Initial profile
        save_profile(SAMPLE_PROFILE, SAMPLE_GOALS, user_id="user_update", db_path=temp_db)
        score_1 = get_or_calculate_health_score(user_id="user_update", db_path=temp_db)
        assert score_1["overall_score"] is not None

        # 2. Update profile with significant increase in income & liquid savings
        improved_profile = {
            **SAMPLE_PROFILE,
            "monthly_income": 180000.0,
            "savings_liquid": 600000.0,
            "outstanding_debt": 0.0,
            "monthly_debt_repayment": 0.0,
        }
        save_profile(improved_profile, SAMPLE_GOALS, user_id="user_update", db_path=temp_db)

        # 3. Next call should detect changed profile_updated_at and recalculate
        score_2 = get_or_calculate_health_score(user_id="user_update", db_path=temp_db)
        assert score_2["overall_score"] is not None
        # Improved profile must have higher or equal score
        assert score_2["overall_score"] >= score_1["overall_score"]

        # History should now have 2 records
        history = get_health_score_history(user_id="user_update", db_path=temp_db)
        assert len(history) == 2
        assert history[0]["is_latest"] == 1

    def test_force_recalculate(self, temp_db):
        save_profile(SAMPLE_PROFILE, SAMPLE_GOALS, user_id="user_force", db_path=temp_db)
        get_or_calculate_health_score(user_id="user_force", db_path=temp_db)

        # Force recalculate even if profile hasn't changed
        forced = get_or_calculate_health_score(user_id="user_force", force_recalculate=True, db_path=temp_db)
        assert forced is not None
        history = get_health_score_history(user_id="user_force", db_path=temp_db)
        assert len(history) == 2

    def test_nonexistent_profile_returns_incomplete_state(self, temp_db):
        res = get_or_calculate_health_score(user_id="ghost_user", db_path=temp_db)
        assert res["overall_score"] is None
        assert res["is_sufficient_data"] is False
        assert res["rating"] == "Incomplete Data"

    def test_cas_portfolio_integration_updates_investment_component(self, temp_db):
        save_profile(SAMPLE_PROFILE, SAMPLE_GOALS, user_id="user_cas", db_path=temp_db)

        # Baseline score without CAS
        score_base = get_or_calculate_health_score(user_id="user_cas", db_path=temp_db)
        inv_base = score_base["components"]["investment_health"]

        # Score with uploaded CAS portfolio (well-diversified, direct funds)
        cas_data = {
            "total_value": 800000.0,
            "fund_count": 5,
            "avg_expense_ratio": 0.60,
        }
        score_cas = get_or_calculate_health_score(
            user_id="user_cas",
            cas_portfolio=cas_data,
            force_recalculate=True,
            db_path=temp_db,
        )
        inv_cas = score_cas["components"]["investment_health"]
        assert inv_cas["is_available"] is True
        assert inv_cas["actual_value"] >= 800000.0
        assert "Well-balanced fund count" in inv_cas["explanation"]
        assert "Cost-efficient direct funds" in inv_cas["explanation"]

    def test_persisted_score_preserves_breakdown_and_disclaimer(self, temp_db):
        save_profile(SAMPLE_PROFILE, SAMPLE_GOALS, user_id="user_persist", db_path=temp_db)
        calc = get_or_calculate_health_score(user_id="user_persist", db_path=temp_db)
        latest = get_latest_health_score(user_id="user_persist", db_path=temp_db)

        assert latest is not None
        assert latest["overall_score"] == calc["overall_score"]
        assert "savings_rate" in latest["components"]
        assert "debt_burden" in latest["components"]
        assert "emergency_fund" in latest["components"]
        assert "investment_health" in latest["components"]
        assert "goal_progress" in latest["components"]
        assert latest["disclaimer"] is not None
