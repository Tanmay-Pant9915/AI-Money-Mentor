"""
tests/test_money_health_score.py
Unit tests for deterministic Money Health Score calculations, individual components,
curves, interpolation, weight normalization, and incomplete data states.
"""
import math
import pytest

from utils.money_health_score import (
    calculate_debt_burden_score,
    calculate_emergency_fund_score,
    calculate_goal_progress_score,
    calculate_investment_health_score,
    calculate_money_health_score,
    calculate_savings_rate_score,
    classify_rating,
)


class TestSavingsRateScore:

    def test_zero_or_missing_income(self):
        res1 = calculate_savings_rate_score(0.0, 30000.0)
        assert res1["is_available"] is False
        assert res1["score"] == 0.0

        res2 = calculate_savings_rate_score(None, 30000.0)
        assert res2["is_available"] is False

    def test_negative_surplus_deficit(self):
        # Income 50k, Expenses 60k -> Deficit -10k -> 0 points
        res = calculate_savings_rate_score(50000.0, 60000.0)
        assert res["is_available"] is True
        assert res["score"] == 0.0
        assert res["status"] == "Deficit"
        assert res["actual_value"] == -20.0  # -20% savings rate

    def test_breaking_even_zero_savings(self):
        # Income 50k, Expenses 50k -> 0% savings rate -> 20 points
        res = calculate_savings_rate_score(50000.0, 50000.0)
        assert res["is_available"] is True
        assert res["score"] == 20.0
        assert res["actual_value"] == 0.0

    def test_reference_points_and_interpolation(self):
        # 10% savings rate: exactly 50 points
        res_10 = calculate_savings_rate_score(100000.0, 90000.0)
        assert res_10["score"] == 50.0

        # 5% savings rate: interpolation between 0% (20 pts) and 10% (50 pts) -> 35 pts
        res_5 = calculate_savings_rate_score(100000.0, 95000.0)
        assert res_5["score"] == 35.0

        # 20% savings rate: exactly 80 points
        res_20 = calculate_savings_rate_score(100000.0, 80000.0)
        assert res_20["score"] == 80.0

        # 15% savings rate: interpolation between 10% (50 pts) and 20% (80 pts) -> 65 pts
        res_15 = calculate_savings_rate_score(100000.0, 85000.0)
        assert res_15["score"] == 65.0

        # 30% savings rate: exactly 100 points
        res_30 = calculate_savings_rate_score(100000.0, 70000.0)
        assert res_30["score"] == 100.0

        # > 30% savings rate: capped at 100 points
        res_50 = calculate_savings_rate_score(100000.0, 50000.0)
        assert res_50["score"] == 100.0


class TestDebtBurdenScore:

    def test_debt_free(self):
        # Zero repayments and zero debt -> 100 points
        res = calculate_debt_burden_score(100000.0, 0.0, 0.0)
        assert res["is_available"] is True
        assert res["score"] == 100.0
        assert res["status"] == "Debt-Free"

    def test_unserviced_debt(self):
        # Outstanding debt reported without repayment
        res = calculate_debt_burden_score(100000.0, 0.0, 200000.0)
        assert res["is_available"] is True
        assert res["score"] == 70.0
        assert res["status"] == "Unserviced Debt"

    def test_missing_debt_or_income(self):
        res1 = calculate_debt_burden_score(None, 10000.0)
        assert res1["is_available"] is False

        res2 = calculate_debt_burden_score(100000.0, None)
        assert res2["is_available"] is False

    def test_increasing_debt_to_income(self):
        # DTI = 10% -> 95 points
        res_10 = calculate_debt_burden_score(100000.0, 10000.0)
        assert res_10["score"] == 95.0

        # DTI = 20% -> 80 points
        res_20 = calculate_debt_burden_score(100000.0, 20000.0)
        assert res_20["score"] == 80.0

        # DTI = 36% -> 50 points
        res_36 = calculate_debt_burden_score(100000.0, 36000.0)
        assert res_36["score"] == 50.0

        # DTI = 50% -> 20 points
        res_50 = calculate_debt_burden_score(100000.0, 50000.0)
        assert res_50["score"] == 20.0

        # DTI >= 70% -> 0 points
        res_75 = calculate_debt_burden_score(100000.0, 75000.0)
        assert res_75["score"] == 0.0

    def test_unconfirmed_debt_when_outstanding_is_none(self):
        # Repayment is 0, but total debt is unrecorded (None) -> Unconfirmed Debt, not 100 pts
        res = calculate_debt_burden_score(100000.0, 0.0, None)
        assert res["is_available"] is True
        assert res["score"] == 85.0
        assert res["status"] == "Unconfirmed Debt"

    def test_debt_threshold_boundaries(self):
        # Around 10%:
        res_9_0 = calculate_debt_burden_score(100000.0, 9000.0)
        assert res_9_0["score"] > 95.0
        res_10_0 = calculate_debt_burden_score(100000.0, 10000.0)
        assert res_10_0["score"] == 95.0
        res_11_0 = calculate_debt_burden_score(100000.0, 11000.0)
        assert res_11_0["score"] < 95.0

        # Around 20%:
        res_19_0 = calculate_debt_burden_score(100000.0, 19000.0)
        assert res_19_0["score"] > 80.0
        res_20_0 = calculate_debt_burden_score(100000.0, 20000.0)
        assert res_20_0["score"] == 80.0
        res_21_0 = calculate_debt_burden_score(100000.0, 21000.0)
        assert res_21_0["score"] < 80.0

        # Around 36%:
        res_35_0 = calculate_debt_burden_score(100000.0, 35000.0)
        assert res_35_0["score"] > 50.0
        res_36_0 = calculate_debt_burden_score(100000.0, 36000.0)
        assert res_36_0["score"] == 50.0
        res_37_0 = calculate_debt_burden_score(100000.0, 37000.0)
        assert res_37_0["score"] < 50.0

        # Around 50%:
        res_49_0 = calculate_debt_burden_score(100000.0, 49000.0)
        assert res_49_0["score"] > 20.0
        res_50_0 = calculate_debt_burden_score(100000.0, 50000.0)
        assert res_50_0["score"] == 20.0
        res_51_0 = calculate_debt_burden_score(100000.0, 51000.0)
        assert res_51_0["score"] < 20.0

        # Around 70%:
        res_69_0 = calculate_debt_burden_score(100000.0, 69000.0)
        assert res_69_0["score"] > 0.0
        res_70_0 = calculate_debt_burden_score(100000.0, 70000.0)
        assert res_70_0["score"] == 0.0


