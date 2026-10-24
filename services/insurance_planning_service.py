"""
services/insurance_planning_service.py
Service layer for Insurance Needs Assessment in AI Money Mentor.
Integrates user profile (dependents, income, debt, goals), orchestrates
health, life, and personal accident calculations, and manages SQLite persistence.
"""
from datetime import datetime
import json
from typing import Any, Dict, List, Optional, Tuple

from data.database import get_connection, init_db
from services.goal_planning_service import get_user_goals
from services.profile_service import format_inr, get_profile
from utils.insurance_calculator import (
    calculate_health_insurance_gap,
    calculate_life_insurance_needs,
    evaluate_personal_accident_coverage,
)


def get_user_insurance_context(
    user_id: str = "default_user", db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve user's financial profile, goals, liabilities, and previous insurance
    data to populate insurance planning defaults without re-asking questions.
    """
    init_db(db_path)
    profile = get_profile(user_id=user_id, db_path=db_path)
    goals = get_user_goals(user_id=user_id, db_path=db_path)
    latest_saved = get_latest_insurance_assessment(user_id=user_id, db_path=db_path)

    has_profile = profile is not None and bool(profile.get("name"))

    age = int(profile.get("age", 30)) if profile else 30
    monthly_income = float(profile.get("monthly_income", 80000.0)) if profile else 80000.0
    annual_income = monthly_income * 12.0
    dependents = int(profile.get("dependents", 0)) if profile else 0
    debt = float(profile.get("outstanding_debt", 0.0)) if profile else 0.0
    savings_liquid = float(profile.get("savings_liquid", 0.0)) if profile else 0.0
    existing_investments = float(profile.get("existing_investments", 0.0)) if profile else 0.0
    emp_status = str(profile.get("employment_status", "Salaried Employee")) if profile else "Salaried Employee"

    # Sum goal targets committed for family/dependents (Education, Marriage, Family)
    family_goal_categories = ["education", "children", "child", "marriage", "family"]
    family_goals_sum = sum(
        float(g.get("target_amount", 0.0))
        for g in goals
        if any(cat in str(g.get("category", "")).lower() or cat in str(g.get("name", "")).lower() for cat in family_goal_categories)
    )

    # Defaults or previous saved choices
    prev_details = latest_saved.get("assessment_details", {}) if latest_saved else {}
    health_personal = float(prev_details.get("health_personal_cover", 0.0))
    health_employer = float(prev_details.get("health_employer_cover", 500000.0 if emp_status == "Salaried Employee" else 0.0))
    health_target = float(prev_details.get("health_target_cover", 1000000.0 if dependents > 0 else 500000.0))
    members_count = max(1, 1 + dependents)

    life_existing = float(prev_details.get("life_existing_cover", 0.0))
    income_multiplier = float(prev_details.get("life_income_multiplier_years", 10.0))
    has_accident = bool(prev_details.get("has_accident_disability_cover", False))
    accident_sum = float(prev_details.get("accident_cover_amount", 0.0))

    # Eligible assets that can support dependents (liquid savings + non-retirement investments)
    eligible_assets = round(savings_liquid + existing_investments, 2)

    return {
        "user_id": user_id,
        "has_profile": has_profile,
        "name": profile.get("name", "Investor") if profile else "Investor",
        "age": age,
        "employment_status": emp_status,
        "monthly_income": round(monthly_income, 2),
        "annual_income": round(annual_income, 2),
        "dependents": dependents,
        "outstanding_debt": round(debt, 2),
        "savings_liquid": round(savings_liquid, 2),
        "existing_investments": round(existing_investments, 2),
        "eligible_assets": eligible_assets,
        "family_goals_sum": round(family_goals_sum, 2),
        "number_of_members": members_count,
        # Health Insurance Defaults
        "health_personal_coverage": health_personal,
        "health_employer_coverage": health_employer,
        "health_target_coverage": health_target,
        "health_policy_type": "Family Floater" if dependents > 0 else "Individual",
        # Life Insurance Defaults
        "life_existing_coverage": life_existing,
        "life_income_multiplier_years": income_multiplier,
        "future_family_obligations": round(family_goals_sum, 2),
        # Accident Defaults
        "has_accident_disability_cover": has_accident,
        "accident_cover_amount": accident_sum,
    }


def validate_insurance_inputs(inputs: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate insurance assessment inputs."""
    errors: List[str] = []

    ann_inc = inputs.get("annual_income")
    if ann_inc is not None and float(ann_inc or 0.0) < 0.0:
        errors.append("Annual income cannot be negative.")

    h_target = inputs.get("health_target_coverage")
    if h_target is not None and float(h_target or 0.0) < 0.0:
        errors.append("Target health coverage cannot be negative.")

    mult = inputs.get("life_income_multiplier_years")
    if mult is not None and (float(mult or 0.0) < 0.0 or float(mult or 0.0) > 30.0):
        errors.append("Income replacement multiplier must be between 0 and 30 years.")

    return len(errors) == 0, errors


def evaluate_insurance_assessment(
    inputs: Dict[str, Any], user_id: str = "default_user", db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run comprehensive deterministic health, life, and personal accident evaluations.
    """
    is_valid, errors = validate_insurance_inputs(inputs)
    if not is_valid:
        return {"is_valid": False, "errors": errors}

    ann_income = float(inputs.get("annual_income", 0.0))
    deps = int(inputs.get("dependents", 0))
    liabilities = float(inputs.get("outstanding_debt", 0.0))
    family_obligations = float(inputs.get("future_family_obligations", 0.0))
    goals = float(inputs.get("family_goals_sum", 0.0))
    eligible_assets = float(inputs.get("eligible_assets", 0.0))

    # 1. Health Insurance Evaluation
    h_personal = float(inputs.get("health_personal_coverage", 0.0))
    h_employer = float(inputs.get("health_employer_coverage", 0.0))
    h_target = float(inputs.get("health_target_coverage", 1000000.0))
    members = int(inputs.get("number_of_members", max(1, 1 + deps)))
    pol_type = str(inputs.get("health_policy_type", "Family Floater" if deps > 0 else "Individual"))

    health_eval = calculate_health_insurance_gap(
        personal_coverage=h_personal,
        employer_coverage=h_employer,
        target_coverage=h_target,
        number_of_members=members,
        policy_type=pol_type,
    )

    # 2. Life Insurance Evaluation
    l_existing = float(inputs.get("life_existing_coverage", 0.0))
    l_multiplier = float(inputs.get("life_income_multiplier_years", 10.0))

    life_eval = calculate_life_insurance_needs(
        annual_income=ann_income,
        number_of_dependents=deps,
        income_replacement_years=l_multiplier,
        outstanding_liabilities=liabilities,
        future_family_obligations=family_obligations,
        specified_goals=goals,
        existing_eligible_assets=eligible_assets,
        existing_life_insurance=l_existing,
    )

    # 3. Personal Accident & Disability Evaluation
    has_acc = bool(inputs.get("has_accident_disability_cover", False))
    acc_amt = float(inputs.get("accident_cover_amount", 0.0))

    accident_eval = evaluate_personal_accident_coverage(
        annual_income=ann_income,
        has_accident_cover=has_acc,
        current_sum_insured=acc_amt,
    )

    return {
        "is_valid": True,
        "inputs": inputs,
        "annual_income": ann_income,
        "dependents": deps,
        "health_assessment": health_eval,
        "life_assessment": life_eval,
        "accident_assessment": accident_eval,
    }


def save_insurance_assessment(
    assessment_data: Dict[str, Any], user_id: str = "default_user", db_path: Optional[str] = None
) -> Tuple[bool, Optional[int], List[str]]:
    """Save an evaluated insurance assessment snapshot to SQLite idempotently."""
    init_db(db_path)
    inputs = assessment_data.get("inputs", {})
    now_str = datetime.now().isoformat()

    h_eval = assessment_data.get("health_assessment", {})
    l_eval = assessment_data.get("life_assessment", {})
    acc_eval = assessment_data.get("accident_assessment", {})

    try:
        details_json = json.dumps(assessment_data)
    except Exception as e:
        return False, None, [f"Serialization error: {str(e)}"]

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE insurance_assessments SET is_latest = 0 WHERE user_id = ?", (user_id,))

        cursor.execute(
            """
            INSERT INTO insurance_assessments (
                user_id, assessment_name, created_at, health_personal_cover, health_employer_cover,
                health_target_cover, health_gap, life_existing_cover, life_income_multiplier_years,
                life_liabilities, life_future_obligations, life_eligible_assets, life_estimated_need,
                life_gap, has_accident_disability_cover, accident_cover_amount, assessment_details_json, is_latest
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                user_id,
                str(inputs.get("assessment_name") or "Insurance Assessment").strip(),
                now_str,
                float(h_eval.get("personal_coverage", 0.0)),
                float(h_eval.get("employer_coverage", 0.0)),
                float(h_eval.get("target_coverage", 0.0)),
                float(h_eval.get("total_coverage_gap", 0.0)),
                float(l_eval.get("existing_life_insurance", 0.0)),
                float(l_eval.get("income_replacement_years", 10.0)),
                float(l_eval.get("outstanding_liabilities", 0.0)),
                float(l_eval.get("future_family_obligations", 0.0)),
                float(l_eval.get("existing_eligible_assets", 0.0)),
                float(l_eval.get("gross_protection_need", 0.0)),
                float(l_eval.get("net_additional_need", 0.0)),
                1 if acc_eval.get("has_accident_cover") else 0,
                float(acc_eval.get("current_sum_insured", 0.0)),
                details_json,
            ),
        )
        new_id = cursor.lastrowid
        conn.commit()

    return True, new_id, []


def get_latest_insurance_assessment(
    user_id: str = "default_user", db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Retrieve the most recent saved insurance assessment."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM insurance_assessments
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
            res["assessment_details"] = json.loads(res["assessment_details_json"])
        except Exception:
            res["assessment_details"] = {}
        return res


def get_insurance_assessment_history(
    user_id: str = "default_user", db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve full history of saved insurance assessments."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, assessment_name, created_at, health_target_cover, health_gap,
                   life_estimated_need, life_gap, is_latest
            FROM insurance_assessments
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def delete_insurance_assessment(
    assessment_id: int, user_id: str = "default_user", db_path: Optional[str] = None
) -> bool:
    """Delete a saved insurance assessment by ID."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM insurance_assessments WHERE id = ? AND user_id = ?", (assessment_id, user_id))
        conn.commit()
    return True
