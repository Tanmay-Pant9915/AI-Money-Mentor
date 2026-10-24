"""
services/financial_planning_service.py
Service layer for orchestrating financial profile retrieval, deterministic budgeting,
scenario adjustments, plan persistence, and historical tracking.
"""
from datetime import datetime
import json
from typing import Any, Dict, List, Optional

from data.database import get_connection, init_db
from services.money_health_service import get_latest_health_score
from services.profile_service import get_profile
from services.risk_profile_service import get_latest_risk_assessment
from utils.ai_financial_planner import generate_plan_explanation
from utils.budget_calculator import (
    calculate_financial_summary,
    calculate_goal_contributions,
    generate_budget_recommendations,
)
from utils.financial_recommendations import generate_prioritized_financial_actions


def get_financial_plan_inputs(
    user_id: str = "default_user",
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve all financial context for planning from the persistence layer."""
    init_db(db_path)
    profile = get_profile(user_id=user_id, db_path=db_path)
    risk_assessment = get_latest_risk_assessment(user_id=user_id, db_path=db_path)
    health_score = get_latest_health_score(user_id=user_id, db_path=db_path)
    goals = profile.get("goals", []) if profile else []

    return {
        "profile": profile,
        "goals": goals,
        "risk_assessment": risk_assessment,
        "health_score": health_score,
    }


def generate_active_plan(
    user_id: str = "default_user",
    custom_overrides: Optional[Dict[str, float]] = None,
    db_path: Optional[str] = None,
    debt_already_in_expenses: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Generate an authoritative, deterministic financial plan.
    Supports user adjustments in memory without altering underlying profile records.
    """
    inputs = get_financial_plan_inputs(user_id=user_id, db_path=db_path)
    profile = inputs["profile"]

    if not profile or not profile.get("monthly_income"):
        return {
            "has_profile": False,
            "message": "Financial Profile is missing or has no income recorded. Complete your profile first.",
            "inputs": inputs,
            "summary": calculate_financial_summary(profile, debt_already_in_expenses=debt_already_in_expenses),
            "budget": {},
            "adjusted_budget": {},
            "actions": [],
        }

    goals = inputs["goals"]
    risk = inputs["risk_assessment"]
    health = inputs["health_score"]

    summary = calculate_financial_summary(profile, debt_already_in_expenses=debt_already_in_expenses)
    budget = generate_budget_recommendations(
        profile,
        goals=goals,
        risk_assessment=risk,
        health_score=health,
        debt_already_in_expenses=debt_already_in_expenses,
    )
    actions = generate_prioritized_financial_actions(summary, budget, budget.get("goals_allocation"), risk, health)

    # Compute adjusted budget if user customized allocations via UI
    rec_cats = budget.get("recommended_categories", {})
    adjusted_categories = {}
    for cat_name, cat_data in rec_cats.items():
        adjusted_categories[cat_name] = dict(cat_data)

    if custom_overrides:
        income = summary["monthly_income"]
        fixed_obligations = (
            rec_cats.get("Essential Living", {}).get("recommended", 0.0)
            + rec_cats.get("Other Expenses", {}).get("recommended", 0.0)
            + rec_cats.get("Debt Repayment", {}).get("recommended", 0.0)
        )

        if "Discretionary Living" in custom_overrides:
            val = max(0.0, float(custom_overrides["Discretionary Living"]))
            adjusted_categories["Discretionary Living"]["adjusted"] = round(val, 2)
            adjusted_categories["Discretionary Living"]["diff_from_rec"] = round(
                val - rec_cats["Discretionary Living"]["recommended"], 2
            )
        else:
            adjusted_categories["Discretionary Living"]["adjusted"] = rec_cats["Discretionary Living"]["recommended"]
            adjusted_categories["Discretionary Living"]["diff_from_rec"] = 0.0

        current_disc = adjusted_categories["Discretionary Living"]["adjusted"]
        usable_for_savings = max(0.0, income - (fixed_obligations + current_disc))

        # Adjust emergency savings
        if "Emergency Savings" in custom_overrides:
            emg_val = min(usable_for_savings, max(0.0, float(custom_overrides["Emergency Savings"])))
            adjusted_categories["Emergency Savings"]["adjusted"] = round(emg_val, 2)
        else:
            emg_val = min(usable_for_savings, rec_cats.get("Emergency Savings", {}).get("recommended", 0.0))
            adjusted_categories["Emergency Savings"]["adjusted"] = round(emg_val, 2)

        remaining_for_goals = max(0.0, usable_for_savings - emg_val)

        # Adjust goals
        if "Financial Goals" in custom_overrides:
            goals_val = min(remaining_for_goals, max(0.0, float(custom_overrides["Financial Goals"])))
            adjusted_categories["Financial Goals"]["adjusted"] = round(goals_val, 2)
        else:
            goals_val = min(remaining_for_goals, rec_cats.get("Financial Goals", {}).get("recommended", 0.0))
            adjusted_categories["Financial Goals"]["adjusted"] = round(goals_val, 2)

        # Remaining surplus goes to Long-Term Investments
        inv_val = max(0.0, remaining_for_goals - goals_val)
        adjusted_categories["Long-Term Investments"]["adjusted"] = round(inv_val, 2)
    else:
        for cat_name, data in adjusted_categories.items():
            data["adjusted"] = data.get("recommended", 0.0)
            data["diff_from_rec"] = 0.0

    return {
        "has_profile": True,
        "user_id": user_id,
        "summary": summary,
        "budget": budget,
        "adjusted_categories": adjusted_categories,
        "actions": actions,
        "inputs": inputs,
    }


def save_financial_plan(
    plan_data: Dict[str, Any],
    user_id: str = "default_user",
    plan_name: str = "Monthly Financial Plan",
    ai_explanation: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """
    Persist calculated financial plan snapshot and user-adjusted scenario in SQLite.
    Marks older plans for this user as is_latest=0.
    """
    init_db(db_path)
    now_str = datetime.now().isoformat()
    profile = plan_data.get("inputs", {}).get("profile") or {}
    profile_id = profile.get("id")

    input_snapshot = {
        "profile": profile,
        "risk_assessment": plan_data.get("inputs", {}).get("risk_assessment"),
        "health_score": plan_data.get("inputs", {}).get("health_score"),
        "saved_at": now_str,
    }

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        # Mark previous plans as not latest
        cursor.execute(
            "UPDATE financial_plans SET is_latest = 0 WHERE user_id = ?",
            (user_id,),
        )

        cursor.execute(
            """
            INSERT INTO financial_plans (
                user_id, profile_id, plan_name, created_at,
                input_snapshot_json, current_summary_json, recommended_budget_json,
                adjusted_budget_json, priorities_json, goals_allocation_json,
                ai_explanation, is_latest
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                user_id,
                profile_id,
                plan_name,
                now_str,
                json.dumps(input_snapshot, default=str),
                json.dumps(plan_data.get("summary", {}), default=str),
                json.dumps(plan_data.get("budget", {}), default=str),
                json.dumps(plan_data.get("adjusted_categories", {}), default=str),
                json.dumps(plan_data.get("actions", []), default=str),
                json.dumps(plan_data.get("budget", {}).get("goals_allocation", {}), default=str),
                ai_explanation,
            ),
        )
        plan_id = cursor.lastrowid
        conn.commit()

    return plan_id


import sqlite3


def get_latest_saved_plan(
    user_id: str = "default_user",
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieve the latest persisted financial plan for a user."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT * FROM financial_plans
                WHERE user_id = ? AND is_latest = 1
                ORDER BY id DESC LIMIT 1
                """,
                (user_id,),
            )
            row = cursor.fetchone()
        except sqlite3.OperationalError:
            init_db(db_path)
            try:
                cursor.execute(
                    """
                    SELECT * FROM financial_plans
                    WHERE user_id = ? AND is_latest = 1
                    ORDER BY id DESC LIMIT 1
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()
            except sqlite3.OperationalError:
                return None

        if not row:
            return None

        data = dict(row)
        try:
            input_snapshot = json.loads(data["input_snapshot_json"])
            summary = json.loads(data["current_summary_json"])
            budget = json.loads(data["recommended_budget_json"])
            adjusted = json.loads(data["adjusted_budget_json"])
            actions = json.loads(data["priorities_json"])
            goals = json.loads(data["goals_allocation_json"])
        except Exception:
            input_snapshot, summary, budget, adjusted, actions, goals = {}, {}, {}, {}, [], {}

        return {
            "id": data["id"],
            "user_id": data["user_id"],
            "profile_id": data["profile_id"],
            "plan_name": data["plan_name"],
            "created_at": data["created_at"],
            "input_snapshot": input_snapshot,
            "summary": summary,
            "budget": budget,
            "adjusted_categories": adjusted,
            "actions": actions,
            "goals_allocation": goals,
            "ai_explanation": data["ai_explanation"],
        }


def get_saved_plan_history(
    user_id: str = "default_user",
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve chronological list of historical saved plans."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, plan_name, created_at, is_latest
                FROM financial_plans
                WHERE user_id = ?
                ORDER BY created_at DESC, id DESC
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            init_db(db_path)
            try:
                cursor.execute(
                    """
                    SELECT id, plan_name, created_at, is_latest
                    FROM financial_plans
                    WHERE user_id = ?
                    ORDER BY created_at DESC, id DESC
                    """,
                    (user_id,),
                )
                rows = cursor.fetchall()
            except sqlite3.OperationalError:
                return []

        return [dict(r) for r in rows]
