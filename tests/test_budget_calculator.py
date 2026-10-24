"""
tests/test_budget_calculator.py
Automated unit tests for deterministic budget calculations, financial summaries,
goal scheduling, emergency reserves, prioritization rules, and AI planner fallbacks.
"""
from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from utils.ai_financial_planner import _generate_deterministic_fallback, generate_plan_explanation
from utils.budget_calculator import (
    calculate_financial_summary,
    calculate_goal_contributions,
    calculate_remaining_months,
    generate_budget_recommendations,
)
from utils.financial_recommendations import generate_prioritized_financial_actions


class TestFinancialSummaryCalculations:

    def test_valid_income_and_expenses(self):
        profile = {
            "monthly_income": 100000.0,
            "essential_expenses": 40000.0,
            "discretionary_expenses": 20000.0,
            "other_expenses": 5000.0,
            "monthly_debt_repayment": 10000.0,
            "outstanding_debt": 150000.0,
            "savings_liquid": 120000.0,
        }
        res = calculate_financial_summary(profile)
        assert res["has_data"] is True
        assert res["monthly_income"] == 100000.0
        # Living expenses: 40k + 20k + 5k = 65k
        assert res["living_expenses"] == 65000.0
        # Debt repayment: 10k
        assert res["monthly_debt_repayment"] == 10000.0
        # Total outflows: 75k (no double counting)
        assert res["total_monthly_outflows"] == 75000.0
        # Surplus: 25k
        assert res["monthly_surplus"] == 25000.0
        assert res["is_deficit"] is False
        assert res["savings_rate"] == 25.0
        assert res["debt_to_income"] == 10.0

    def test_zero_income_handled_safely(self):
        profile = {
            "monthly_income": 0.0,
            "essential_expenses": 20000.0,
        }
        res = calculate_financial_summary(profile)
        assert res["has_data"] is False
        assert res["monthly_income"] == 0.0
        assert res["savings_rate"] == 0.0
        assert res["debt_to_income"] == 0.0
        assert res["is_deficit"] is True

    def test_negative_monthly_surplus_deficit(self):
        profile = {
            "monthly_income": 50000.0,
            "essential_expenses": 35000.0,
            "discretionary_expenses": 15000.0,
            "other_expenses": 5000.0,
            "monthly_debt_repayment": 10000.0,
        }
        # Outflows = 65k vs income 50k -> Deficit 15k
        res = calculate_financial_summary(profile)
        assert res["is_deficit"] is True
        assert res["monthly_surplus"] == -15000.0
        assert res["savings_rate"] == -30.0

    def test_missing_financial_fields_handled_safely(self):
        sparse_profile = {"monthly_income": 60000.0}
        res = calculate_financial_summary(sparse_profile)
        assert res["has_data"] is True
        assert res["essential_expenses"] == 0.0
        assert res["monthly_debt_repayment"] == 0.0
        assert res["total_monthly_outflows"] == 0.0
        assert res["monthly_surplus"] == 60000.0
        assert res["is_data_incomplete"] is True
        assert "Essential Living Expenses" in res["missing_fields"]
        assert "Liquid Savings" in res["missing_fields"]
        assert res["is_emergency_provisional"] is True

    def test_expense_categories_that_already_include_debt_repayments(self):
        # When user reports that their essential expenses already include EMI debt repayments
        profile = {
            "monthly_income": 90000.0,
            "essential_expenses": 45000.0,  # Already includes 15k EMI
            "discretionary_expenses": 20000.0,
            "other_expenses": 5000.0,
            "monthly_debt_repayment": 15000.0,
            "debt_included_in_expenses": True,
        }
        res = calculate_financial_summary(profile, debt_already_in_expenses=True)
        # Total outflows must be 45k + 20k + 5k = 70k (NOT 70k + 15k = 85k)
        assert res["total_monthly_outflows"] == 70000.0
        assert res["monthly_surplus"] == 20000.0
        assert res["debt_already_in_expenses"] is True
        # Verify breakdown sum matches total outflows exactly (no double-counting)
        cat_sum = sum(c["amount"] for c in res["breakdown"].values())
        assert cat_sum == 70000.0

    def test_no_double_counting_of_debt_in_outflows(self):
        profile = {
            "monthly_income": 80000.0,
            "essential_expenses": 30000.0,
            "discretionary_expenses": 10000.0,
            "other_expenses": 0.0,
            "monthly_debt_repayment": 15000.0,
        }
        res = calculate_financial_summary(profile)
        # Verify that total outflows equals exactly sum of categories (30k + 10k + 0k + 15k = 55k)
        cat_sum = sum(c["amount"] for c in res["breakdown"].values())
        assert cat_sum == res["total_monthly_outflows"]
        assert res["total_monthly_outflows"] == 55000.0


