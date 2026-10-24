"""
services/emergency_fund_service.py
Service layer for Emergency Fund Planning in AI Money Mentor.
Integrates user profile context, budget surplus, debt obligations,
orchestrates deterministic calculations, and manages SQLite persistence.
"""
from datetime import date, datetime
import json
from typing import Any, Dict, List, Optional, Tuple

from data.database import get_connection, init_db
from services.profile_service import format_inr, get_profile
from utils.emergency_fund_calculator import (
    calculate_completion_date,
    calculate_emergency_fund_coverage,
    calculate_emergency_fund_gap,
    calculate_emergency_fund_progress,
    calculate_emergency_fund_target,
    calculate_months_to_target,
    evaluate_contribution_scenarios,
    get_emergency_fund_status,
    recommend_monthly_contribution,
)


def _get_active_budget_surplus(
    user_id: str = "default_user", db_path: Optional[str] = None
) -> Optional[float]:
    """Retrieve monthly surplus from saved financial plan table if available."""
    try:
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT current_summary_json FROM financial_plans
                WHERE user_id = ? AND is_latest = 1
                ORDER BY id DESC LIMIT 1
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            if row and row["current_summary_json"]:
                summary = json.loads(row["current_summary_json"])
                if "monthly_surplus" in summary:
                    return float(summary["monthly_surplus"])
    except Exception:
        pass
    return None


