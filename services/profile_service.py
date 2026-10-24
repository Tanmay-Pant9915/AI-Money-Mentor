"""
services/profile_service.py
Service layer for managing financial profiles, goal tracking, validation,
and persistence in AI Money Mentor.
"""
from datetime import date, datetime
import re
from typing import Any, Dict, List, Optional, Tuple

from data.database import get_connection, init_db

VALID_EMPLOYMENT_STATUSES = [
    "Salaried Employee",
    "Self-Employed",
    "Business Owner",
    "Student",
    "Other",
]


def format_inr(amount: float, include_paise: bool = False) -> str:
    """
    Format a float/int into Indian Rupee notation (e.g. ₹1,50,000 or -₹25,000).
    Follows Indian numbering grouping (2, 2, 3 digits).
    """
    if amount is None:
        return "₹0"
    is_negative = amount < 0
    abs_amt = abs(amount)

    if include_paise:
        amt_str = f"{abs_amt:.2f}"
        int_part, dec_part = amt_str.split(".")
    else:
        int_part = str(int(round(abs_amt)))
        dec_part = None

    if len(int_part) <= 3:
        formatted = int_part
    else:
        last_three = int_part[-3:]
        remaining = int_part[:-3]
        # Group in pairs from right to left
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted = ",".join(groups) + "," + last_three

    if dec_part is not None:
        formatted = f"{formatted}.{dec_part}"

    prefix = "-₹" if is_negative else "₹"
    return f"{prefix}{formatted}"