class TestBudgetRecommendationEngine:

    def test_user_with_positive_surplus(self):
        profile = {
            "monthly_income": 100000.0,
            "essential_expenses": 40000.0,
            "discretionary_expenses": 20000.0,
            "other_expenses": 0.0,
            "monthly_debt_repayment": 10000.0,
            "savings_liquid": 240000.0,  # 6 months emergency coverage
        }
        budget = generate_budget_recommendations(profile)
        assert budget["is_deficit"] is False
        assert budget["current_surplus"] == 30000.0
        # Discretionary is 20% (<35%), preserved as 20k
        assert budget["recommended_categories"]["Discretionary Living"]["recommended"] == 20000.0
        # Emergency buffer is fully funded, so emergency allocation is 0
        assert budget["emergency_allocation"]["recommended_monthly"] == 0.0

    def test_discretionary_trim_when_unusually_high(self):
        profile = {
            "monthly_income": 100000.0,
            "essential_expenses": 30000.0,
            "discretionary_expenses": 45000.0,  # 45% of income (> 35%)
            "other_expenses": 0.0,
            "monthly_debt_repayment": 5000.0,
            "savings_liquid": 100000.0,
        }
        budget = generate_budget_recommendations(profile)
        rec_disc = budget["recommended_categories"]["Discretionary Living"]["recommended"]
        # Trimmed to 25% of income (25k)
        assert rec_disc == 25000.0
        assert budget["potential_savings_improvement"] > 0

    def test_user_with_monthly_deficit(self):
        profile = {
            "monthly_income": 50000.0,
            "essential_expenses": 30000.0,
            "discretionary_expenses": 25000.0,
            "other_expenses": 0.0,
            "monthly_debt_repayment": 5000.0,
            "savings_liquid": 10000.0,
        }
        budget = generate_budget_recommendations(profile)
        assert budget["is_deficit"] is True
        # Fixed commitments = 30k + 5k = 35k. Income = 50k. Available for discretionary = 15k.
        rec_disc = budget["recommended_categories"]["Discretionary Living"]["recommended"]
        assert rec_disc < 25000.0
        assert budget["budget_surplus"] >= 0.0

    def test_structural_deficit_essential_and_debt_exceed_income(self):
        profile = {
            "monthly_income": 40000.0,
            "essential_expenses": 35000.0,
            "discretionary_expenses": 10000.0,
            "other_expenses": 0.0,
            "monthly_debt_repayment": 10000.0,  # 35k + 10k = 45k > 40k income
            "savings_liquid": 0.0,
        }
        budget = generate_budget_recommendations(profile)
        assert budget["is_deficit"] is True
        # Structural deficit flagged in notes
        has_structural_note = any("structural" in n.lower() for n in budget["notes"])
        assert has_structural_note
        # Discretionary reduced to 0
        assert budget["recommended_categories"]["Discretionary Living"]["recommended"] == 0.0

    def test_user_with_zero_surplus(self):
        # User whose outflows exactly equal take-home pay
        profile = {
            "monthly_income": 70000.0,
            "essential_expenses": 40000.0,
            "discretionary_expenses": 20000.0,
            "other_expenses": 0.0,
            "monthly_debt_repayment": 10000.0,
            "savings_liquid": 50000.0,
        }
        budget = generate_budget_recommendations(profile)
        assert budget["is_deficit"] is False
        assert budget["current_surplus"] == 0.0
        assert budget["budget_surplus"] == 0.0
        assert budget["recommended_categories"]["Emergency Savings"]["recommended"] == 0.0
        assert budget["recommended_categories"]["Financial Goals"]["recommended"] == 0.0
        assert budget["recommended_categories"]["Long-Term Investments"]["recommended"] == 0.0

    def test_debt_repayments_consuming_most_available_income(self):
        # Extreme DTI burden: debt repayments consume 65% of income
        profile = {
            "monthly_income": 100000.0,
            "essential_expenses": 25000.0,
            "discretionary_expenses": 10000.0,
            "other_expenses": 0.0,
            "monthly_debt_repayment": 65000.0,  # 65% DTI
            "savings_liquid": 20000.0,
        }
        budget = generate_budget_recommendations(profile)
        assert budget["recommended_categories"]["Debt Repayment"]["recommended"] == 65000.0
        assert budget["recommended_categories"]["Essential Living"]["recommended"] == 25000.0
        # Total outflows = 100k
        assert budget["recommended_outflows"] <= 100000.0
        assert budget["budget_surplus"] >= 0.0

    def test_missing_expense_categories_handled_gracefully(self):
        # Profile without discretionary or other expenses
        profile = {
            "monthly_income": 50000.0,
            "essential_expenses": 25000.0,
        }
        budget = generate_budget_recommendations(profile)
        assert budget["income"] == 50000.0
        assert budget["recommended_categories"]["Essential Living"]["recommended"] == 25000.0
        assert budget["recommended_categories"]["Discretionary Living"]["recommended"] == 0.0

    def test_correct_current_versus_recommended_comparisons(self):
        # Profile with high discretionary that gets trimmed
        profile = {
            "monthly_income": 100000.0,
            "essential_expenses": 30000.0,
            "discretionary_expenses": 40000.0,  # 40% of income -> trimmed to 25k (diff = -15k)
            "other_expenses": 5000.0,
            "monthly_debt_repayment": 5000.0,
            "savings_liquid": 60000.0,
        }
        budget = generate_budget_recommendations(profile)
        disc_cat = budget["recommended_categories"]["Discretionary Living"]
        assert disc_cat["current"] == 40000.0
        assert disc_cat["recommended"] == 25000.0
        assert disc_cat["diff"] == -15000.0
        assert budget["potential_savings_improvement"] == 15000.0

    def test_allocations_never_exceed_income(self):
        profile = {
            "monthly_income": 60000.0,
            "essential_expenses": 30000.0,
            "discretionary_expenses": 15000.0,
            "other_expenses": 0.0,
            "monthly_debt_repayment": 5000.0,
            "savings_liquid": 0.0,
        }
        goals = [{"name": "Car", "target_amount": 500000.0, "current_amount": 0.0, "target_date": "2027-12-31"}]
        budget = generate_budget_recommendations(profile, goals=goals)

        total_allocations = (
            budget["recommended_categories"]["Essential Living"]["recommended"]
            + budget["recommended_categories"]["Discretionary Living"]["recommended"]
            + budget["recommended_categories"]["Other Expenses"]["recommended"]
            + budget["recommended_categories"]["Debt Repayment"]["recommended"]
            + budget["recommended_categories"]["Emergency Savings"]["recommended"]
            + budget["recommended_categories"]["Financial Goals"]["recommended"]
            + budget["recommended_categories"]["Long-Term Investments"]["recommended"]
        )
        assert total_allocations <= budget["income"] + 0.01


