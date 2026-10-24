"""
utils/budget_calculator.py
Deterministic budgeting and financial planning engine for AI Money Mentor.
Performs financial summary calculations, non-overlapping outflow aggregation,
goal contribution scheduling, emergency fund allocation, and scenario comparisons.
"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple


def parse_target_date_info(target_date_val: Any, current_date: Optional[date] = None) -> Tuple[bool, int, bool]:
    """
    Parse target date and return (is_valid_date, remaining_months, is_expired).
    Month-counting convention: (target_year - cur_year)*12 + (target_month - cur_month).
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


def calculate_financial_summary(
    profile_data: Optional[Dict[str, Any]],
    debt_already_in_expenses: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Calculate deterministic monthly cash flow summary from validated profile data.
    Ensures non-overlapping expense categories and avoids double-counting debt repayments.
    Flags missing fields and distinguishes debt repayments from day-to-day living expenses.
    """
    if not profile_data:
        missing_fields = [
            "Monthly Take-Home Income",
            "Essential Living Expenses",
            "Discretionary Living Expenses",
            "Other Living Expenses",
            "Monthly Debt Repayment",
            "Outstanding Debt Balance",
            "Liquid Savings",
            "Existing Investments",
        ]
        return {
            "has_data": False,
            "monthly_income": 0.0,
            "essential_expenses": 0.0,
            "discretionary_expenses": 0.0,
            "other_expenses": 0.0,
            "living_expenses": 0.0,
            "monthly_debt_repayment": 0.0,
            "outstanding_debt": 0.0,
            "savings_liquid": 0.0,
            "existing_investments": 0.0,
            "dependents": 0,
            "debt_already_in_expenses": False,
            "total_monthly_outflows": 0.0,
            "monthly_surplus": 0.0,
            "is_deficit": False,
            "savings_rate": 0.0,
            "debt_to_income": 0.0,
            "breakdown": {},
            "missing_fields": missing_fields,
            "is_data_incomplete": True,
            "is_emergency_provisional": True,
            "status_message": "No financial profile data provided.",
        }

    # Detect explicitly missing fields
    missing_fields: List[str] = []
    field_checks = [
        ("monthly_income", "Monthly Take-Home Income"),
        ("essential_expenses", "Essential Living Expenses"),
        ("discretionary_expenses", "Discretionary Living Expenses"),
        ("other_expenses", "Other Living Expenses"),
        ("monthly_debt_repayment", "Monthly Debt Repayment"),
        ("outstanding_debt", "Outstanding Debt Balance"),
        ("savings_liquid", "Liquid Savings"),
        ("existing_investments", "Existing Investments"),
    ]
    for key, label in field_checks:
        if profile_data.get(key) is None:
            missing_fields.append(label)

    is_data_incomplete = len(missing_fields) > 0
    is_emergency_provisional = (
        "Liquid Savings" in missing_fields or "Essential Living Expenses" in missing_fields
    )

    income = max(0.0, float(profile_data.get("monthly_income") or 0.0))
    essential = max(0.0, float(profile_data.get("essential_expenses") or 0.0))
    discretionary = max(0.0, float(profile_data.get("discretionary_expenses") or 0.0))
    other = max(0.0, float(profile_data.get("other_expenses") or 0.0))

    raw_debt_repay = profile_data.get("monthly_debt_repayment")
    debt_repayment = max(0.0, float(raw_debt_repay or 0.0))
    outstanding_debt = max(0.0, float(profile_data.get("outstanding_debt") or 0.0))
    savings_liquid = max(0.0, float(profile_data.get("savings_liquid") or 0.0))
    existing_investments = max(0.0, float(profile_data.get("existing_investments") or 0.0))
    dependents = int(profile_data.get("dependents") or 0)

    # Debt double-counting guard: check if debt is explicitly marked as included in expenses
    debt_included = bool(
        debt_already_in_expenses
        if debt_already_in_expenses is not None
        else profile_data.get("debt_included_in_expenses", False)
    )

    # Living expenses
    living_expenses = essential + discretionary + other

    if debt_included:
        # Debt repayments are already embedded in expense categories (e.g. Essential or Other).
        # Total monthly outflows = living_expenses (do not add debt_repayment again).
        total_outflows = living_expenses
        non_debt_essential = max(0.0, essential - debt_repayment)
        categories = [
            ("Essential Living (excl. debt)", non_debt_essential, "#3b82f6"),
            ("Discretionary Living", discretionary, "#f59e0b"),
            ("Other Expenses", other, "#8b5cf6"),
            ("Debt Repayment (Included in Expenses)", debt_repayment, "#ef4444"),
        ]
    else:
        # Living expenses exclude debt repayments to guarantee non-overlapping categories
        total_outflows = living_expenses + debt_repayment
        categories = [
            ("Essential Living", essential, "#3b82f6"),
            ("Discretionary Living", discretionary, "#f59e0b"),
            ("Other Expenses", other, "#8b5cf6"),
            ("Debt Repayment", debt_repayment, "#ef4444"),
        ]

    surplus = income - total_outflows
    is_deficit = surplus < 0

    # Savings rate (%) and DTI (%) - Handle zero income safely
    if income > 0:
        savings_rate = round((surplus / income) * 100.0, 1)
        dti = round((debt_repayment / income) * 100.0, 1)
    else:
        savings_rate = 0.0
        dti = 0.0

    breakdown = {}
    for name, amount, color in categories:
        pct_outflows = round((amount / total_outflows * 100.0), 1) if total_outflows > 0 else 0.0
        pct_income = round((amount / income * 100.0), 1) if income > 0 else 0.0
        breakdown[name] = {
            "amount": round(amount, 2),
            "pct_of_outflows": pct_outflows,
            "pct_of_income": pct_income,
            "color": color,
        }

    status_msg = (
        "Provisional: Incomplete profile data."
        if is_data_incomplete
        else "Deficit: Outflows exceed income."
        if is_deficit
        else "Positive cash flow."
    )

    return {
        "has_data": income > 0,
        "monthly_income": round(income, 2),
        "essential_expenses": round(essential, 2),
        "discretionary_expenses": round(discretionary, 2),
        "other_expenses": round(other, 2),
        "living_expenses": round(living_expenses, 2),
        "monthly_debt_repayment": round(debt_repayment, 2),
        "outstanding_debt": round(outstanding_debt, 2),
        "savings_liquid": round(savings_liquid, 2),
        "existing_investments": round(existing_investments, 2),
        "dependents": dependents,
        "debt_already_in_expenses": debt_included,
        "total_monthly_outflows": round(total_outflows, 2),
        "monthly_surplus": round(surplus, 2),
        "is_deficit": is_deficit,
        "savings_rate": savings_rate,
        "debt_to_income": dti,
        "breakdown": breakdown,
        "missing_fields": missing_fields,
        "is_data_incomplete": is_data_incomplete,
        "is_emergency_provisional": is_emergency_provisional,
        "status_message": status_msg,
    }


def calculate_remaining_months(target_date_val: Any, current_date: Optional[date] = None) -> int:
    """
    Calculate remaining months between current date and target date.
    Uses month-difference convention: (target_year - cur_year)*12 + (target_month - cur_month).
    """
    is_valid, months, _ = parse_target_date_info(target_date_val, current_date=current_date)
    return months if is_valid else 0


def calculate_goal_contributions(
    goals: Optional[List[Dict[str, Any]]],
    available_surplus: float,
    current_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Calculate deterministic required monthly contributions for active financial goals.
    Pro-rates or prioritizes allocations when total requested contributions exceed available surplus.
    Does not assume investment returns (provides conservative deterministic baseline).
    """
    if not goals:
        return {
            "has_goals": False,
            "goals_detail": [],
            "total_required_monthly": 0.0,
            "total_allocated_monthly": 0.0,
            "is_fully_funded": True,
            "surplus_shortfall": 0.0,
            "status_message": "No financial goals configured in profile.",
        }

    goals_detail = []
    total_required = 0.0

    for g in goals:
        name = str(g.get("name") or "Unnamed Goal").strip()
        target = max(0.0, float(g.get("target_amount") or 0.0))
        saved = max(0.0, float(g.get("current_amount") or 0.0))
        target_date_raw = g.get("target_date")

        remaining_amt = max(0.0, target - saved)
        is_completed = remaining_amt == 0.0 and target > 0

        is_valid_date, rem_months, is_expired = parse_target_date_info(target_date_raw, current_date=current_date)

        if is_completed:
            required_monthly = 0.0
            status = "Completed"
        elif target <= 0:
            required_monthly = 0.0
            status = "Invalid Target"
        elif not is_valid_date:
            required_monthly = 0.0
            status = "Invalid Target Date"
        elif is_expired or rem_months == 0:
            required_monthly = remaining_amt
            status = "Due / Expired Target Date"
        else:
            required_monthly = remaining_amt / rem_months
            status = "In Progress"

        required_monthly = round(required_monthly, 2)
        total_required += required_monthly

        goals_detail.append({
            "name": name,
            "target_amount": round(target, 2),
            "current_amount": round(saved, 2),
            "remaining_amount": round(remaining_amt, 2),
            "target_date": str(target_date_raw) if target_date_raw else "Not Set",
            "remaining_months": rem_months,
            "is_completed": is_completed,
            "is_expired": is_expired,
            "is_valid_date": is_valid_date,
            "required_monthly": required_monthly,
            "allocated_monthly": 0.0,  # Computed below based on available surplus
            "shortfall": 0.0,
            "status": status,
        })

    # Allocation of available surplus across goals
    usable_surplus = max(0.0, available_surplus)
    total_allocated = 0.0

    if total_required <= usable_surplus and total_required > 0:
        # Full funding feasible
        for item in goals_detail:
            item["allocated_monthly"] = item["required_monthly"]
            item["shortfall"] = 0.0
        total_allocated = total_required
        is_fully_funded = True
        surplus_shortfall = 0.0
    elif usable_surplus > 0 and total_required > 0:
        # Partial funding: pro-rate proportionally so total does not exceed usable_surplus
        scale = usable_surplus / total_required
        for item in goals_detail:
            alloc = round(item["required_monthly"] * scale, 2)
            item["allocated_monthly"] = alloc
            item["shortfall"] = round(item["required_monthly"] - alloc, 2)
            total_allocated += alloc
        total_allocated = round(total_allocated, 2)
        is_fully_funded = False
        surplus_shortfall = round(total_required - usable_surplus, 2)
    else:
        # Zero surplus or zero goals required
        for item in goals_detail:
            item["allocated_monthly"] = 0.0
            item["shortfall"] = item["required_monthly"]
        total_allocated = 0.0
        is_fully_funded = total_required == 0.0
        surplus_shortfall = round(total_required, 2)

    return {
        "has_goals": len(goals_detail) > 0,
        "goals_detail": goals_detail,
        "total_required_monthly": round(total_required, 2),
        "total_allocated_monthly": round(total_allocated, 2),
        "is_fully_funded": is_fully_funded,
        "surplus_shortfall": round(surplus_shortfall, 2),
        "status_message": (
            "All goals fully funded from surplus."
            if is_fully_funded
            else f"Goal funding shortfall of ₹{surplus_shortfall:,.2f}/mo. Competing goals require prioritization."
        ),
    }


def generate_budget_recommendations(
    profile_data: Optional[Dict[str, Any]],
    goals: Optional[List[Dict[str, Any]]] = None,
    risk_assessment: Optional[Dict[str, Any]] = None,
    health_score: Optional[Dict[str, Any]] = None,
    current_date: Optional[date] = None,
    debt_already_in_expenses: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Generate practical deterministic budget allocations.
    Does not apply 50/30/20 blindly:
    - Protects necessary living essentials
    - Preserves contractual minimum debt repayments
    - Prioritizes emergency buffer building when coverage < 3-6 months
    - Allocates toward financial goals safely from positive surplus
    - Handles deficits without suggesting impossible allocations exceeding income
    - Prevents double-counting across categories and savings pools
    """
    summary = calculate_financial_summary(profile_data, debt_already_in_expenses=debt_already_in_expenses)
    income = summary["monthly_income"]
    essential = summary["essential_expenses"]
    discretionary = summary["discretionary_expenses"]
    other = summary["other_expenses"]
    debt_repay = summary["monthly_debt_repayment"]
    liquid_savings = summary["savings_liquid"]
    is_deficit = summary["is_deficit"]
    actual_surplus = summary["monthly_surplus"]
    debt_included = summary["debt_already_in_expenses"]

    # 1. Non-negotiable obligations (Essential + Other + Debt Repayments)
    if debt_included:
        non_debt_essential = max(0.0, essential - debt_repay)
        non_negotiable_commitments = non_debt_essential + other + debt_repay
    else:
        non_negotiable_commitments = essential + other + debt_repay

    # 2. Recommended Discretionary Spending Strategy
    notes = []
    if income == 0:
        rec_discretionary = 0.0
        notes.append("Zero income recorded. Budget allocations require recorded take-home pay.")
    elif is_deficit:
        # Deficit analysis
        if non_negotiable_commitments > income:
            # Structural deficit: essential expenses and debt alone exceed income!
            rec_discretionary = 0.0
            structural_gap = non_negotiable_commitments - income
            notes.append(
                f"Structural Deficit Warning: Your essential commitments and debt service (₹{non_negotiable_commitments:,.0f}) "
                f"exceed monthly take-home pay by ₹{structural_gap:,.0f}. Discretionary cuts alone cannot eliminate this deficit."
            )
        else:
            # Deficit caused by discretionary spending: cut discretionary to achieve balance
            available_for_discretionary = income - non_negotiable_commitments
            rec_discretionary = max(0.0, available_for_discretionary * 0.85)  # Leave small 15% buffer
            cut_amount = discretionary - rec_discretionary
            notes.append(
                f"Cash Flow Rebalancing: Discretionary expenses adjusted by ₹{cut_amount:,.0f}/mo "
                "to restore cash flow solvency and eliminate the monthly deficit."
            )
    else:
        # Positive or zero surplus: Optimize discretionary spending without deprivation
        if income > 0 and (discretionary / income) > 0.35:
            # Discretionary is unusually high (> 35% of income): gently trim to 25% of income
            rec_discretionary = income * 0.25
            trim = discretionary - rec_discretionary
            notes.append(
                f"Spending Optimization: Discretionary spending trimmed by ₹{trim:,.0f}/mo "
                "(capped at a sustainable 25% of take-home pay) to accelerate goal funding and emergency reserves."
            )
        else:
            rec_discretionary = discretionary

    rec_discretionary = round(rec_discretionary, 2)
    recommended_outflows = non_negotiable_commitments + rec_discretionary
    budget_surplus = max(0.0, income - recommended_outflows)

    # 3. Emergency Fund Allocation
    is_emergency_provisional = summary.get("is_emergency_provisional", False)
    if is_emergency_provisional:
        notes.append("Provisional: Liquid emergency savings data is unrecorded in profile. Using ₹0 baseline.")

    emergency_months = (liquid_savings / essential) if essential > 0 else 0.0
    rec_emergency_contrib = 0.0
    target_6m_shortfall = max(0.0, (6.0 * essential) - liquid_savings) if essential > 0 else 0.0

    if budget_surplus > 0 and target_6m_shortfall > 0:
        if emergency_months < 1.0:
            # Critical urgency: 50% of available budget surplus
            alloc = budget_surplus * 0.50
            rec_emergency_contrib = min(alloc, target_6m_shortfall)
            notes.append("Emergency Buffer Priority: Allocating 50% of surplus to build a critical 1–3 month liquidity runway.")
        elif emergency_months < 3.0:
            # Moderate urgency: 35% of available budget surplus
            alloc = budget_surplus * 0.35
            rec_emergency_contrib = min(alloc, target_6m_shortfall)
            notes.append("Emergency Cushion: Allocating 35% of surplus toward the baseline 3-month safety guideline.")
        elif emergency_months < 6.0:
            # Finishing buffer: 20% of available budget surplus
            alloc = budget_surplus * 0.20
            rec_emergency_contrib = min(alloc, target_6m_shortfall)
            notes.append("Emergency Resilience: Allocating 20% of surplus to achieve full 6-month financial independence cushion.")

    rec_emergency_contrib = round(rec_emergency_contrib, 2)
    surplus_after_emergency = max(0.0, budget_surplus - rec_emergency_contrib)

    # 4. Financial Goal Allocation (sequential, non-overlapping)
    goal_res = calculate_goal_contributions(goals, surplus_after_emergency, current_date=current_date)
    rec_goals_contrib = goal_res["total_allocated_monthly"]
    surplus_after_goals = max(0.0, surplus_after_emergency - rec_goals_contrib)

    # 5. Long-term Wealth / Extra Investments Allocation
    rec_investment_contrib = round(surplus_after_goals, 2)
    if rec_investment_contrib > 0:
        notes.append(
            f"Wealth Accumulation: Remaining monthly surplus of ₹{rec_investment_contrib:,.0f} "
            "allocated to long-term diversified SIPs and discretionary investment buffers."
        )

    # 6. Build Structured Recommended Budget
    recommended_categories = {
        "Essential Living": {
            "current": round(essential, 2),
            "recommended": round(essential, 2),
            "diff": 0.0,
            "type": "Fixed Need",
        },
        "Discretionary Living": {
            "current": round(discretionary, 2),
            "recommended": rec_discretionary,
            "diff": round(rec_discretionary - discretionary, 2),
            "type": "Flexible Want",
        },
        "Other Expenses": {
            "current": round(other, 2),
            "recommended": round(other, 2),
            "diff": 0.0,
            "type": "Fixed Need",
        },
        "Debt Repayment": {
            "current": round(debt_repay, 2),
            "recommended": round(debt_repay, 2),
            "diff": 0.0,
            "type": "Contractual Obligation",
        },
        "Emergency Savings": {
            "current": 0.0,
            "recommended": rec_emergency_contrib,
            "diff": rec_emergency_contrib,
            "type": "Safety Cushion",
        },
        "Financial Goals": {
            "current": 0.0,
            "recommended": rec_goals_contrib,
            "diff": rec_goals_contrib,
            "type": "Milestone Wealth",
        },
        "Long-Term Investments": {
            "current": 0.0,
            "recommended": rec_investment_contrib,
            "diff": rec_investment_contrib,
            "type": "Future Compounding",
        },
    }

    # Potential savings improvement = (rec_emergency + rec_goals + rec_investments) - max(0, actual_surplus)
    total_new_savings = rec_emergency_contrib + rec_goals_contrib + rec_investment_contrib
    potential_savings_improvement = max(0.0, total_new_savings - max(0.0, actual_surplus))

    return {
        "income": round(income, 2),
        "current_outflows": summary["total_monthly_outflows"],
        "current_surplus": actual_surplus,
        "is_deficit": is_deficit,
        "recommended_outflows": round(recommended_outflows, 2),
        "budget_surplus": round(budget_surplus, 2),
        "recommended_categories": recommended_categories,
        "emergency_allocation": {
            "current_liquid": round(liquid_savings, 2),
            "essential_expenses": round(essential, 2),
            "coverage_months": round(emergency_months, 2),
            "target_months": 6.0,
            "shortfall": round(target_6m_shortfall, 2),
            "recommended_monthly": rec_emergency_contrib,
            "is_provisional": is_emergency_provisional,
            "is_essential_zero": essential == 0.0,
        },
        "goals_allocation": goal_res,
        "potential_savings_improvement": round(potential_savings_improvement, 2),
        "total_savings_and_investments": round(total_new_savings, 2),
        "notes": notes,
    }