class TestEmergencyFundScore:

    def test_zero_liquid_savings(self):
        res = calculate_emergency_fund_score(0.0, 40000.0)
        assert res["is_available"] is True
        assert res["score"] == 0.0
        assert res["actual_value"] == 0.0
        assert res["shortfall"] == 240000.0  # 6 * 40k

    def test_missing_or_zero_essential_expenses(self):
        res1 = calculate_emergency_fund_score(100000.0, 0.0)
        assert res1["is_available"] is False

        res2 = calculate_emergency_fund_score(100000.0, None)
        assert res2["is_available"] is False

    def test_reference_points_coverage(self):
        # 1 Month coverage: exactly 25 points
        res_1 = calculate_emergency_fund_score(40000.0, 40000.0)
        assert res_1["score"] == 25.0

        # 3 Months coverage: exactly 60 points
        res_3 = calculate_emergency_fund_score(120000.0, 40000.0)
        assert res_3["score"] == 60.0

        # 6 Months coverage: exactly 100 points
        res_6 = calculate_emergency_fund_score(240000.0, 40000.0)
        assert res_6["score"] == 100.0
        assert res_6["shortfall"] == 0.0

        # > 6 Months coverage: capped at 100 points
        res_10 = calculate_emergency_fund_score(400000.0, 40000.0)
        assert res_10["score"] == 100.0

    def test_unknown_liquid_savings(self):
        res = calculate_emergency_fund_score(None, 40000.0)
        assert res["is_available"] is False
        assert res["score"] == 0.0

    def test_emergency_interpolation(self):
        # 0.5 months: 0.5 * 25 = 12.5 points
        res_0_5 = calculate_emergency_fund_score(20000.0, 40000.0)
        assert res_0_5["score"] == 12.5

        # 2 months: 25 + (1/2)*35 = 42.5 points
        res_2 = calculate_emergency_fund_score(80000.0, 40000.0)
        assert res_2["score"] == 42.5

        # 4.5 months: 60 + (1.5/3)*40 = 80.0 points
        res_4_5 = calculate_emergency_fund_score(180000.0, 40000.0)
        assert res_4_5["score"] == 80.0