class TestGoalAllocation:

    def test_calculate_remaining_months(self):
        ref_date = date(2026, 1, 1)
        assert calculate_remaining_months("2026-06-30", current_date=ref_date) == 5
        assert calculate_remaining_months("2027-01-01", current_date=ref_date) == 12
        assert calculate_remaining_months("2025-12-31", current_date=ref_date) == 0
        assert calculate_remaining_months("", current_date=ref_date) == 0
        assert calculate_remaining_months(None, current_date=ref_date) == 0

    def test_single_goal_fully_funded(self):
        goals = [
            {"name": "Laptop", "target_amount": 60000.0, "current_amount": 12000.0, "target_date": "2026-07-01"}
        ]
        # 48k remaining over 6 months = 8k/mo required
        ref_date = date(2026, 1, 1)
        res = calculate_goal_contributions(goals, available_surplus=15000.0, current_date=ref_date)
        assert res["has_goals"] is True
        assert res["total_required_monthly"] == 8000.0
        assert res["total_allocated_monthly"] == 8000.0
        assert res["is_fully_funded"] is True
        assert res["surplus_shortfall"] == 0.0

    def test_insufficient_surplus_prorates_goals(self):
        goals = [
            {"name": "Goal A", "target_amount": 100000.0, "current_amount": 0.0, "target_date": "2026-11-01"},  # 10k/mo
            {"name": "Goal B", "target_amount": 100000.0, "current_amount": 0.0, "target_date": "2026-11-01"},  # 10k/mo
        ]
        # Total required = 20k/mo. Available surplus = 10k/mo.
        ref_date = date(2026, 1, 1)
        res = calculate_goal_contributions(goals, available_surplus=10000.0, current_date=ref_date)
        assert res["is_fully_funded"] is False
        assert res["total_allocated_monthly"] <= 10000.01
        assert res["surplus_shortfall"] == 10000.0
        for g in res["goals_detail"]:
            assert g["allocated_monthly"] == 5000.0
            assert g["shortfall"] == 5000.0

    def test_completed_and_expired_goals_handled(self):
        ref_date = date(2026, 5, 1)
        goals = [
            {"name": "Done Goal", "target_amount": 50000.0, "current_amount": 50000.0, "target_date": "2026-12-31"},
            {"name": "Past Goal", "target_amount": 30000.0, "current_amount": 10000.0, "target_date": "2025-12-31"},
        ]
        res = calculate_goal_contributions(goals, available_surplus=5000.0, current_date=ref_date)
        g_done = res["goals_detail"][0]
        g_past = res["goals_detail"][1]

        assert g_done["is_completed"] is True
        assert g_done["required_monthly"] == 0.0

        assert g_past["is_expired"] is True
        assert g_past["remaining_months"] == 0
        assert g_past["required_monthly"] == 20000.0

    def test_goal_with_missing_current_savings(self):
        # Goal where current_amount is missing or None
        goals = [
            {"name": "Emergency Vacation", "target_amount": 50000.0, "current_amount": None, "target_date": "2026-11-01"}
        ]
        ref_date = date(2026, 1, 1)
        res = calculate_goal_contributions(goals, available_surplus=10000.0, current_date=ref_date)
        g = res["goals_detail"][0]
        assert g["current_amount"] == 0.0
        assert g["remaining_amount"] == 50000.0
        assert g["required_monthly"] == 5000.0

    def test_goal_with_invalid_target_date(self):
        # Goal where target_date is an invalid string
        goals = [
            {"name": "Future Car", "target_amount": 300000.0, "current_amount": 0.0, "target_date": "invalid-date-string"}
        ]
        ref_date = date(2026, 1, 1)
        res = calculate_goal_contributions(goals, available_surplus=10000.0, current_date=ref_date)
        g = res["goals_detail"][0]
        assert g["status"] == "Invalid Target Date"
        assert g["required_monthly"] == 0.0
        assert g["is_valid_date"] is False


