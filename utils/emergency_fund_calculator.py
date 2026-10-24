"""
utils/emergency_fund_calculator.py
Deterministic mathematical calculations for Emergency Fund planning in AI Money Mentor.
Includes target corpus, coverage in months, gap, completion timeline,
status categorizations, and contribution scenario modeling.
"""
from datetime import date
import math
from typing import Any, Dict, List, Optional


def calculate_emergency_fund_target(
    essential_expenses: float,
    target_months: float = 6.0,
) -> float:
    """
    Calculate the target emergency fund amount.
    Formula: Target = Monthly Essential Expenses * Target Coverage Months

    Args:
        essential_expenses: Monthly essential living expenses in ₹.
        target_months: Desired emergency coverage in months (e.g. 3, 6, 9, 12).

    Returns:
        Target emergency fund amount in ₹ rounded to 2 decimal places.
    """
    exp = max(0.0, float(essential_expenses or 0.0))
    months = max(0.0, float(target_months or 0.0))
    return round(exp * months, 2)


def calculate_emergency_fund_coverage(
    current_savings: float,
    essential_expenses: float,
) -> float:
    """
    Calculate emergency fund coverage in months.
    Formula: Coverage Months = Current Eligible Savings / Monthly Essential Expenses

    Handles zero essential expenses safely without division by zero.
    """
    sav = max(0.0, float(current_savings or 0.0))
    exp = max(0.0, float(essential_expenses or 0.0))
    if exp <= 0.0:
        return 0.0
    return round(sav / exp, 2)


def calculate_emergency_fund_gap(
    target_amount: float,
    current_savings: float,
) -> float:
    """
    Calculate the amount remaining to reach the emergency fund target.
    Formula: Gap = max(0, Target - Current Eligible Savings)
    """
    tgt = max(0.0, float(target_amount or 0.0))
    sav = max(0.0, float(current_savings or 0.0))
    return round(max(0.0, tgt - sav), 2)


def calculate_emergency_fund_progress(
    current_savings: float,
    target_amount: float,
) -> Dict[str, Any]:
    """
    Calculate the percentage of the emergency fund target completed.
    Formula: Progress = (Current Eligible Savings / Target) * 100

    Caps displayed completion percentage at 100% while preserving actual percentage.
    """
    sav = max(0.0, float(current_savings or 0.0))
    tgt = max(0.0, float(target_amount or 0.0))

    if tgt <= 0.0:
        pct = 100.0 if sav >= 0 else 0.0
        return {
            "progress_pct": 100.0,
            "actual_pct": 100.0,
            "is_target_reached": True,
            "surplus_amount": round(sav, 2),
        }

    actual_pct = round((sav / tgt) * 100.0, 1)
    display_pct = min(100.0, actual_pct)
    is_reached = sav >= tgt
    surplus = max(0.0, sav - tgt) if is_reached else 0.0

    return {
        "progress_pct": display_pct,
        "actual_pct": actual_pct,
        "is_target_reached": is_reached,
        "surplus_amount": round(surplus, 2),
    }


def calculate_months_to_target(
    gap: float,
    monthly_contribution: float,
) -> Dict[str, Any]:
    """
    Calculate estimated months to reach the emergency fund target.
    Formula: Months = Ceiling(Gap / Monthly Contribution)

    Handles zero contribution and zero gap edge cases cleanly.
    """
    g = max(0.0, float(gap or 0.0))
    contrib = float(monthly_contribution or 0.0)

    if g <= 0.0:
        return {
            "months": 0,
            "is_reachable": True,
            "message": "Target already reached. No additional contributions required.",
        }

    if contrib <= 0.0:
        return {
            "months": None,
            "is_reachable": False,
            "message": "Target cannot be reached with zero or negative monthly contributions alone.",
        }

    months = math.ceil(g / contrib)
    return {
        "months": months,
        "is_reachable": True,
        "message": f"Estimated {months} months to complete at ₹{contrib:,.0f}/mo.",
    }