class TestInvestmentHealthScore:

    def test_missing_investment_data(self):
        res = calculate_investment_health_score(None, 100000.0)
        assert res["is_available"] is False

    def test_zero_investments_reported(self):
        res = calculate_investment_health_score(0.0, 100000.0)
        assert res["is_available"] is True
        assert res["score"] == 10.0
        assert res["status"] == "Not Started"

    def test_healthy_investments_ratio(self):
        # Annual income = 12 * 100k = 12 Lakhs.
        # Investments = 18 Lakhs (ratio 1.5) -> Base score 85
        res = calculate_investment_health_score(1800000.0, 100000.0)
        assert res["is_available"] is True
        assert res["score"] >= 80.0

    def test_cas_portfolio_diversification_bonus(self):
        cas_data = {
            "total_value": 500000.0,
            "fund_count": 5,
            "avg_expense_ratio": 0.65,
        }
        res = calculate_investment_health_score(500000.0, 100000.0, cas_portfolio=cas_data)
        assert res["is_available"] is True
        assert "Well-balanced fund count" in res["explanation"]
        assert "Cost-efficient direct funds" in res["explanation"]

    def test_risk_profile_aware_rules(self):
        # Aggressive risk with zero investments -> penalty note
        res_agg = calculate_investment_health_score(
            0.0, 100000.0, risk_assessment={"classification": "Aggressive"}
        )
        assert res_agg["is_available"] is True
        assert "Aggressive risk tolerance but zero investment" in res_agg["explanation"]

        # Moderate with investments -> positive alignment note
        res_mod = calculate_investment_health_score(
            500000.0, 100000.0, risk_assessment={"classification": "Moderate"}
        )
        assert "aligned with Moderate profile" in res_mod["explanation"]

    def test_unknown_asset_allocation_does_not_fabricate(self):
        # Without CAMS portfolio, no fabricated fund holdings or allocations
        res = calculate_investment_health_score(300000.0, 50000.0)
        assert "schemes" not in res["explanation"]
        assert "expense" not in res["explanation"].lower()


class TestGoalProgressScore:

    def test_no_goals(self):
        res = calculate_goal_progress_score([])
        assert res["is_available"] is False

    def test_zero_target_amount_and_missing_saved(self):
        goals = [
            {"name": "Invalid Target", "target_amount": 0.0, "current_amount": 1000.0},
            {"name": "Valid Goal", "target_amount": 50000.0, "current_amount": None},  # current None -> 0.0 saved
        ]
        res = calculate_goal_progress_score(goals)
        assert res["is_available"] is True
        assert res["score"] == 0.0

    def test_invalid_target_dates_handled_safely(self):
        goals = [
            {"name": "Date Bad", "target_amount": 100000.0, "target_date": "invalid-date", "current_amount": 50000.0}
        ]
        res = calculate_goal_progress_score(goals)
        assert res["is_available"] is True
        assert res["score"] == 50.0

    def test_missing_contribution_history_no_schedule_claimed(self):
        # The engine must evaluate funded progress without falsely claiming schedule track record
        goals = [{"name": "Retirement", "target_amount": 1000000.0, "current_amount": 250000.0}]
        res = calculate_goal_progress_score(goals)
        assert res["is_available"] is True
        assert res["score"] == 25.0
        assert "schedule" not in res["explanation"].lower() or "not" in res.get("schedule_note", "").lower()

    def test_single_and_multiple_goals(self):
        goals = [
            {"name": "Emergency Fund", "target_amount": 100000.0, "current_amount": 50000.0},  # 50%
            {"name": "Car", "target_amount": 200000.0, "current_amount": 200000.0},            # 100%
        ]
        res = calculate_goal_progress_score(goals)
        assert res["is_available"] is True
        # Average: (50 + 100) / 2 = 75.0%
        assert res["score"] == 75.0

    def test_overfunded_goal_capped_at_100(self):
        goals = [
            {"name": "Vacation", "target_amount": 50000.0, "current_amount": 100000.0},  # 200% -> capped 100%
            {"name": "Laptop", "target_amount": 100000.0, "current_amount": 0.0},        # 0%
        ]
        res = calculate_goal_progress_score(goals)
        assert res["score"] == 50.0  # (100 + 0) / 2 = 50%