class TestEmergencySavingsIntegration:

    def test_inadequate_emergency_reserve_prioritized(self):
        # 10k liquid on 40k essential expenses -> 0.25 months (< 1 month)
        profile = {
            "monthly_income": 90000.0,
            "essential_expenses": 40000.0,
            "discretionary_expenses": 20000.0,
            "other_expenses": 0.0,
            "monthly_debt_repayment": 10000.0,
            "savings_liquid": 10000.0,
        }
        budget = generate_budget_recommendations(profile)
        emg = budget["emergency_allocation"]
        assert emg["coverage_months"] == 0.25
        assert emg["recommended_monthly"] > 0
        # Check notes highlight emergency priority
        has_emg_note = any("emergency" in n.lower() for n in budget["notes"])
        assert has_emg_note

    def test_adequate_emergency_reserve_no_extra_allocation(self):
        # 300k liquid on 40k essential expenses -> 7.5 months (> 6 months)
        profile = {
            "monthly_income": 100000.0,
            "essential_expenses": 40000.0,
            "discretionary_expenses": 20000.0,
            "other_expenses": 0.0,
            "monthly_debt_repayment": 0.0,
            "savings_liquid": 300000.0,
        }
        budget = generate_budget_recommendations(profile)
        assert budget["emergency_allocation"]["recommended_monthly"] == 0.0
        assert budget["emergency_allocation"]["shortfall"] == 0.0

    def test_missing_emergency_savings_data_flagged_provisional(self):
        # When savings_liquid is None/missing in profile
        profile = {
            "monthly_income": 80000.0,
            "essential_expenses": 35000.0,
            "discretionary_expenses": 15000.0,
            "savings_liquid": None,
        }
        budget = generate_budget_recommendations(profile)
        emg = budget["emergency_allocation"]
        assert emg["is_provisional"] is True
        assert any("provisional" in n.lower() for n in budget["notes"])

    def test_zero_essential_expenses_emergency_handling(self):
        # When essential_expenses is 0, no division by zero error occurs
        profile = {
            "monthly_income": 50000.0,
            "essential_expenses": 0.0,
            "savings_liquid": 50000.0,
        }
        budget = generate_budget_recommendations(profile)
        emg = budget["emergency_allocation"]
        assert emg["coverage_months"] == 0.0
        assert emg["is_essential_zero"] is True

    def test_no_double_counting_of_contributions(self):
        # Verify emergency + goals + investments partitioned strictly without double counting
        profile = {
            "monthly_income": 100000.0,
            "essential_expenses": 30000.0,
            "discretionary_expenses": 20000.0,
            "savings_liquid": 30000.0,  # 1 month (< 3 mo) -> needs emergency
        }
        goals = [{"name": "Retirement Fund", "target_amount": 1000000.0, "current_amount": 0.0, "target_date": "2030-12-31"}]
        budget = generate_budget_recommendations(profile, goals=goals)
        emg_m = budget["recommended_categories"]["Emergency Savings"]["recommended"]
        goal_m = budget["recommended_categories"]["Financial Goals"]["recommended"]
        inv_m = budget["recommended_categories"]["Long-Term Investments"]["recommended"]

        # Sum of savings and investment allocations exactly equals budget surplus
        assert round(emg_m + goal_m + inv_m, 2) == round(budget["budget_surplus"], 2)
        assert round(budget["total_savings_and_investments"], 2) == round(budget["budget_surplus"], 2)


