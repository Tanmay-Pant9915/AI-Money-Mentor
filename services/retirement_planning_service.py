"""
services/retirement_planning_service.py
Service layer for Retirement & FIRE Planning in AI Money Mentor.
Integrates user financial profile, budgeting surplus, investments, and risk classifications;
orchestrates deterministic calculations for inflation-adjusted expenses, corpus targets,
accumulation projections, required monthly contributions, and FIRE timelines;
and provides robust persistence for saved retirement plans.
"""
from datetime import datetime
import json
from typing import Any, Dict, List, Optional, Tuple

from data.database import get_connection, init_db
from services.goal_planning_service import get_user_goals
from services.profile_service import format_inr, get_profile
from services.risk_profile_service import get_latest_risk_assessment
from utils.fire_calculator import (
    calculate_fire_corpus,
    calculate_fire_timeline,
    calculate_savings_rate_table,
    calculate_target_fire_age_analysis,
)
from utils.retirement_calculator import (
    calculate_inflation_adjusted_expenses,
    calculate_required_monthly_contribution,
    calculate_retirement_accumulation,
    calculate_retirement_corpus,
)


def _get_active_budget_surplus(
    user_id: str = "default_user", db_path: Optional[str] = None
) -> Optional[float]:
    """Retrieve monthly surplus from saved financial plan table without heavy imports."""
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