class TestOverallHealthScore:

    SAMPLE_FULL_PROFILE = {
        "monthly_income": 100000.0,
        "essential_expenses": 40000.0,
        "discretionary_expenses": 20000.0,
        "other_expenses": 5000.0,
        "monthly_debt_repayment": 15000.0,
        "savings_liquid": 240000.0,
        "outstanding_debt": 300000.0,
        "existing_investments": 600000.0,
        "goals": [
            {"name": "House", "target_amount": 1000000.0, "current_amount": 200000.0}
        ],
    }

    def test_all_components_available(self):
        result = calculate_money_health_score(self.SAMPLE_FULL_PROFILE)
        assert result["is_sufficient_data"] is True
        assert result["data_completeness"] == 100.0
        assert 0 <= result["overall_score"] <= 100
        assert result["rating"] in ["Needs Attention", "Fair", "Good", "Excellent"]
        assert len(result["excluded_components"]) == 0
        assert len(result["insights"]) > 0
        assert len(result["recommendations"]) > 0

    def test_missing_components_weight_normalization(self):
        # Profile without goals and without investment data
        partial_profile = {
            "monthly_income": 100000.0,
            "essential_expenses": 40000.0,
            "discretionary_expenses": 20000.0,
            "other_expenses": 0.0,
            "monthly_debt_repayment": 10000.0,
            "savings_liquid": 200000.0,
            "outstanding_debt": 0.0,
            "existing_investments": None,
            "goals": [],
        }
        res = calculate_money_health_score(partial_profile)
        assert res["is_sufficient_data"] is True
        # savings (0.25) + debt (0.25) + emergency (0.20) = 0.70 -> 70% data completeness
        assert res["data_completeness"] == 70.0
        assert res["overall_score"] is not None
        assert "Goal Progress" in res["excluded_components"]
        assert "Investment Health" in res["excluded_components"]

    def test_insufficient_data_state(self):
        # Almost no data
        sparse_profile = {
            "monthly_income": 0.0,
            "essential_expenses": None,
        }
        res = calculate_money_health_score(sparse_profile)
        assert res["is_sufficient_data"] is False
        assert res["overall_score"] is None
        assert res["rating"] == "Incomplete Data"

    def test_no_nan_or_infinity(self):
        edge_profile = {
            "monthly_income": 1.0,
            "essential_expenses": 0.0,
            "discretionary_expenses": 0.0,
            "other_expenses": 0.0,
            "monthly_debt_repayment": 0.0,
            "savings_liquid": 0.0,
            "outstanding_debt": 0.0,
            "existing_investments": 0.0,
            "goals": [],
        }
        res = calculate_money_health_score(edge_profile)
        if res["overall_score"] is not None:
            assert not math.isnan(res["overall_score"])
            assert not math.isinf(res["overall_score"])

    def test_classify_rating_boundaries(self):
        assert classify_rating(0) == "Needs Attention"
        assert classify_rating(39) == "Needs Attention"
        assert classify_rating(40) == "Fair"
        assert classify_rating(59) == "Fair"
        assert classify_rating(60) == "Good"
        assert classify_rating(79) == "Good"
        assert classify_rating(80) == "Excellent"
        assert classify_rating(100) == "Excellent"
        assert classify_rating(None) == "Incomplete Data"

    def test_minimum_possible_score_low(self):
        # Heavy deficit, critical debt (DTI 80%), zero emergency fund, no investments
        stressed_profile = {
            "monthly_income": 50000.0,
            "essential_expenses": 40000.0,
            "discretionary_expenses": 20000.0,
            "other_expenses": 10000.0,
            "monthly_debt_repayment": 40000.0,  # 80% DTI
            "savings_liquid": 0.0,
            "outstanding_debt": 500000.0,
            "existing_investments": 0.0,
            "goals": [],
        }
        res = calculate_money_health_score(stressed_profile)
        assert res["overall_score"] is not None
        assert res["overall_score"] <= 10  # Very low score
        assert res["rating"] == "Needs Attention"

    def test_maximum_possible_score_hundred(self):
        # 50% savings, 0 debt, 12 months emergency, large investments, 100% goals
        stellar_profile = {
            "monthly_income": 200000.0,
            "essential_expenses": 50000.0,
            "discretionary_expenses": 30000.0,
            "other_expenses": 0.0,
            "monthly_debt_repayment": 0.0,
            "savings_liquid": 600000.0,  # 12 months coverage
            "outstanding_debt": 0.0,
            "existing_investments": 5000000.0,
            "goals": [{"name": "Retirement", "target_amount": 100000.0, "current_amount": 100000.0}],
        }
        res = calculate_money_health_score(stellar_profile)
        assert res["overall_score"] == 100
        assert res["rating"] == "Excellent"

    def test_expenses_with_debt_repayments_no_double_counting(self):
        # Living expenses (30k + 10k = 40k) + debt repayment (20k) = 60k total commitments
        # Income = 50k -> deficit 10k
        profile = {
            "monthly_income": 50000.0,
            "essential_expenses": 30000.0,
            "discretionary_expenses": 10000.0,
            "other_expenses": 0.0,
            "monthly_debt_repayment": 20000.0,
            "savings_liquid": 50000.0,
            "outstanding_debt": 100000.0,
            "existing_investments": 0.0,
        }
        res = calculate_money_health_score(profile)
        assert res["is_sufficient_data"] is True
        # Verify an insight specifically flagged living expenses + debt repayments exceeding income
        has_commitments_flag = any(
            "living expenses" in ins.lower() and "debt repayments" in ins.lower()
            for ins in res["insights"]
        )
        assert has_commitments_flag