def calculate_completion_date(
    months: Optional[int],
    start_date: Optional[date] = None,
) -> Optional[date]:
    """
    Estimate completion calendar month/date given number of months.
    Adds calendar months safely.
    """
    if months is None or months < 0:
        return None

    ref = start_date or date.today()
    if months == 0:
        return ref

    new_year = ref.year + ((ref.month - 1 + months) // 12)
    new_month = ((ref.month - 1 + months) % 12) + 1
    # Clamp day to maximum in that target month
    max_days = [31, 29 if (new_year % 4 == 0 and (new_year % 100 != 0 or new_year % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    new_day = min(ref.day, max_days[new_month - 1])

    return date(new_year, new_month, new_day)


def get_emergency_fund_status(
    coverage_months: float,
    target_months: float = 6.0,
    thresholds: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Categorize emergency fund resilience into neutral educational categories:
      - Critical: < 1.0 month
      - Low: 1.0 to < 3.0 months
      - Building: 3.0 to < target_months
      - Target Reached: >= target_months

    Thresholds can be customized via the `thresholds` dictionary.
    """
    cov = max(0.0, float(coverage_months or 0.0))
    tgt = max(1.0, float(target_months or 6.0))

    t_crit = (thresholds or {}).get("critical", 1.0)
    t_low = (thresholds or {}).get("low", 3.0)

    if cov >= tgt:
        return {
            "status": "Target Reached",
            "tier": "safe",
            "badge": "✅ Fully Funded",
            "color": "#10b981",
            "description": f"Your liquid savings cover {cov:.1f} months of essential expenses, meeting or exceeding your {tgt:.0f}-month target.",
            "next_action": "Maintain this buffer in high-yield liquid accounts or sweep-in FDs. Direct additional surplus to long-term wealth goals.",
        }
    elif cov < t_crit:
        return {
            "status": "Critical",
            "tier": "critical",
            "badge": "🚨 Critical (< 1 Month)",
            "color": "#ef4444",
            "description": f"Your liquid reserves cover {cov:.1f} months of essential expenses (less than {t_crit:.0f} month).",
            "next_action": "Prioritize building an immediate 1-month essential cash buffer before allocating surplus to aggressive investments.",
        }
    elif cov < t_low:
        return {
            "status": "Low",
            "tier": "warning",
            "badge": "⚠️ Low (1-3 Months)",
            "color": "#f59e0b",
            "description": f"You have {cov:.1f} months of emergency coverage. This provides a basic safety net but remains vulnerable to prolonged income disruptions.",
            "next_action": "Gradually scale emergency savings toward 3 to 6 months by allocating a consistent monthly contribution.",
        }
    else:  # cov < tgt
        return {
            "status": "Building",
            "tier": "info",
            "badge": "⏳ Building (3+ Months)",
            "color": "#3b82f6",
            "description": f"You have {cov:.1f} months of coverage. Good foundation in place, progressing toward your target of {tgt:.0f} months.",
            "next_action": "Continue steady monthly allocations until the target is reached.",
        }


def recommend_monthly_contribution(
    available_surplus: Optional[float],
    gap: float,
    monthly_debt: float = 0.0,
    target_months_to_save: int = 12,
) -> Dict[str, Any]:
    """
    Recommend a realistic monthly contribution based on available budget surplus,
    debt obligations, and remaining emergency fund gap.

    Does not invent money if the user has a cash-flow deficit.
    """
    g = max(0.0, float(gap or 0.0))
    debt = max(0.0, float(monthly_debt or 0.0))
    horizon_months = max(1, int(target_months_to_save or 12))

    if g <= 0.0:
        return {
            "recommended_monthly": 0.0,
            "status": "Target Reached",
            "reason": "Emergency fund is already fully funded. ₹0 monthly contribution needed.",
            "is_affordable": True,
        }

    if available_surplus is None:
        ideal = round(g / horizon_months, 2)
        return {
            "recommended_monthly": ideal,
            "status": "Budget Data Missing",
            "reason": f"Mathematical baseline to complete in {horizon_months} months (₹{ideal:,.0f}/mo). Set up your budget profile to verify affordability.",
            "is_affordable": True,
        }

    surplus = float(available_surplus)
    if surplus <= 0.0:
        deficit_amt = abs(surplus)
        return {
            "recommended_monthly": 0.0,
            "status": "Cash Flow Deficit",
            "reason": (
                f"You are currently running a monthly deficit of ₹{deficit_amt:,.0f}. "
                "Establishing an emergency fund is critical, but requires reducing discretionary expenses first to free up surplus."
            ),
            "is_affordable": False,
        }

    # If debt repayment is heavy, balance between debt and emergency fund
    ideal_pace = g / horizon_months
    # Allocate up to 50% of available surplus or ideal pace, capped at total surplus
    suggested = min(surplus, max(min(surplus * 0.5, ideal_pace), min(surplus, 1000.0)))
    suggested = round(suggested, 2)

    is_affordable = suggested <= surplus

    return {
        "recommended_monthly": suggested,
        "status": "Affordable",
        "available_surplus": round(surplus, 2),
        "surplus_utilization_pct": round((suggested / surplus) * 100.0, 1) if surplus > 0 else 0.0,
        "reason": f"Allocating ₹{suggested:,.0f}/mo ({round((suggested / surplus) * 100.0):.0f}% of surplus) leaves ₹{surplus - suggested:,.0f}/mo for debt service and wealth goals.",
        "is_affordable": is_affordable,
    }


def evaluate_contribution_scenarios(
    gap: float,
    available_surplus: Optional[float],
    scenarios: Optional[List[float]] = None,
    start_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    Compare multiple monthly contribution scenarios (e.g. ₹2,000, ₹5,000, ₹10,000)
    and their impact on time to reach the emergency fund target and affordability.
    """
    g = max(0.0, float(gap or 0.0))
    surplus = float(available_surplus) if available_surplus is not None else None
    ref_date = start_date or date.today()

    default_scenarios = [2000.0, 5000.0, 10000.0, 20000.0]
    amounts = sorted(list(set([float(x) for x in (scenarios or default_scenarios) if float(x) > 0])))

    results: List[Dict[str, Any]] = []
    for amt in amounts:
        timing = calculate_months_to_target(g, amt)
        months = timing.get("months")
        comp_date = calculate_completion_date(months, ref_date) if months is not None else None

        is_affordable = (amt <= surplus) if surplus is not None else True
        afford_status = "Affordable" if is_affordable else (
            "Exceeds Surplus" if (surplus is not None and surplus > 0) else "Cash Deficit"
        )

        results.append({
            "monthly_amount": amt,
            "months_to_target": months,
            "completion_date": comp_date.strftime("%b %Y") if comp_date else "N/A",
            "is_affordable": is_affordable,
            "affordability_status": afford_status,
            "is_reachable": timing["is_reachable"],
        })

    return results