def get_user_retirement_context(
    user_id: str = "default_user", db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve user's existing financial information to automatically populate
    retirement planning defaults without re-asking questions.
    """
    init_db(db_path)
    profile = get_profile(user_id=user_id, db_path=db_path)
    plan_surplus = _get_active_budget_surplus(user_id=user_id, db_path=db_path)
    goals = get_user_goals(user_id=user_id, db_path=db_path)
    risk_info = get_latest_risk_assessment(user_id=user_id, db_path=db_path)

    has_profile = profile is not None and bool(profile.get("name"))

    current_age = int(profile.get("age", 30)) if profile else 30
    monthly_income = float(profile.get("monthly_income", 100000.0)) if profile else 100000.0
    essential_exp = float(profile.get("essential_expenses", 40000.0)) if profile else 40000.0
    discretionary_exp = float(profile.get("discretionary_expenses", 15000.0)) if profile else 15000.0
    total_living_expenses = essential_exp + discretionary_exp

    # Check existing investments
    liquid = float(profile.get("savings_liquid", 0.0)) if profile else 0.0
    investments = float(profile.get("existing_investments", 0.0)) if profile else 0.0
    total_invested = investments + liquid

    # Check if a dedicated 'Retirement' goal exists
    retire_goal = next((g for g in goals if str(g.get("category", "")).lower() == "retirement"), None)
    goal_saved = float(retire_goal.get("current_amount", 0.0)) if retire_goal else 0.0
    goal_contrib = float(retire_goal.get("monthly_contribution", 0.0)) if retire_goal else 0.0

    current_corpus = max(total_invested, goal_saved)

    # Monthly surplus from budget
    if plan_surplus is not None:
        monthly_surplus = plan_surplus
    elif profile:
        monthly_surplus = float(profile.get("metrics", {}).get("monthly_surplus", 0.0))
    else:
        monthly_surplus = 35000.0

    monthly_contrib = goal_contrib if goal_contrib > 0 else max(0.0, monthly_surplus * 0.5)

    # Risk-adjusted return assumptions
    risk_class = risk_info.get("classification") if risk_info else "Moderate"
    if risk_class == "Conservative":
        pre_ret_return = 8.5
        post_ret_return = 6.5
    elif risk_class == "Aggressive":
        pre_ret_return = 12.0
        post_ret_return = 7.5
    else:  # Moderate
        pre_ret_return = 10.0
        post_ret_return = 7.0

    # Default expected expenses in retirement: ~80% of current living expenses
    est_retirement_monthly_exp = round(total_living_expenses * 0.8, 2) if total_living_expenses > 0 else 40000.0

    return {
        "user_id": user_id,
        "has_profile": has_profile,
        "name": profile.get("name", "Investor") if profile else "Investor",
        "current_age": current_age,
        "target_retirement_age": max(current_age + 5, 60),
        "planning_age": 85,
        "current_corpus": round(current_corpus, 2),
        "monthly_income": round(monthly_income, 2),
        "monthly_expenses_today": round(est_retirement_monthly_exp, 2),
        "current_living_expenses_today": round(total_living_expenses, 2),
        "monthly_contribution": round(monthly_contrib, 2),
        "available_monthly_surplus": round(monthly_surplus, 2),
        "annual_inflation_rate": 6.0,
        "pre_retirement_return": pre_ret_return,
        "post_retirement_return": post_ret_return,
        "safe_withdrawal_rate": 4.0,
        "fire_safe_withdrawal_rate": 3.5,
        "target_fire_age": min(max(current_age + 5, 50), max(current_age + 5, 60)),
        "monthly_pension": 0.0,
        "is_pension_inflation_indexed": False,
        "risk_classification": risk_class,
    }


def validate_retirement_inputs(inputs: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate retirement planning inputs and age constraints."""
    errors: List[str] = []

    cur_age = inputs.get("current_age")
    ret_age = inputs.get("target_retirement_age")
    plan_age = inputs.get("planning_age", 85)

    if cur_age is None or not isinstance(cur_age, (int, float)) or cur_age < 18 or cur_age > 100:
        errors.append("Current age must be between 18 and 100 years.")
    if ret_age is None or not isinstance(ret_age, (int, float)) or ret_age < 18 or ret_age > 110:
        errors.append("Target retirement age must be between 18 and 110 years.")
    if cur_age is not None and ret_age is not None and ret_age <= cur_age:
        errors.append("Target retirement age must be greater than current age.")
    if plan_age is not None and ret_age is not None and plan_age <= ret_age:
        errors.append("Planning age (life expectancy) must be greater than retirement age.")

    exp = inputs.get("monthly_expenses_today")
    if exp is None or float(exp or 0.0) <= 0.0:
        errors.append("Expected monthly expenses in retirement must be greater than ₹0.")

    corpus = inputs.get("current_corpus", 0.0)
    if float(corpus or 0.0) < 0.0:
        errors.append("Current retirement corpus cannot be negative.")

    contrib = inputs.get("monthly_contribution", 0.0)
    if float(contrib or 0.0) < 0.0:
        errors.append("Monthly contribution cannot be negative.")

    return len(errors) == 0, errors


def evaluate_retirement_and_fire_plan(
    inputs: Dict[str, Any], user_id: str = "default_user", db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run comprehensive deterministic retirement and FIRE calculations.
    Combines inflation projections, corpus requirements, accumulation models,
    required contributions, budget affordability, and FIRE timeline evaluation.
    """
    is_valid, validation_errors = validate_retirement_inputs(inputs)
    if not is_valid:
        return {
            "is_valid": False,
            "errors": validation_errors,
        }

    cur_age = int(inputs["current_age"])
    ret_age = int(inputs["target_retirement_age"])
    plan_age = int(inputs.get("planning_age", 85))
    years_to_ret = max(0.0, float(ret_age - cur_age))
    ret_duration = max(1, plan_age - ret_age)

    mo_exp_today = float(inputs["monthly_expenses_today"])
    inf_rate = float(inputs.get("annual_inflation_rate", 6.0))
    pre_return = float(inputs.get("pre_retirement_return", 10.0))
    post_return = float(inputs.get("post_retirement_return", 7.0))
    swr = float(inputs.get("safe_withdrawal_rate", 4.0))
    fire_swr = float(inputs.get("fire_safe_withdrawal_rate", 3.5))
    cur_corpus = float(inputs.get("current_corpus", 0.0))
    mo_contrib = float(inputs.get("monthly_contribution", 0.0))
    mo_pension = float(inputs.get("monthly_pension", 0.0))
    ann_pension = mo_pension * 12.0
    pension_indexed = bool(inputs.get("is_pension_inflation_indexed", False))
    surplus = inputs.get("available_monthly_surplus")

    # 1. Inflation-Adjusted Expenses
    exp_calc = calculate_inflation_adjusted_expenses(
        monthly_expenses_today=mo_exp_today,
        annual_inflation_rate=inf_rate,
        years_until_retirement=years_to_ret,
    )
    future_ann_exp = exp_calc["annual_expenses_at_retirement"]
    future_mo_exp = exp_calc["monthly_expenses_at_retirement"]

    # 2. Target Retirement Corpus (Simplified & Detailed with Pension)
    corpus_calc = calculate_retirement_corpus(
        annual_expenses_at_retirement=future_ann_exp,
        retirement_duration_years=ret_duration,
        post_retirement_annual_return=post_return,
        annual_inflation_rate=inf_rate,
        annual_pension_at_retirement=ann_pension,
        is_pension_inflation_indexed=pension_indexed,
        safe_withdrawal_rate=swr,
    )
    target_corpus = corpus_calc["recommended_target_corpus"]

    # 3. Accumulation at Retirement
    accum_calc = calculate_retirement_accumulation(
        current_corpus=cur_corpus,
        monthly_contribution=mo_contrib,
        years_until_retirement=years_to_ret,
        assumed_annual_return=pre_return,
    )
    projected_corpus = accum_calc["future_value"]

    # 4. Required Monthly Contribution
    req_contrib_calc = calculate_required_monthly_contribution(
        target_corpus=target_corpus,
        current_corpus=cur_corpus,
        years_until_retirement=years_to_ret,
        assumed_annual_return=pre_return,
    )
    required_monthly = req_contrib_calc["required_monthly_contribution"]

    # 5. Gap / Surplus Analysis
    corpus_gap = round(target_corpus - projected_corpus, 2)
    is_corpus_funded = corpus_gap <= 0.0
    surplus_or_shortfall = round(projected_corpus - target_corpus, 2)

    # 6. Affordability Evaluation
    is_affordable = True
    affordability_status = "Affordable"
    if surplus is not None:
        surplus_val = float(surplus)
        if surplus_val <= 0:
            is_affordable = False
            affordability_status = "Cash Flow Deficit"
        elif surplus_val < required_monthly:
            is_affordable = False
            affordability_status = "Contribution Shortfall"
        else:
            is_affordable = True
            affordability_status = "Affordable"

    # 7. FIRE Analysis
    ann_exp_today = mo_exp_today * 12.0
    fire_corpus_info = calculate_fire_corpus(
        annual_expenses_today=ann_exp_today,
        safe_withdrawal_rate=fire_swr,
        years_to_fire=years_to_ret,
        annual_inflation_rate=inf_rate,
    )

    fire_timeline = calculate_fire_timeline(
        current_age=cur_age,
        current_invested_assets=cur_corpus,
        monthly_investment_contribution=mo_contrib,
        annual_expenses_today=ann_exp_today,
        assumed_annual_return=pre_return,
        annual_inflation_rate=inf_rate,
        safe_withdrawal_rate=fire_swr,
    )

    # Specific Target FIRE Age Analysis
    target_fire_age_val = inputs.get("target_fire_age")
    if target_fire_age_val is not None:
        target_fire_age = int(target_fire_age_val)
    else:
        target_fire_age = min(ret_age, max(cur_age + 5, 50))

    target_fire_analysis = calculate_target_fire_age_analysis(
        current_age=cur_age,
        current_invested_assets=cur_corpus,
        monthly_investment_contribution=mo_contrib,
        annual_expenses_today=ann_exp_today,
        target_fire_age=target_fire_age,
        assumed_annual_return=pre_return,
        annual_inflation_rate=inf_rate,
        safe_withdrawal_rate=fire_swr,
    )

    # Savings rate table and current savings rate
    monthly_inc = float(inputs.get("monthly_income", 100000.0))
    current_savings_rate = round((mo_contrib / monthly_inc) * 100.0, 1) if monthly_inc > 0 else 0.0
    savings_table = calculate_savings_rate_table(
        monthly_income=monthly_inc,
        current_age=cur_age,
        current_invested_assets=cur_corpus,
        assumed_annual_return=pre_return,
        annual_inflation_rate=inf_rate,
        safe_withdrawal_rate=fire_swr,
    )

    # 8. Deterministic Alerts & Warnings
    alerts: List[Dict[str, str]] = []

    if years_to_ret <= 0:
        alerts.append({
            "level": "warning",
            "title": "Retirement Date Reached",
            "message": "Your target retirement age is equal to or less than your current age. Regular accumulation projections are not applicable.",
        })

    if not is_corpus_funded and required_monthly > 0:
        alerts.append({
            "level": "warning",
            "title": "Projected Corpus Shortfall",
            "message": (
                f"At your planned contribution of ₹{mo_contrib:,.0f}/mo, your projected corpus (₹{projected_corpus:,.0f}) falls short "
                f"of the target (₹{target_corpus:,.0f}) by ₹{abs(corpus_gap):,.0f}. Increasing contributions to ₹{required_monthly:,.0f}/mo "
                "or adjusting the retirement age is recommended."
            ),
        })

    if surplus is not None and float(surplus) < required_monthly and required_monthly > 0:
        alerts.append({
            "level": "error" if float(surplus) <= 0 else "warning",
            "title": "Monthly Contribution Unaffordable",
            "message": (
                f"Required contribution (₹{required_monthly:,.0f}/mo) exceeds your available monthly surplus (₹{float(surplus):,.0f}/mo). "
                "Rebalancing essential and discretionary expenses in your budget will improve retirement readiness."
            ),
        })

    if post_return <= inf_rate:
        alerts.append({
            "level": "info",
            "title": "Negative or Zero Real Return in Retirement",
            "message": (
                f"Your post-retirement return assumption ({post_return:.1f}%) is less than or equal to inflation ({inf_rate:.1f}%). "
                "The portfolio will experience purchasing power decay unless asset allocation includes moderate growth elements."
            ),
        })

    if fire_timeline["is_feasible"] and fire_timeline.get("fire_age") and fire_timeline["fire_age"] < ret_age:
        alerts.append({
            "level": "success",
            "title": "Early Financial Independence Achievable",
            "message": (
                f"At your current investment pace, you can achieve FIRE by age {fire_timeline['fire_age']:.0f} "
                f"({fire_timeline['years_to_fire']:.1f} years), ahead of your traditional retirement age {ret_age}."
            ),
        })
    elif not fire_timeline["is_feasible"]:
        alerts.append({
            "level": "info",
            "title": "Extended FIRE Horizon",
            "message": "FIRE is not projected before age 100 under current savings rates. Increasing savings rate or optimizing living expenses will accelerate freedom.",
        })

    return {
        "is_valid": True,
        "inputs": inputs,
        "current_age": cur_age,
        "target_retirement_age": ret_age,
        "planning_age": plan_age,
        "years_until_retirement": years_to_ret,
        "retirement_duration_years": ret_duration,
        "monthly_expenses_today": mo_exp_today,
        "annual_expenses_today": mo_exp_today * 12.0,
        "inflation_rate": inf_rate,
        "pre_retirement_return": pre_return,
        "post_retirement_return": post_return,
        "safe_withdrawal_rate": swr,
        "fire_safe_withdrawal_rate": fire_swr,
        "current_corpus": cur_corpus,
        "monthly_contribution": mo_contrib,
        "available_monthly_surplus": surplus,
        "affordability_status": affordability_status,
        "is_affordable": is_affordable,
        "expense_projection": exp_calc,
        "future_monthly_expenses": future_mo_exp,
        "future_annual_expenses": future_ann_exp,
        "corpus_calculation": corpus_calc,
        "target_corpus": target_corpus,
        "simplified_target_corpus": corpus_calc["simplified_corpus"],
        "detailed_target_corpus": corpus_calc["detailed_corpus"],
        "accumulation": accum_calc,
        "projected_corpus": projected_corpus,
        "is_corpus_funded": is_corpus_funded,
        "corpus_gap": corpus_gap,
        "surplus_or_shortfall": surplus_or_shortfall,
        "required_contribution": req_contrib_calc,
        "required_monthly_contribution": required_monthly,
        "fire_corpus_info": fire_corpus_info,
        "fire_timeline": fire_timeline,
        "target_fire_age": target_fire_age,
        "target_fire_analysis": target_fire_analysis,
        "current_savings_rate": current_savings_rate,
        "savings_rate_table": savings_table,
        "alerts": alerts,
    }


def save_retirement_plan(
    plan_data: Dict[str, Any], user_id: str = "default_user", db_path: Optional[str] = None
) -> Tuple[bool, Optional[int], List[str]]:
    """Save an evaluated retirement plan to the database idempotently, preserving history."""
    init_db(db_path)
    inputs = plan_data.get("inputs", {})
    now_str = datetime.now().isoformat()

    try:
        details_json = json.dumps(plan_data)
    except Exception as e:
        return False, None, [f"Serialization error: {str(e)}"]

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Mark previous plans as non-latest
        cursor.execute("UPDATE retirement_plans SET is_latest = 0 WHERE user_id = ?", (user_id,))

        cursor.execute(
            """
            INSERT INTO retirement_plans (
                user_id, plan_name, created_at, current_age, target_retirement_age,
                planning_age, current_corpus, monthly_contribution, monthly_expenses_today,
                inflation_rate, pre_retirement_return, post_retirement_return, withdrawal_rate,
                monthly_pension, is_pension_inflation_indexed, target_corpus, projected_corpus,
                required_monthly, estimated_fire_age, years_to_fire, plan_details_json, is_latest
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                user_id,
                str(inputs.get("plan_name") or "Retirement & FIRE Plan").strip(),
                now_str,
                int(inputs.get("current_age", 30)),
                int(inputs.get("target_retirement_age", 60)),
                int(inputs.get("planning_age", 85)),
                float(inputs.get("current_corpus", 0.0)),
                float(inputs.get("monthly_contribution", 0.0)),
                float(inputs.get("monthly_expenses_today", 0.0)),
                float(inputs.get("annual_inflation_rate", 6.0)),
                float(inputs.get("pre_retirement_return", 10.0)),
                float(inputs.get("post_retirement_return", 7.0)),
                float(inputs.get("safe_withdrawal_rate", 4.0)),
                float(inputs.get("monthly_pension", 0.0)),
                1 if inputs.get("is_pension_inflation_indexed") else 0,
                float(plan_data.get("target_corpus", 0.0)),
                float(plan_data.get("projected_corpus", 0.0)),
                float(plan_data.get("required_monthly_contribution", 0.0)),
                plan_data.get("fire_timeline", {}).get("fire_age"),
                plan_data.get("fire_timeline", {}).get("years_to_fire"),
                details_json,
            ),
        )
        new_id = cursor.lastrowid
        conn.commit()

    return True, new_id, []


def get_latest_saved_plan(
    user_id: str = "default_user", db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Retrieve the most recent saved retirement plan for the user."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM retirement_plans
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


def get_saved_plans_history(
    user_id: str = "default_user", db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve full history of saved retirement plans."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, plan_name, created_at, current_age, target_retirement_age,
                   target_corpus, projected_corpus, required_monthly, is_latest
            FROM retirement_plans
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def delete_saved_plan(
    plan_id: int, user_id: str = "default_user", db_path: Optional[str] = None
) -> bool:
    """Delete a saved retirement plan by ID."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM retirement_plans WHERE id = ? AND user_id = ?", (plan_id, user_id))
        conn.commit()
    return True