class TestPrioritizedFinancialActions:

    def test_actions_ranked_by_financial_urgency(self):
        summary = {
            "monthly_income": 80000.0,
            "monthly_surplus": -10000.0,  # In deficit
            "is_deficit": True,
            "debt_to_income": 55.0,        # Critical DTI
            "monthly_debt_repayment": 44000.0,
            "outstanding_debt": 500000.0,
            "savings_liquid": 5000.0,
            "essential_expenses": 35000.0,
        }
        budget = generate_budget_recommendations(summary)
        actions = generate_prioritized_financial_actions(summary, budget)

        assert len(actions) > 0
        # Top actions must be High priority addressing cash flow or debt
        high_prio = [a for a in actions if a["priority"] == "High"]
        assert len(high_prio) >= 1
        assert any("deficit" in a["title"].lower() or "debt" in a["title"].lower() for a in high_prio)

    def test_unranked_debt_cost_disclosure(self):
        summary = {
            "monthly_income": 100000.0,
            "monthly_surplus": 20000.0,
            "is_deficit": False,
            "debt_to_income": 40.0,
            "monthly_debt_repayment": 40000.0,
            "outstanding_debt": 300000.0,
            "savings_liquid": 150000.0,
            "essential_expenses": 30000.0,
        }
        budget = generate_budget_recommendations(summary)
        actions = generate_prioritized_financial_actions(summary, budget)
        debt_action = next((a for a in actions if "debt" in a["title"].lower()), None)
        assert debt_action is not None
        # Confirms disclosure that interest rates are not tracked
        assert "interest rates were not provided" in debt_action["action"].lower()


class TestAIFinancialPlannerFallback:

    def test_deterministic_fallback_generation(self):
        summary = {
            "monthly_income": 90000.0,
            "monthly_surplus": 25000.0,
            "is_deficit": False,
            "savings_rate": 27.8,
            "debt_to_income": 11.1,
        }
        budget = {
            "recommended_categories": {
                "Discretionary Living": {"recommended": 18000.0, "diff": -2000.0}
            },
            "emergency_allocation": {"coverage_months": 2.5, "recommended_monthly": 8000.0},
        }
        fallback = _generate_deterministic_fallback(summary, budget)
        assert "Executive Financial Summary" in fallback
        assert "Budget Adjustments & Rationale" in fallback
        assert "Debt & Emergency Reserves Roadmap" in fallback
        assert "Goal Strategy & Next Steps" in fallback
        assert "₹25,000" in fallback

    def test_ai_unavailable_returns_deterministic_fallback_without_error(self):
        summary = {
            "monthly_income": 80000.0,
            "monthly_surplus": 15000.0,
            "is_deficit": False,
            "savings_rate": 18.8,
            "debt_to_income": 15.0,
        }
        budget = {
            "recommended_categories": {"Discretionary Living": {"recommended": 15000.0, "diff": 0.0}},
            "emergency_allocation": {"coverage_months": 4.0, "recommended_monthly": 0.0},
        }
        with patch("utils.ai_financial_planner._client", None):
            res = generate_plan_explanation(summary, budget)
            assert "Executive Financial Summary" in res
            assert "₹80,000" in res or "₹15,000" in res

    def test_ai_exception_or_invalid_response_falls_back(self):
        summary = {
            "monthly_income": 80000.0,
            "monthly_surplus": 15000.0,
            "is_deficit": False,
            "savings_rate": 18.8,
            "debt_to_income": 15.0,
        }
        budget = {
            "recommended_categories": {"Discretionary Living": {"recommended": 15000.0, "diff": 0.0}},
            "emergency_allocation": {"coverage_months": 4.0, "recommended_monthly": 0.0},
        }
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API Rate Limit Exceeded")
        with patch("utils.ai_financial_planner._client", mock_client):
            res = generate_plan_explanation(summary, budget)
            assert "unavailable" in res.lower()
            assert "Executive Financial Summary" in res
