"""
utils/goal_calculator.py
Deterministic goal feasibility and affordability calculations for AI Money Mentor.
Calculates remaining amounts, month-difference timelines, required monthly contributions,
and priority-weighted surplus allocations without assuming speculative returns.
"""
from datetime import date, datetime
import math
from typing import Any, Dict, List, Optional, Tuple

GOAL_CATEGORIES = [
    "Education",
    "Vehicle",
    "Home purchase",
    "Wedding",
    "Emergency savings",
    "Retirement",
    "Other",
]

GOAL_PRIORITIES = ["High", "Medium", "Low"]
PRIORITY_WEIGHTS = {"High": 3, "Medium": 2, "Low": 1}


def parse_goal_target_date(target_date_val: Any, current_date: Optional[date] = None) -> Tuple[bool, int, bool]:
    """
    Parse a goal target date and return (is_valid, remaining_months, is_expired).
    Month counting convention: (target_year - cur_year)*12 + (target_month - cur_month).
    """
    if not target_date_val:
        return False, 0, False

    today = current_date or date.today()

    if isinstance(target_date_val, (date, datetime)):
        t_year = target_date_val.year
        t_month = target_date_val.month
        t_day = getattr(target_date_val, "day", 1)
    else:
        date_str = str(target_date_val).strip()
        parts = date_str.split("-")
        if len(parts) < 2:
            return False, 0, False
        try:
            t_year = int(parts[0])
            t_month = int(parts[1])
            t_day = int(parts[2]) if len(parts) > 2 else 28
            if t_year < 1900 or t_year > 2200 or t_month < 1 or t_month > 12 or t_day < 1 or t_day > 31:
                return False, 0, False
        except (ValueError, IndexError):
            return False, 0, False

    months = (t_year - today.year) * 12 + (t_month - today.month)
    is_expired = months < 0 or (months == 0 and t_day < today.day)
    return True, max(0, months), is_expired