def get_user_emergency_fund_context(
    user_id: str = "default_user", db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve user's financial profile and budget surplus to populate
    emergency fund defaults without re-asking questions.
    """
    init_db(db_path)
    profile = get_profile(user_id=user_id, db_path=db_path)
    plan_surplus = _get_active_budget_surplus(user_id=user_id, db_path=db_path)

    has_profile = profile is not None and bool(profile.get("name"))

    essential_exp = float(profile.get("essential_expenses", 35000.0)) if profile else 35000.0
    discretionary_exp = float(profile.get("discretionary_expenses", 15000.0)) if profile else 15000.0
    other_exp = float(profile.get("other_expenses", 0.0)) if profile else 0.0
    debt_emi = float(profile.get("monthly_debt_repayment", 0.0)) if profile else 0.0
    total_expenses = essential_exp + discretionary_exp + other_exp + debt_emi

    monthly_income = float(profile.get("monthly_income", 80000.0)) if profile else 80000.0
    liquid_savings = float(profile.get("savings_liquid", 0.0)) if profile else 0.0
    dependents = int(profile.get("dependents", 0)) if profile else 0
    emp_status = str(profile.get("employment_status", "Salaried Employee")) if profile else "Salaried Employee"

    # Monthly surplus
    if plan_surplus is not None:
        monthly_surplus = plan_surplus
    elif profile:
        monthly_surplus = float(profile.get("metrics", {}).get("monthly_surplus", monthly_income - total_expenses))
    else:
        monthly_surplus = max(0.0, monthly_income - total_expenses)

    # Sensible target months recommendation based on job stability, dependents, and debt:
    # - High risk/dependents: 9-12 months
    # - Moderate: 6 months
    # - Low risk (salaried, 0 dependents, no debt): 3-6 months
    if emp_status in ["Self-Employed", "Business Owner"] or dependents >= 2 or (monthly_income > 0 and (debt_emi / monthly_income) > 0.35):
        suggested_target_months = 9.0
    elif dependents >= 1 or debt_emi > 0:
        suggested_target_months = 6.0
    else:
        suggested_target_months = 6.0

    # Default contribution pace: 50% of surplus or 10% of income
    default_monthly_contrib = max(0.0, round(monthly_surplus * 0.5, 2)) if monthly_surplus > 0 else 0.0

    return {
        "user_id": user_id,
        "has_profile": has_profile,
        "name": profile.get("name", "Investor") if profile else "Investor",
        "monthly_income": round(monthly_income, 2),
        "essential_expenses": round(essential_exp, 2),
        "total_expenses": round(total_expenses, 2),
        "monthly_debt_repayment": round(debt_emi, 2),
        "current_liquid_savings": round(liquid_savings, 2),
        "dependents": dependents,
        "employment_status": emp_status,
        "available_monthly_surplus": round(monthly_surplus, 2),
        "target_months": suggested_target_months,
        "monthly_contribution": default_monthly_contrib,
    }


def validate_emergency_fund_inputs(inputs: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate emergency fund inputs."""
    errors: List[str] = []

    essential = inputs.get("essential_expenses")
    if essential is None or float(essential or 0.0) < 0.0:
        errors.append("Monthly essential expenses cannot be negative.")

    target_m = inputs.get("target_months")
    if target_m is None or float(target_m or 0.0) <= 0.0 or float(target_m or 0.0) > 36.0:
        errors.append("Target coverage must be between 1 and 36 months.")

    current_sav = inputs.get("current_liquid_savings", 0.0)
    if float(current_sav or 0.0) < 0.0:
        errors.append("Current liquid savings cannot be negative.")

    contrib = inputs.get("monthly_contribution", 0.0)
    if float(contrib or 0.0) < 0.0:
        errors.append("Monthly contribution cannot be negative.")

    return len(errors) == 0, errors


def evaluate_emergency_fund_plan(
    inputs: Dict[str, Any], user_id: str = "default_user", db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run comprehensive deterministic emergency fund planning calculations.
    """
    is_valid, errors = validate_emergency_fund_inputs(inputs)
    if not is_valid:
        return {"is_valid": False, "errors": errors}

    essential = float(inputs.get("essential_expenses", 0.0))
    target_months = float(inputs.get("target_months", 6.0))
    current_savings = float(inputs.get("current_liquid_savings", 0.0))
    monthly_contrib = float(inputs.get("monthly_contribution", 0.0))
    surplus = inputs.get("available_monthly_surplus")
    monthly_debt = float(inputs.get("monthly_debt_repayment", 0.0))

    # Core Calculations
    target_amount = calculate_emergency_fund_target(essential, target_months)
    coverage_months = calculate_emergency_fund_coverage(current_savings, essential)
    gap = calculate_emergency_fund_gap(target_amount, current_savings)
    progress_info = calculate_emergency_fund_progress(current_savings, target_amount)
    timing_info = calculate_months_to_target(gap, monthly_contrib)
    months_to_target = timing_info.get("months")
    completion_date = calculate_completion_date(months_to_target)

    status_info = get_emergency_fund_status(coverage_months, target_months)
    rec_contrib_info = recommend_monthly_contribution(
        available_surplus=float(surplus) if surplus is not None else None,
        gap=gap,
        monthly_debt=monthly_debt,
    )

    # Scenarios Comparison
    scenarios = evaluate_contribution_scenarios(
        gap=gap,
        available_surplus=float(surplus) if surplus is not None else None,
        scenarios=[2000.0, 5000.0, 10000.0, 20000.0],
    )

    # Deterministic Alerts
    alerts: List[Dict[str, str]] = []
    if essential <= 0:
        alerts.append({
            "level": "warning",
            "title": "Zero Essential Expenses",
            "message": "Monthly essential expenses are ₹0. Emergency fund calculations require non-zero essential living expenses.",
        })
    elif coverage_months < 1.0:
        alerts.append({
            "level": "error",
            "title": "Critical Cash Reserve Shortfall",
            "message": f"Your current liquid reserves cover {coverage_months:.1f} months. An immediate 1-month cash buffer of ₹{essential:,.0f} is recommended before aggressive investing.",
        })
    elif progress_info["is_target_reached"]:
        alerts.append({
            "level": "success",
            "title": "Emergency Fund Fully Funded",
            "message": f"Congratulations! Your liquid savings cover {coverage_months:.1f} months, exceeding your target of {target_months:.0f} months.",
        })

    if surplus is not None and float(surplus) < monthly_contrib and monthly_contrib > 0:
        alerts.append({
            "level": "warning",
            "title": "Contribution Exceeds Budget Surplus",
            "message": f"Your planned contribution (₹{monthly_contrib:,.0f}/mo) exceeds your available surplus (₹{float(surplus):,.0f}/mo). Adjust discretionary expenses to afford this contribution.",
        })

    return {
        "is_valid": True,
        "inputs": inputs,
        "essential_expenses": essential,
        "target_months": target_months,
        "target_amount": target_amount,
        "current_liquid_savings": current_savings,
        "coverage_months": coverage_months,
        "fund_gap": gap,
        "gap": gap,
        "progress_pct": progress_info["progress_pct"],
        "actual_pct": progress_info["actual_pct"],
        "is_target_reached": progress_info["is_target_reached"],
        "surplus_amount": progress_info["surplus_amount"],
        "monthly_contribution": monthly_contrib,
        "months_to_target": months_to_target,
        "completion_date": completion_date.strftime("%b %Y") if completion_date else "N/A",
        "status": status_info["status"],
        "tier": status_info["tier"],
        "badge": status_info["badge"],
        "color": status_info["color"],
        "description": status_info["description"],
        "next_action": status_info["next_action"],
        "recommendation_info": rec_contrib_info,
        "recommended_monthly": rec_contrib_info["recommended_monthly"],
        "contribution_scenarios": scenarios,
        "alerts": alerts,
    }


def save_emergency_fund_plan(
    plan_data: Dict[str, Any], user_id: str = "default_user", db_path: Optional[str] = None
) -> Tuple[bool, Optional[int], List[str]]:
    """Save an evaluated emergency fund plan to SQLite idempotently, preserving history."""
    init_db(db_path)
    inputs = plan_data.get("inputs", {})
    now_str = datetime.now().isoformat()

    try:
        details_json = json.dumps(plan_data)
    except Exception as e:
        return False, None, [f"Serialization error: {str(e)}"]

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE emergency_fund_plans SET is_latest = 0 WHERE user_id = ?", (user_id,))

        cursor.execute(
            """
            INSERT INTO emergency_fund_plans (
                user_id, plan_name, created_at, essential_expenses, target_months,
                target_amount, current_savings, fund_gap, coverage_months,
                monthly_contribution, estimated_months, status, plan_details_json, is_latest
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                user_id,
                str(inputs.get("plan_name") or f"Emergency Fund Plan ({plan_data.get('target_months', 6):.0f} Mo)").strip(),
                now_str,
                float(plan_data.get("essential_expenses", 0.0)),
                float(plan_data.get("target_months", 6.0)),
                float(plan_data.get("target_amount", 0.0)),
                float(plan_data.get("current_liquid_savings", 0.0)),
                float(plan_data.get("fund_gap", 0.0)),
                float(plan_data.get("coverage_months", 0.0)),
                float(plan_data.get("monthly_contribution", 0.0)),
                plan_data.get("months_to_target"),
                str(plan_data.get("status", "Building")),
                details_json,
            ),
        )
        new_id = cursor.lastrowid
        conn.commit()

    return True, new_id, []


def get_latest_emergency_fund_plan(
    user_id: str = "default_user", db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Retrieve the most recent saved emergency fund plan."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM emergency_fund_plans
            WHERE user_id = ? AND is_latest = 1
            ORDER BY id DESC LIMIT 1
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        res = dict(row)
        try:
            res["plan_details"] = json.loads(res["plan_details_json"])
        except Exception:
            res["plan_details"] = {}
        return res


def get_emergency_fund_history(
    user_id: str = "default_user", db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve full history of saved emergency fund plans."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, plan_name, created_at, essential_expenses, target_months,
                   target_amount, current_savings, fund_gap, coverage_months, status, is_latest
            FROM emergency_fund_plans
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def delete_emergency_fund_plan(
    plan_id: int, user_id: str = "default_user", db_path: Optional[str] = None
) -> bool:
    """Delete a saved emergency fund plan by ID."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM emergency_fund_plans WHERE id = ? AND user_id = ?", (plan_id, user_id))
        conn.commit()
    return True