def validate_profile_data(data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """
    Validate user-entered financial profile data.

    Returns:
        (is_valid, errors, warnings)
        errors: blocking issues (negative amounts, missing name, invalid age)
        warnings: non-blocking advisory flags (e.g., expenses exceed income)
    """
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Name
    name = str(data.get("name", "")).strip()
    if not name:
        errors.append("Name or display name is required.")

    # 2. Age
    age = data.get("age")
    if age is None or not isinstance(age, (int, float)):
        errors.append("Age is required and must be a valid number.")
    else:
        if age < 18 or age > 120:
            errors.append("Age must be between 18 and 120 years.")

    # 3. Employment Status
    emp_status = data.get("employment_status")
    if not emp_status or emp_status not in VALID_EMPLOYMENT_STATUSES:
        errors.append(
            f"Employment status must be one of: {', '.join(VALID_EMPLOYMENT_STATUSES)}."
        )

    # 4. Financial Non-negative amounts
    financial_fields = [
        ("monthly_income", "Monthly take-home income"),
        ("essential_expenses", "Monthly essential expenses"),
        ("discretionary_expenses", "Monthly discretionary expenses"),
        ("other_expenses", "Other monthly expenses"),
        ("savings_liquid", "Current savings & liquid cash reserves"),
        ("outstanding_debt", "Outstanding debt balance"),
        ("monthly_debt_repayment", "Monthly debt repayments"),
        ("existing_investments", "Existing investment value"),
    ]

    numeric_values: Dict[str, float] = {}
    for key, label in financial_fields:
        val = data.get(key, 0.0)
        try:
            val_f = float(val) if val is not None else 0.0
            if val_f < 0:
                errors.append(f"{label} cannot be negative.")
            numeric_values[key] = max(0.0, val_f)
        except (ValueError, TypeError):
            errors.append(f"{label} must be a valid number.")
            numeric_values[key] = 0.0

    # 5. Dependents
    dependents = data.get("dependents", 0)
    try:
        dep_int = int(dependents) if dependents is not None else 0
        if dep_int < 0:
            errors.append("Number of financial dependents cannot be negative.")
    except (ValueError, TypeError):
        errors.append("Number of financial dependents must be an integer.")

    # 6. Warnings (Non-blocking)
    if not errors:
        total_monthly_expenses = (
            numeric_values["essential_expenses"]
            + numeric_values["discretionary_expenses"]
            + numeric_values["other_expenses"]
            + numeric_values["monthly_debt_repayment"]
        )
        income = numeric_values["monthly_income"]

        if total_monthly_expenses > income:
            deficit = total_monthly_expenses - income
            warnings.append(
                f"Warning: Total monthly expenses ({format_inr(total_monthly_expenses)}) "
                f"exceed monthly income ({format_inr(income)}). "
                f"You are running a monthly deficit of {format_inr(deficit)}."
            )

        if numeric_values["outstanding_debt"] > 0 and numeric_values["monthly_debt_repayment"] == 0:
            warnings.append(
                f"Notice: You reported outstanding debt of {format_inr(numeric_values['outstanding_debt'])}, "
                "but monthly debt repayment is set to ₹0."
            )

    return (len(errors) == 0, errors, warnings)


def validate_goal_data(goal: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate an individual financial goal.

    Returns:
        (is_valid, errors)
    """
    errors: List[str] = []

    name = str(goal.get("name", "")).strip()
    if not name:
        errors.append("Goal name cannot be empty.")

    try:
        target_amt = float(goal.get("target_amount", 0))
        if target_amt <= 0:
            errors.append(f"Goal '{name or 'Unnamed'}': Target amount must be greater than ₹0.")
    except (ValueError, TypeError):
        errors.append(f"Goal '{name or 'Unnamed'}': Target amount must be a valid number.")

    try:
        curr_amt = float(goal.get("current_amount", 0))
        if curr_amt < 0:
            errors.append(f"Goal '{name or 'Unnamed'}': Current amount saved cannot be negative.")
    except (ValueError, TypeError):
        errors.append(f"Goal '{name or 'Unnamed'}': Current amount must be a valid number.")

    target_date_val = goal.get("target_date")
    if not target_date_val:
        errors.append(f"Goal '{name or 'Unnamed'}': Target date is required.")
    else:
        # Check date format / value
        target_d: Optional[date] = None
        if isinstance(target_date_val, (date, datetime)):
            target_d = target_date_val if isinstance(target_date_val, date) else target_date_val.date()
        elif isinstance(target_date_val, str):
            try:
                target_d = datetime.strptime(target_date_val.strip(), "%Y-%m-%d").date()
            except ValueError:
                errors.append(f"Goal '{name or 'Unnamed'}': Target date must be in YYYY-MM-DD format.")

        if target_d and target_d < date.today():
            errors.append(f"Goal '{name or 'Unnamed'}': Target date ({target_d}) cannot be in the past.")

    return (len(errors) == 0, errors)


def calculate_profile_metrics(profile_data: Dict[str, Any], goals: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Deterministic calculation of financial summary metrics.
    Surplus = Monthly income - Total monthly expenses
    """
    income = float(profile_data.get("monthly_income") or 0.0)
    essential = float(profile_data.get("essential_expenses") or 0.0)
    discretionary = float(profile_data.get("discretionary_expenses") or 0.0)
    other = float(profile_data.get("other_expenses") or 0.0)
    debt_repayment = float(profile_data.get("monthly_debt_repayment") or 0.0)

    total_expenses = essential + discretionary + other + debt_repayment
    surplus = income - total_expenses
    is_deficit = surplus < 0

    savings = float(profile_data.get("savings_liquid") or 0.0)
    debt = float(profile_data.get("outstanding_debt") or 0.0)
    investments = float(profile_data.get("existing_investments") or 0.0)
    net_worth = (savings + investments) - debt

    emergency_months = (savings / essential) if essential > 0 else 0.0

    num_goals = len(goals) if goals is not None else 0
    total_goals_target = sum(float(g.get("target_amount") or 0) for g in (goals or []))
    total_goals_saved = sum(float(g.get("current_amount") or 0) for g in (goals or []))

    return {
        "monthly_income": income,
        "essential_expenses": essential,
        "discretionary_expenses": discretionary,
        "other_expenses": other,
        "monthly_debt_repayment": debt_repayment,
        "total_monthly_expenses": total_expenses,
        "monthly_surplus": surplus,
        "is_deficit": is_deficit,
        "surplus_label": "Monthly Deficit" if is_deficit else "Monthly Surplus",
        "savings_liquid": savings,
        "outstanding_debt": debt,
        "existing_investments": investments,
        "net_worth": net_worth,
        "dependents": int(profile_data.get("dependents") or 0),
        "emergency_months": round(emergency_months, 1),
        "num_goals": num_goals,
        "total_goals_target": total_goals_target,
        "total_goals_saved": total_goals_saved,
    }


def save_profile(
    profile_data: Dict[str, Any],
    goals: Optional[List[Dict[str, Any]]] = None,
    user_id: str = "default_user",
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Save or update a financial profile and associated goals.
    Maintains a single record per user_id, preventing duplicates.
    """
    init_db(db_path)
    now_str = datetime.now().isoformat()

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Check existing profile
        cursor.execute(
            "SELECT id FROM financial_profiles WHERE user_id = ?",
            (user_id,)
        )
        existing = cursor.fetchone()

        if existing:
            profile_id = existing["id"]
            cursor.execute(
                """
                UPDATE financial_profiles SET
                    name = ?,
                    age = ?,
                    employment_status = ?,
                    monthly_income = ?,
                    essential_expenses = ?,
                    discretionary_expenses = ?,
                    other_expenses = ?,
                    savings_liquid = ?,
                    outstanding_debt = ?,
                    monthly_debt_repayment = ?,
                    existing_investments = ?,
                    dependents = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    str(profile_data["name"]).strip(),
                    int(profile_data["age"]),
                    str(profile_data["employment_status"]),
                    float(profile_data["monthly_income"]),
                    float(profile_data["essential_expenses"]),
                    float(profile_data["discretionary_expenses"]),
                    float(profile_data.get("other_expenses", 0.0)),
                    float(profile_data.get("savings_liquid", 0.0)),
                    float(profile_data.get("outstanding_debt", 0.0)),
                    float(profile_data.get("monthly_debt_repayment", 0.0)),
                    float(profile_data.get("existing_investments", 0.0)),
                    int(profile_data.get("dependents", 0)),
                    now_str,
                    profile_id,
                )
            )
        else:
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
                    str(profile_data["name"]).strip(),
                    int(profile_data["age"]),
                    str(profile_data["employment_status"]),
                    float(profile_data["monthly_income"]),
                    float(profile_data["essential_expenses"]),
                    float(profile_data["discretionary_expenses"]),
                    float(profile_data.get("other_expenses", 0.0)),
                    float(profile_data.get("savings_liquid", 0.0)),
                    float(profile_data.get("outstanding_debt", 0.0)),
                    float(profile_data.get("monthly_debt_repayment", 0.0)),
                    float(profile_data.get("existing_investments", 0.0)),
                    int(profile_data.get("dependents", 0)),
                    now_str,
                    now_str,
                )
            )
            profile_id = cursor.lastrowid

        # Replace goals
        cursor.execute("DELETE FROM financial_goals WHERE profile_id = ?", (profile_id,))
        if goals:
            for g in goals:
                target_date_str = str(g["target_date"])
                if isinstance(g["target_date"], (date, datetime)):
                    target_date_str = g["target_date"].strftime("%Y-%m-%d")
                category = str(g.get("category") or "Other").strip()
                priority = str(g.get("priority") or "Medium").strip()
                mo_contrib = float(g.get("monthly_contribution", 0.0) or 0.0)
                is_comp = 1 if g.get("is_completed") else 0
                cursor.execute(
                    """
                    INSERT INTO financial_goals (
                        profile_id, name, category, target_amount, target_date, current_amount,
                        monthly_contribution, priority, is_completed, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        profile_id,
                        str(g["name"]).strip(),
                        category,
                        float(g["target_amount"]),
                        target_date_str,
                        float(g.get("current_amount", 0.0) or 0.0),
                        mo_contrib,
                        priority,
                        is_comp,
                        now_str,
                        now_str,
                    )
                )

        conn.commit()

    return get_profile(user_id=user_id, db_path=db_path)


def get_profile(user_id: str = "default_user", db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve financial profile and goals for a given user.
    Returns None if no profile exists.
    """
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM financial_profiles WHERE user_id = ?",
            (user_id,)
        )
        profile_row = cursor.fetchone()
        if not profile_row:
            return None

        profile_dict = dict(profile_row)

        cursor.execute(
            "SELECT * FROM financial_goals WHERE profile_id = ? ORDER BY target_date ASC",
            (profile_dict["id"],)
        )
        goals_rows = cursor.fetchall()
        profile_dict["goals"] = [dict(g) for g in goals_rows]
        profile_dict["metrics"] = calculate_profile_metrics(profile_dict, profile_dict["goals"])

        return profile_dict