def evaluate_goal_feasibility(
    goal: Dict[str, Any],
    available_surplus: Optional[float] = None,
    current_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Evaluate deterministic mathematical feasibility for an individual goal.
    Calculates remaining shortfall, required monthly contributions, and affordability.
    """
    name = str(goal.get("name") or "Unnamed Goal").strip()
    category = str(goal.get("category") or "Other").strip()
    if category not in GOAL_CATEGORIES:
        category = "Other"

    priority = str(goal.get("priority") or "Medium").strip().capitalize()
    if priority not in GOAL_PRIORITIES:
        priority = "Medium"

    target_amount = max(0.0, float(goal.get("target_amount") or 0.0))
    current_amount = max(0.0, float(goal.get("current_amount") or 0.0))
    monthly_planned = max(0.0, float(goal.get("monthly_contribution") or 0.0))
    target_date_raw = goal.get("target_date")

    remaining_amount = max(0.0, target_amount - current_amount)
    explicit_completed = bool(goal.get("is_completed"))
    is_completed = explicit_completed or (remaining_amount == 0.0 and target_amount > 0.0)

    is_valid_date, remaining_months, is_expired = parse_goal_target_date(
        target_date_raw, current_date=current_date
    )

    alerts: List[Dict[str, str]] = []
    assumptions: List[str] = [
        "Baseline calculation assumes 0% investment returns (principal contributions only).",
        "Month-counting convention is based on calendar month difference to target date.",
    ]

    # Required monthly contribution logic
    if is_completed:
        required_monthly = 0.0
        status = "Completed"
    elif target_amount <= 0.0:
        required_monthly = 0.0
        status = "Invalid Target Amount"
        alerts.append({
            "level": "error",
            "message": "Target amount must be greater than ₹0 to calculate contributions.",
        })
    elif not is_valid_date:
        required_monthly = 0.0
        status = "Invalid Target Date"
        alerts.append({
            "level": "error",
            "message": "Target date is missing or has an invalid format (YYYY-MM-DD required).",
        })
    elif is_expired:
        required_monthly = 0.0
        status = "Target Date Passed"
        alerts.append({
            "level": "warning",
            "message": (
                f"Target date has already passed. A shortfall of ₹{remaining_amount:,.0f} "
                "remains. Update your target date to generate a realistic monthly plan."
            ),
        })
    elif remaining_months == 0:
        required_monthly = remaining_amount
        status = "Due Immediately"
        alerts.append({
            "level": "warning",
            "message": f"This goal is due immediately. Requires lump sum funding of ₹{remaining_amount:,.0f}.",
        })
    else:
        required_monthly = round(remaining_amount / remaining_months, 2)
        status = "In Progress"

    # Affordability analysis relative to available monthly surplus
    is_affordable = True
    surplus_shortfall = 0.0
    coverage_pct = 100.0
    affordability = "Affordable" if is_completed else ("Unknown" if available_surplus is None else "Affordable")

    if available_surplus is not None and not is_completed and required_monthly > 0:
        if available_surplus <= 0:
            is_affordable = False
            surplus_shortfall = required_monthly
            coverage_pct = 0.0
            affordability = "Cash Flow Deficit"
            alerts.append({
                "level": "warning",
                "message": (
                    f"Monthly surplus is ₹{available_surplus:,.0f}. You are operating in cash-flow deficit "
                    f"or zero surplus, making the required ₹{required_monthly:,.0f}/mo contribution unaffordable."
                ),
            })
        elif available_surplus < required_monthly:
            is_affordable = False
            surplus_shortfall = round(required_monthly - available_surplus, 2)
            coverage_pct = round((available_surplus / required_monthly) * 100.0, 1)
            affordability = "Shortfall"
            alerts.append({
                "level": "warning",
                "message": (
                    f"Required contribution (₹{required_monthly:,.0f}/mo) exceeds your available monthly "
                    f"surplus (₹{available_surplus:,.0f}) by ₹{surplus_shortfall:,.0f}/mo."
                ),
            })
        else:
            is_affordable = True
            surplus_shortfall = 0.0
            coverage_pct = round((available_surplus / required_monthly) * 100.0, 1)
            affordability = "Affordable"
    elif available_surplus is None and not is_completed and required_monthly > 0:
        affordability = "Unknown"

    # Progress percentage
    progress_pct = (
        round((current_amount / target_amount) * 100.0, 1)
        if target_amount > 0
        else (100.0 if is_completed else 0.0)
    )
    progress_pct = min(100.0, max(0.0, progress_pct))

    return {
        "id": goal.get("id"),
        "name": name,
        "category": category,
        "priority": priority,
        "target_amount": round(target_amount, 2),
        "current_amount": round(current_amount, 2),
        "remaining_amount": round(remaining_amount, 2),
        "monthly_planned": round(monthly_planned, 2),
        "target_date": str(target_date_raw) if target_date_raw else "Not Set",
        "remaining_months": remaining_months,
        "is_valid_date": is_valid_date,
        "is_expired": is_expired,
        "is_completed": is_completed,
        "required_monthly": required_monthly,
        "required_monthly_contribution": required_monthly,
        "allocated_from_surplus": 0.0,
        "progress_pct": progress_pct,
        "status": status,
        "is_affordable": is_affordable,
        "affordability": affordability,
        "surplus_shortfall": surplus_shortfall,
        "coverage_pct": coverage_pct,
        "alerts": alerts,
        "assumptions": assumptions,
    }


def evaluate_goals_portfolio(
    goals: List[Dict[str, Any]],
    available_surplus: Optional[float] = None,
    current_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Evaluate multiple goals simultaneously against the user's available monthly surplus.
    Prioritizes allocation by priority level (High > Medium > Low) and timeline urgency.
    """
    today = current_date or date.today()
    evaluated_goals = [
        evaluate_goal_feasibility(g, available_surplus=available_surplus, current_date=today)
        for g in (goals or [])
    ]

    total_goals_count = len(evaluated_goals)
    active_goals = [g for g in evaluated_goals if not g["is_completed"]]
    completed_goals = [g for g in evaluated_goals if g["is_completed"]]

    total_target_amount = sum(g["target_amount"] for g in evaluated_goals)
    total_saved_amount = sum(g["current_amount"] for g in evaluated_goals)
    total_remaining_amount = sum(g["remaining_amount"] for g in active_goals)

    # Sum only valid calculable required monthly contributions
    valid_active_contributions = [
        g["required_monthly_contribution"]
        for g in active_goals
        if not g["is_expired"] and g["is_valid_date"] and g["required_monthly_contribution"] > 0
    ]
    total_required_monthly = round(sum(valid_active_contributions), 2)

    if available_surplus is None:
        usable_surplus = 0.0
        is_portfolio_fully_funded = False
        portfolio_shortfall = total_required_monthly
        affordability_status = "Surplus Unknown"
    elif available_surplus <= 0:
        usable_surplus = 0.0
        is_portfolio_fully_funded = False
        portfolio_shortfall = total_required_monthly
        affordability_status = "Cash Flow Deficit"
    else:
        usable_surplus = float(available_surplus)
        is_portfolio_fully_funded = (total_required_monthly <= usable_surplus) and (
            total_required_monthly > 0 or not active_goals
        )
        portfolio_shortfall = max(0.0, round(total_required_monthly - usable_surplus, 2))
        affordability_status = (
            "Fully Affordable" if is_portfolio_fully_funded else "Partially Affordable"
        )

    # Priority-based sequential allocation of available surplus
    # Sort: Higher Priority (3 > 2 > 1), then shorter remaining months (urgent first)
    sorted_active = sorted(
        active_goals,
        key=lambda g: (-PRIORITY_WEIGHTS.get(g["priority"], 2), g["remaining_months"]),
    )

    remaining_funds = usable_surplus if (available_surplus is not None and available_surplus > 0) else 0.0
    allocation_schedule = []
    goal_alloc_map: Dict[Any, Dict[str, Any]] = {}

    for g in sorted_active:
        req = g["required_monthly_contribution"]
        if req <= 0 or g["is_expired"]:
            allocated = 0.0
        elif remaining_funds >= req:
            allocated = req
            remaining_funds -= req
        else:
            allocated = round(remaining_funds, 2)
            remaining_funds = 0.0

        is_funded = (allocated >= req) if req > 0 else True
        afford = "Affordable" if is_funded else ("Partially Funded" if allocated > 0 else "Shortfall")
        if available_surplus is None:
            afford = "Unknown"
        elif available_surplus <= 0:
            afford = "Cash Flow Deficit"

        g_alloc = dict(g)
        g_alloc["allocated_from_surplus"] = allocated
        g_alloc["allocated_monthly"] = allocated
        g_alloc["allocation_gap"] = round(max(0.0, req - allocated), 2)
        g_alloc["is_funded_from_surplus"] = is_funded
        g_alloc["affordability"] = afford

        goal_alloc_map[g.get("id")] = g_alloc
        allocation_schedule.append(g_alloc)

    # Enrich evaluated_goals list with allocated_from_surplus
    enriched_evaluated = []
    for g in evaluated_goals:
        if g.get("id") in goal_alloc_map:
            enriched_evaluated.append(goal_alloc_map[g.get("id")])
        else:
            enriched_evaluated.append(g)

    # Overall portfolio alerts
    portfolio_alerts = []
    if available_surplus is None:
        portfolio_alerts.append({
            "level": "info",
            "title": "Monthly Surplus Unknown",
            "message": "Monthly surplus is unknown. Operating with unknown surplus prevents validating goal affordability.",
        })
    elif available_surplus <= 0 and active_goals:
        portfolio_alerts.append({
            "level": "error",
            "title": "Monthly Cash-Flow Deficit",
            "message": (
                f"Your monthly surplus is ₹{available_surplus:,.0f}. Operating in deficit prevents funding "
                f"your active goals (₹{total_required_monthly:,.0f}/mo required). Rebalance your budget first."
            ),
        })
    elif portfolio_shortfall > 0:
        portfolio_alerts.append({
            "level": "warning",
            "title": "Goal Competition Shortfall",
            "message": (
                f"Your active goals require ₹{total_required_monthly:,.0f}/mo, exceeding affordable surplus "
                f"(₹{usable_surplus:,.0f}/mo) by ₹{portfolio_shortfall:,.0f}/mo. Lower-priority goals have been curtailed."
            ),
        })
    elif is_portfolio_fully_funded and total_required_monthly > 0:
        portfolio_alerts.append({
            "level": "success",
            "title": "Goals Fully Affordable",
            "message": (
                f"Your monthly surplus of ₹{usable_surplus:,.0f} comfortably covers all active goals "
                f"(₹{total_required_monthly:,.0f}/mo required). Automate these transfers on salary day."
            ),
        })

    affordable_count = sum(
        1 for g in allocation_schedule if g["is_funded_from_surplus"] and g["required_monthly_contribution"] > 0
    )
    shortfall_count = sum(1 for g in allocation_schedule if not g["is_funded_from_surplus"])

    summary = {
        "total_goals_count": total_goals_count,
        "active_goals_count": len(active_goals),
        "completed_goals_count": len(completed_goals),
        "total_target_amount": round(total_target_amount, 2),
        "total_saved_amount": round(total_saved_amount, 2),
        "total_remaining_amount": round(total_remaining_amount, 2),
        "total_required_monthly": total_required_monthly,
        "available_surplus": round(available_surplus, 2) if available_surplus is not None else None,
        "is_portfolio_fully_funded": is_portfolio_fully_funded,
        "portfolio_shortfall": portfolio_shortfall,
        "affordable_goals_count": affordable_count,
        "shortfall_goals_count": shortfall_count,
        "affordability_status": affordability_status,
    }

    return {
        "summary": summary,
        "portfolio_alerts": portfolio_alerts,
        "alerts": portfolio_alerts,
        "evaluated_goals": enriched_evaluated,
        "allocation_schedule": allocation_schedule,
        **summary,
    }

