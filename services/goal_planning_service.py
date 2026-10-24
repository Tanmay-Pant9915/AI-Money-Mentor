"""
services/goal_planning_service.py
Service layer for Goal-Based Investment Planning in AI Money Mentor.
Orchestrates goal management (CRUD), feasibility evaluation, budget surplus
integration, deterministic compound investment projections, risk-aware asset
allocations, and what-if scenario evaluation.
"""
from datetime import date, datetime
import math
from typing import Any, Dict, List, Optional, Tuple

from data.database import get_connection, init_db
from services.financial_planning_service import generate_active_plan
from services.profile_service import get_profile
from services.risk_profile_service import get_latest_risk_assessment
from utils.goal_allocation import generate_goal_asset_allocation
from utils.goal_calculator import (
    GOAL_CATEGORIES,
    GOAL_PRIORITIES,
    evaluate_goal_feasibility,
    evaluate_goals_portfolio,
    parse_goal_target_date,
)
from utils.investment_projection import (
    calculate_required_contribution_for_target,
    project_investment_growth,
)


def _ensure_profile_id(user_id: str, db_path: Optional[str] = None) -> int:
    """Ensure a financial profile row exists for the user and return its ID."""
    init_db(db_path)
    now_str = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM financial_profiles WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return int(row["id"])

        cursor.execute(
            """
            INSERT INTO financial_profiles (
                user_id, name, age, employment_status, monthly_income,
                essential_expenses, discretionary_expenses, other_expenses,
                savings_liquid, outstanding_debt, monthly_debt_repayment,
                existing_investments, dependents, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                "Investor",
                30,
                "Salaried Employee",
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0,
                now_str,
                now_str,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def get_user_goals(user_id: str = "default_user", db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all financial goals for a given user ordered by priority and target date."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT g.id, g.profile_id, g.name, g.category, g.target_amount,
                   g.target_date, g.current_amount, g.monthly_contribution,
                   g.priority, g.is_completed, g.created_at, g.updated_at
            FROM financial_goals g
            JOIN financial_profiles p ON g.profile_id = p.id
            WHERE p.user_id = ?
            ORDER BY g.is_completed ASC,
                     CASE g.priority
                         WHEN 'High' THEN 1
                         WHEN 'Medium' THEN 2
                         WHEN 'Low' THEN 3
                         ELSE 4
                     END ASC,
                     g.target_date ASC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_goal_by_id(
    goal_id: int, user_id: str = "default_user", db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Retrieve a single goal by ID, ensuring it belongs to the specified user."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT g.*
            FROM financial_goals g
            JOIN financial_profiles p ON g.profile_id = p.id
            WHERE g.id = ? AND p.user_id = ?
            """,
            (goal_id, user_id),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def validate_goal_input(goal_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate user input fields for creating or updating a financial goal."""
    errors: List[str] = []

    name = str(goal_data.get("name") or "").strip()
    if not name:
        errors.append("Goal name cannot be empty.")

    target_amount = goal_data.get("target_amount")
    try:
        val = float(target_amount)
        if val <= 0:
            errors.append("Target amount must be greater than zero.")
    except (ValueError, TypeError):
        errors.append("Target amount must be a valid positive number.")

    current_amount = goal_data.get("current_amount", 0.0)
    try:
        cur_val = float(current_amount or 0.0)
        if cur_val < 0:
            errors.append("Current saved amount cannot be negative.")
    except (ValueError, TypeError):
        errors.append("Current saved amount must be a valid number.")

    monthly_contrib = goal_data.get("monthly_contribution", 0.0)
    try:
        mo_val = float(monthly_contrib or 0.0)
        if mo_val < 0:
            errors.append("Monthly contribution cannot be negative.")
    except (ValueError, TypeError):
        errors.append("Monthly contribution must be a valid number.")

    target_date_val = goal_data.get("target_date")
    is_valid_date, _, _ = parse_goal_target_date(target_date_val)
    if not is_valid_date:
        errors.append("Target date must be a valid date in YYYY-MM-DD or YYYY-MM format.")

    category = str(goal_data.get("category") or "Other").strip()
    if category not in GOAL_CATEGORIES:
        errors.append(f"Invalid category '{category}'. Must be one of {GOAL_CATEGORIES}.")

    priority = str(goal_data.get("priority") or "Medium").strip().capitalize()
    if priority not in GOAL_PRIORITIES:
        errors.append(f"Invalid priority '{priority}'. Must be High, Medium, or Low.")

    return len(errors) == 0, errors


def create_goal(
    goal_data: Dict[str, Any], user_id: str = "default_user", db_path: Optional[str] = None
) -> Tuple[bool, Optional[Dict[str, Any]], List[str]]:
    """Create a new financial goal with full validation and persistence."""
    is_valid, errors = validate_goal_input(goal_data)
    if not is_valid:
        return False, None, errors

    profile_id = _ensure_profile_id(user_id=user_id, db_path=db_path)
    now_str = datetime.now().isoformat()

    target_date_str = str(goal_data["target_date"]).strip()
    if isinstance(goal_data["target_date"], (date, datetime)):
        target_date_str = goal_data["target_date"].strftime("%Y-%m-%d")

    category = str(goal_data.get("category") or "Other").strip()
    priority = str(goal_data.get("priority") or "Medium").strip().capitalize()
    target_amount = float(goal_data["target_amount"])
    current_amount = float(goal_data.get("current_amount", 0.0) or 0.0)
    monthly_contribution = float(goal_data.get("monthly_contribution", 0.0) or 0.0)
    is_completed = 1 if (goal_data.get("is_completed") or current_amount >= target_amount) else 0

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO financial_goals (
                profile_id, name, category, target_amount, target_date, current_amount,
                monthly_contribution, priority, is_completed, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id,
                str(goal_data["name"]).strip(),
                category,
                target_amount,
                target_date_str,
                current_amount,
                monthly_contribution,
                priority,
                is_completed,
                now_str,
                now_str,
            ),
        )
        new_id = cursor.lastrowid
        conn.commit()

    created_goal = get_goal_by_id(new_id, user_id=user_id, db_path=db_path)
    return True, created_goal, []


def update_goal(
    goal_id: int, goal_data: Dict[str, Any], user_id: str = "default_user", db_path: Optional[str] = None
) -> Tuple[bool, Optional[Dict[str, Any]], List[str]]:
    """Update existing financial goal details."""
    is_valid, errors = validate_goal_input(goal_data)
    if not is_valid:
        return False, None, errors

    existing = get_goal_by_id(goal_id, user_id=user_id, db_path=db_path)
    if not existing:
        return False, None, [f"Goal with ID {goal_id} not found."]

    target_date_str = str(goal_data["target_date"]).strip()
    if isinstance(goal_data["target_date"], (date, datetime)):
        target_date_str = goal_data["target_date"].strftime("%Y-%m-%d")

    category = str(goal_data.get("category") or existing.get("category", "Other")).strip()
    priority = str(goal_data.get("priority") or existing.get("priority", "Medium")).strip().capitalize()
    target_amount = float(goal_data["target_amount"])
    current_amount = float(goal_data.get("current_amount", existing.get("current_amount", 0.0)) or 0.0)
    monthly_contribution = float(
        goal_data.get("monthly_contribution", existing.get("monthly_contribution", 0.0)) or 0.0
    )
    is_completed = (
        1 if (goal_data.get("is_completed") or current_amount >= target_amount) else 0
    )
    now_str = datetime.now().isoformat()

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE financial_goals SET
                name = ?,
                category = ?,
                target_amount = ?,
                target_date = ?,
                current_amount = ?,
                monthly_contribution = ?,
                priority = ?,
                is_completed = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                str(goal_data["name"]).strip(),
                category,
                target_amount,
                target_date_str,
                current_amount,
                monthly_contribution,
                priority,
                is_completed,
                now_str,
                goal_id,
            ),
        )
        conn.commit()

    updated = get_goal_by_id(goal_id, user_id=user_id, db_path=db_path)
    return True, updated, []


def mark_goal_completed(
    goal_id: int, is_completed: bool, user_id: str = "default_user", db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Mark a goal as completed or re-open it."""
    existing = get_goal_by_id(goal_id, user_id=user_id, db_path=db_path)
    if not existing:
        return None

    val = 1 if is_completed else 0
    now_str = datetime.now().isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE financial_goals SET is_completed = ?, updated_at = ? WHERE id = ?",
            (val, now_str, goal_id),
        )
        conn.commit()

    return get_goal_by_id(goal_id, user_id=user_id, db_path=db_path)


def delete_goal(
    goal_id: int, user_id: str = "default_user", db_path: Optional[str] = None
) -> bool:
    """Delete a goal by ID after confirming ownership."""
    existing = get_goal_by_id(goal_id, user_id=user_id, db_path=db_path)
    if not existing:
        return False

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM financial_goals WHERE id = ?", (goal_id,))
        conn.commit()
    return True


def get_available_monthly_surplus(
    user_id: str = "default_user", db_path: Optional[str] = None
) -> Tuple[Optional[float], bool, str]:
    """
    Retrieve user's available monthly surplus from Financial Planning/Profile.
    Returns (surplus_amount, has_data, status_message).
    """
    plan = generate_active_plan(user_id=user_id, db_path=db_path)
    if plan and plan.get("has_profile") and plan.get("summary"):
        surplus = plan["summary"].get("monthly_surplus", 0.0)
        return float(surplus), True, "Calculated from Financial Planning & Budgeting"

    profile = get_profile(user_id=user_id, db_path=db_path)
    if profile and profile.get("monthly_income") is not None:
        inc = float(profile.get("monthly_income") or 0.0)
        exp = (
            float(profile.get("essential_expenses") or 0.0)
            + float(profile.get("discretionary_expenses") or 0.0)
            + float(profile.get("other_expenses") or 0.0)
            + float(profile.get("monthly_debt_repayment") or 0.0)
        )
        return inc - exp, True, "Calculated from Financial Profile"

    return None, False, "Financial profile or budget data is missing. Monthly surplus unknown."


def evaluate_goal_planning_overview(
    user_id: str = "default_user",
    assumed_annual_return: Optional[float] = None,
    annual_inflation_rate: float = 0.0,
    contribution_timing: str = "end_of_period",
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Produce complete goal planning analysis for the user.
    Integrates feasibility, portfolio-level surplus allocation, risk classification,
    deterministic investment growth projections, and asset allocation policies.
    """
    goals = get_user_goals(user_id=user_id, db_path=db_path)
    surplus, has_surplus, surplus_msg = get_available_monthly_surplus(user_id=user_id, db_path=db_path)
    risk_info = get_latest_risk_assessment(user_id=user_id, db_path=db_path)

    risk_class = risk_info.get("classification") if risk_info else None
    capacity_score = risk_info.get("capacity_score") if risk_info else None
    tolerance_score = risk_info.get("tolerance_score") if risk_info else None

    # Evaluate portfolio-level feasibility & priority allocation
    portfolio_res = evaluate_goals_portfolio(goals=goals, available_surplus=surplus)

    enriched_goals: List[Dict[str, Any]] = []
    for g_eval in portfolio_res["evaluated_goals"]:
        g_id = g_eval.get("id")
        rem_months = g_eval["remaining_months"]
        cur_amt = g_eval["current_amount"]
        planned_pmt = g_eval["monthly_planned"]
        req_pmt = g_eval["required_monthly"]
        target_amt = g_eval["target_amount"]

        # Asset allocation based on horizon, risk classification & capacity
        allocation_res = generate_goal_asset_allocation(
            remaining_months=rem_months,
            risk_classification=risk_class,
            capacity_score=capacity_score,
            tolerance_score=tolerance_score,
            is_deficit=(surplus is not None and surplus < 0),
            goal_priority=g_eval.get("priority", "Medium"),
        )

        # Assumed return: use caller's parameter or the weighted expected return from allocation
        est_return = (
            assumed_annual_return
            if assumed_annual_return is not None
            else allocation_res["expected_return_benchmark"]
        )

        # Deterministic Investment Projection using Planned Contribution
        pmt_to_project = planned_pmt if planned_pmt > 0 else req_pmt
        projection = project_investment_growth(
            current_savings=cur_amt,
            monthly_contribution=pmt_to_project,
            remaining_months=rem_months,
            assumed_annual_return=est_return,
            contribution_timing=contribution_timing,
            annual_inflation_rate=annual_inflation_rate,
        )

        # Required contribution under assumed return
        growth_req_contrib = calculate_required_contribution_for_target(
            target_amount=target_amt,
            current_savings=cur_amt,
            remaining_months=rem_months,
            assumed_annual_return=est_return,
            contribution_timing=contribution_timing,
        )

        # Alerts and comparison
        projected_fv = projection["future_value"]
        shortfall_vs_projected = max(0.0, target_amt - projected_fv)
        surplus_vs_projected = max(0.0, projected_fv - target_amt)

        goal_alerts = list(g_eval.get("alerts", []))

        # 1. Projected shortfall alert
        if shortfall_vs_projected > 0 and not g_eval.get("is_completed") and not g_eval.get("is_expired") and rem_months > 0:
            growth_req = growth_req_contrib["required_monthly_contribution"]
            goal_alerts.append({
                "level": "warning",
                "title": "Projected Growth Shortfall",
                "message": (
                    f"At your planned contribution of ₹{pmt_to_project:,.0f}/mo and an assumed {est_return:.1f}% return, "
                    f"the projected corpus (₹{projected_fv:,.0f}) will fall short of the target (₹{target_amt:,.0f}) by ₹{shortfall_vs_projected:,.0f}. "
                    f"A monthly SIP of ₹{growth_req:,.0f} is required under this return assumption (or ₹{req_pmt:,.0f}/mo at 0% return)."
                ),
            })

        # 2. Relying on market returns for essential (High-priority) goal
        if (
            g_eval.get("priority") == "High"
            and planned_pmt > 0
            and planned_pmt < req_pmt
            and projected_fv >= target_amt
            and not g_eval.get("is_completed")
        ):
            goal_alerts.append({
                "level": "warning",
                "title": "Market Reliance for Essential Goal",
                "message": (
                    f"Your planned contribution (₹{planned_pmt:,.0f}/mo) is below the 0%-return requirement (₹{req_pmt:,.0f}/mo) and relies on "
                    f"{est_return:.1f}% annual market growth to reach this High-priority goal. If market returns fall short near your target date, "
                    "a funding deficit will occur. Consider increasing guaranteed savings or adjusting the target timeline."
                ),
            })

        # 3. Short horizon with higher assumed return
        if rem_months > 0 and rem_months <= 36 and est_return > 7.5 and not g_eval.get("is_completed"):
            goal_alerts.append({
                "level": "info",
                "title": "Short-Horizon Return Assumption",
                "message": (
                    f"For a short timeline of {rem_months} months (< 3 years), relying on higher returns ({est_return:.1f}%) introduces sequence-of-returns "
                    "risk. Educational frameworks prioritize capital preservation (fixed deposits and liquid reserves) over market growth for near-term needs."
                ),
            })

        enriched = {
            **g_eval,
            "asset_allocation": allocation_res,
            "projection": projection,
            "growth_required_monthly": growth_req_contrib["required_monthly_contribution"],
            "projected_future_value": projected_fv,
            "projected_shortfall": shortfall_vs_projected,
            "projected_surplus": surplus_vs_projected,
            "assumed_annual_return": est_return,
            "alerts": goal_alerts,
        }
        enriched_goals.append(enriched)

    portfolio_alerts = list(portfolio_res.get("portfolio_alerts", []))

    # Profile checks for emergency fund adequacy and unserviced debt
    profile = get_profile(user_id=user_id, db_path=db_path)
    if profile:
        essential = float(profile.get("essential_expenses") or 0.0)
        liquid = float(profile.get("savings_liquid") or 0.0)
        debt = float(profile.get("outstanding_debt") or 0.0)
        debt_repay = float(profile.get("monthly_debt_repayment") or 0.0)

        if essential > 0 and liquid < (3 * essential) and goals:
            months_covered = round(liquid / essential, 1)
            portfolio_alerts.append({
                "level": "warning",
                "title": "Emergency Savings Adequacy",
                "message": (
                    f"You currently have approximately {months_covered} months of essential living expenses saved in liquid cash "
                    f"(₹{liquid:,.0f} vs ₹{3 * essential:,.0f} recommended for 3 months). Building an emergency cushion is advised "
                    "before committing full surplus to long-term illiquid investments."
                ),
            })

        if debt > 0 and debt_repay == 0 and goals:
            portfolio_alerts.append({
                "level": "warning",
                "title": "Unserviced Outstanding Debt",
                "message": (
                    f"You have ₹{debt:,.0f} in outstanding debt with ₹0 monthly repayment recorded. "
                    "Servicing debt obligations should take precedence over speculative goal investments."
                ),
            })

    return {
        "user_id": user_id,
        "has_surplus_data": has_surplus,
        "available_monthly_surplus": surplus,
        "surplus_source_message": surplus_msg,
        "risk_classification": risk_class or "Not Assessed (Defaulting to Moderate)",
        "capacity_score": capacity_score,
        "tolerance_score": tolerance_score,
        "portfolio_summary": portfolio_res["summary"],
        "portfolio_alerts": portfolio_alerts,
        "goals": enriched_goals,
    }
