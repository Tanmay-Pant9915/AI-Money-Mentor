"""
utils/money_health_score.py
Deterministic Money Health Scoring Engine for AI Money Mentor.
Evaluates savings rate, debt burden, emergency reserves, investment health,
and goal progress using configurable mathematical scoring curves and weight normalization.
"""
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_WEIGHTS: Dict[str, float] = {
    "savings_rate": 0.25,
    "debt_burden": 0.25,
    "emergency_fund": 0.20,
    "investment_health": 0.20,
    "goal_progress": 0.10,
}

RATING_THRESHOLDS = [
    (0, 39, "Needs Attention", "#ef4444"),
    (40, 59, "Fair", "#f59e0b"),
    (60, 79, "Good", "#3b82f6"),
    (80, 100, "Excellent", "#10b981"),
]


def classify_rating(score: Optional[float]) -> str:
    """Classify overall score into descriptive rating band."""
    if score is None:
        return "Incomplete Data"
    rounded = round(score)
    for low, high, label, _ in RATING_THRESHOLDS:
        if low <= rounded <= high:
            return label
    return "Excellent" if rounded > 100 else "Needs Attention"


def calculate_savings_rate_score(
    income: Optional[float],
    total_expenses: Optional[float],
) -> Dict[str, Any]:
    """
    Evaluate savings rate (%) = (income - total_expenses) / income * 100.
    Scoring curve:
        Deficit (< 0%): 0 points
        0%: 20 points (breaking even)
        0% to 10%: 20 -> 50 points
        10% to 20%: 50 -> 80 points
        20% to 30%: 80 -> 100 points
        >= 30%: 100 points
    """
    if income is None or income <= 0:
        return {
            "name": "Savings Rate",
            "score": 0.0,
            "is_available": False,
            "actual_value": None,
            "display_metric": "Data Unavailable",
            "status": "Unavailable",
            "explanation": "Monthly income is missing, zero, or unrecorded.",
        }

    if total_expenses is None or total_expenses < 0:
        return {
            "name": "Savings Rate",
            "score": 0.0,
            "is_available": False,
            "actual_value": None,
            "display_metric": "Data Unavailable",
            "status": "Unavailable",
            "explanation": "Monthly expense breakdown is incomplete.",
        }

    surplus = income - total_expenses
    savings_rate = (surplus / income) * 100.0

    if surplus < 0:
        score = 0.0
        status = "Deficit"
        explanation = (
            f"You are running a monthly deficit of ₹{abs(surplus):,.2f} "
            f"(Savings rate: {savings_rate:.1f}%). Expenses exceed income."
        )
    elif savings_rate == 0.0:
        score = 20.0
        status = "Breaking Even"
        explanation = "You are saving 0% of income; expenses exactly match take-home pay."
    elif savings_rate <= 10.0:
        score = 20.0 + (savings_rate / 10.0) * (50.0 - 20.0)
        status = "Low"
        explanation = (
            f"Saving {savings_rate:.1f}% of income (₹{surplus:,.2f}/mo). "
            "Building initial savings momentum."
        )
    elif savings_rate <= 20.0:
        score = 50.0 + ((savings_rate - 10.0) / 10.0) * (80.0 - 50.0)
        status = "Moderate"
        explanation = (
            f"Healthy savings rate of {savings_rate:.1f}% (₹{surplus:,.2f}/mo), "
            "approaching standard 20% benchmark."
        )
    elif savings_rate <= 30.0:
        score = 80.0 + ((savings_rate - 20.0) / 10.0) * (100.0 - 80.0)
        status = "Strong"
        explanation = (
            f"Robust savings rate of {savings_rate:.1f}% (₹{surplus:,.2f}/mo). "
            "Well above average retail investor benchmark."
        )
    else:
        score = 100.0
        status = "Exceptional"
        explanation = (
            f"Outstanding savings rate of {savings_rate:.1f}% (₹{surplus:,.2f}/mo). "
            "Enables rapid wealth accumulation and financial freedom."
        )

    score = max(0.0, min(100.0, round(score, 1)))

    return {
        "name": "Savings Rate",
        "score": score,
        "is_available": True,
        "actual_value": round(savings_rate, 2),
        "display_metric": f"{savings_rate:.1f}%",
        "status": status,
        "explanation": explanation,
    }


def calculate_debt_burden_score(
    income: Optional[float],
    monthly_debt_repayment: Optional[float],
    outstanding_debt: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Evaluate debt-to-income (DTI) ratio (%) = monthly_debt_repayment / income * 100.
    Scoring curve:
        DTI 0%: 100 points (debt-free)
        0% to 10%: 100 -> 95 points
        10% to 20%: 95 -> 80 points
        20% to 36%: 80 -> 50 points
        36% to 50%: 50 -> 20 points
        50% to 70%: 20 -> 0 points
        >= 70%: 0 points
    """
    if income is None or income <= 0:
        return {
            "name": "Debt Burden",
            "score": 0.0,
            "is_available": False,
            "actual_value": None,
            "display_metric": "Data Unavailable",
            "status": "Unavailable",
            "explanation": "Monthly income is missing or zero.",
        }

    if monthly_debt_repayment is None:
        return {
            "name": "Debt Burden",
            "score": 0.0,
            "is_available": False,
            "actual_value": None,
            "display_metric": "Data Unavailable",
            "status": "Unavailable",
            "explanation": "Monthly debt repayment details are missing.",
        }

    repayment = max(0.0, float(monthly_debt_repayment))
    total_debt = float(outstanding_debt or 0.0)
    dti = (repayment / income) * 100.0

    if repayment == 0.0:
        if outstanding_debt is None:
            score = 85.0
            status = "Unconfirmed Debt"
            explanation = "Zero monthly debt repayment reported, but total outstanding debt is unrecorded."
        elif total_debt == 0.0:
            score = 100.0
            status = "Debt-Free"
            explanation = "Debt-free: Zero monthly loan EMIs and zero outstanding debt reported."
        else:
            score = 70.0
            status = "Unserviced Debt"
            explanation = (
                f"You reported ₹{total_debt:,.2f} in outstanding debt, but monthly repayment is ₹0. "
                "Ensure repayment obligations are tracked."
            )
    elif dti <= 10.0:
        score = 100.0 - (dti / 10.0) * 5.0
        status = "Minimal Debt"
        explanation = f"Very low debt burden (DTI: {dti:.1f}%). EMIs consume less than 10% of monthly income."
    elif dti <= 20.0:
        score = 95.0 - ((dti - 10.0) / 10.0) * 15.0
        status = "Manageable"
        explanation = f"Comfortable debt load (DTI: {dti:.1f}%). Well within conventional lending safety thresholds."
    elif dti <= 36.0:
        score = 80.0 - ((dti - 20.0) / 16.0) * 30.0
        status = "Moderate"
        explanation = (
            f"Moderate debt burden (DTI: {dti:.1f}%). EMIs approach the standard 36% recommended limit."
        )
    elif dti <= 50.0:
        score = 50.0 - ((dti - 36.0) / 14.0) * 30.0
        status = "Heavy"
        explanation = (
            f"High debt burden (DTI: {dti:.1f}%). EMIs consume over a third of your income, "
            "limiting savings flexibility."
        )
    elif dti <= 70.0:
        score = 20.0 - ((dti - 50.0) / 20.0) * 20.0
        status = "Severe"
        explanation = (
            f"Critical debt stress (DTI: {dti:.1f}%). Over half your income goes toward debt service."
        )
    else:
        score = 0.0
        status = "Critical"
        explanation = (
            f"Extreme debt burden (DTI: {dti:.1f}%). Debt obligations pose severe risk to financial stability."
        )

    score = max(0.0, min(100.0, round(score, 1)))

    return {
        "name": "Debt Burden",
        "score": score,
        "is_available": True,
        "actual_value": round(dti, 2),
        "display_metric": f"{dti:.1f}% DTI",
        "status": status,
        "explanation": explanation,
    }


def calculate_emergency_fund_score(
    savings_liquid: Optional[float],
    essential_expenses: Optional[float],
) -> Dict[str, Any]:
    """
    Evaluate emergency fund coverage = savings_liquid / essential_expenses.
    Scoring curve:
        0 months: 0 points
        0 to 1 month: 0 -> 25 points
        1 to 3 months: 25 -> 60 points
        3 to 6 months: 60 -> 100 points
        >= 6 months: 100 points
    Target range: 3 to 6 months of essential living expenses.
    """
    if essential_expenses is None or essential_expenses <= 0:
        return {
            "name": "Emergency Fund",
            "score": 0.0,
            "is_available": False,
            "actual_value": None,
            "display_metric": "Data Unavailable",
            "status": "Unavailable",
            "explanation": "Essential monthly living expenses are missing or zero.",
        }

    if savings_liquid is None or savings_liquid < 0:
        return {
            "name": "Emergency Fund",
            "score": 0.0,
            "is_available": False,
            "actual_value": None,
            "display_metric": "Data Unavailable",
            "status": "Unavailable",
            "explanation": "Liquid cash / savings data is missing.",
        }

    coverage = savings_liquid / essential_expenses
    target_months = 6.0
    shortfall = max(0.0, (target_months * essential_expenses) - savings_liquid)

    if coverage == 0.0:
        score = 0.0
        status = "No Buffer"
        explanation = (
            "Zero liquid emergency reserves reported. Vulnerable to sudden income disruption or medical expenses."
        )
    elif coverage <= 1.0:
        score = (coverage / 1.0) * 25.0
        status = "Critically Low"
        explanation = (
            f"Emergency buffer covers {coverage:.1f} months (₹{savings_liquid:,.2f}). "
            f"Estimated shortfall to 6-month buffer: ₹{shortfall:,.2f}."
        )
    elif coverage <= 3.0:
        score = 25.0 + ((coverage - 1.0) / 2.0) * (60.0 - 25.0)
        status = "Building"
        explanation = (
            f"Emergency savings cover {coverage:.1f} months. Good progress toward the 3–6 month safety guideline."
        )
    elif coverage <= 6.0:
        score = 60.0 + ((coverage - 3.0) / 3.0) * (100.0 - 60.0)
        status = "Adequate"
        explanation = (
            f"Strong emergency cushion of {coverage:.1f} months (₹{savings_liquid:,.2f}). "
            "Meets standard financial planning guidelines."
        )
    else:
        score = 100.0
        status = "Fully Funded"
        explanation = (
            f"Robust safety cushion of {coverage:.1f} months. Full peace of mind against unforeseen shocks."
        )

    score = max(0.0, min(100.0, round(score, 1)))

    return {
        "name": "Emergency Fund",
        "score": score,
        "is_available": True,
        "actual_value": round(coverage, 2),
        "display_metric": f"{coverage:.1f} Months",
        "status": status,
        "shortfall": round(shortfall, 2),
        "explanation": explanation,
    }


def calculate_investment_health_score(
    existing_investments: Optional[float],
    monthly_income: Optional[float],
    cas_portfolio: Optional[Dict[str, Any]] = None,
    risk_assessment: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Evaluate investment depth, diversification indicators, and alignment with risk profile.
    Rule-based deterministic scoring. Does not assume higher equity is always better.
    """
    investments = float(existing_investments or 0.0)
    has_cas = cas_portfolio is not None and bool(cas_portfolio.get("total_value"))
    has_recorded_investments = existing_investments is not None and existing_investments > 0

    if not has_recorded_investments and not has_cas:
        if existing_investments == 0.0:
            notes = []
            if risk_assessment and risk_assessment.get("classification") == "Aggressive":
                notes.append("Aggressive risk tolerance but zero investment assets deployed")
            note_suffix = f" ({'; '.join(notes)})" if notes else ""
            return {
                "name": "Investment Health",
                "score": 10.0,
                "is_available": True,
                "actual_value": 0.0,
                "display_metric": "₹0 Invested",
                "status": "Not Started",
                "explanation": f"No existing investments reported. Initiating regular SIPs is vital for beating inflation.{note_suffix}",
            }
        return {
            "name": "Investment Health",
            "score": 0.0,
            "is_available": False,
            "actual_value": None,
            "display_metric": "Data Unavailable",
            "status": "Unavailable",
            "explanation": "No investment data recorded. Add investments in your Profile or upload a CAMS CAS PDF.",
        }

    # Total investment capital known
    total_inv = max(investments, float(cas_portfolio.get("total_value", 0.0)) if cas_portfolio else 0.0)

    # Ratio to annual income
    annual_income = (monthly_income or 0.0) * 12.0
    if annual_income > 0:
        ratio = total_inv / annual_income
        if ratio >= 2.0:
            base_score = 100.0
            status = "Exceptional Portfolio"
        elif ratio >= 1.5:
            base_score = 85.0
            status = "Strong Portfolio"
        elif ratio >= 1.0:
            base_score = 75.0
            status = "Substantial"
        elif ratio >= 0.5:
            base_score = 60.0
            status = "Growing"
        elif ratio >= 0.25:
            base_score = 45.0
            status = "Developing"
        else:
            base_score = 30.0
            status = "Starting Out"
    else:
        base_score = 50.0
        status = "Invested"

    # Incorporate CAS portfolio diversification if available
    adjustments = 0.0
    notes = []

    if cas_portfolio:
        fund_count = int(cas_portfolio.get("fund_count", 0))
        if 3 <= fund_count <= 8:
            adjustments += 10.0
            notes.append(f"Well-balanced fund count ({fund_count} schemes)")
        elif fund_count in (1, 2):
            adjustments -= 5.0
            notes.append("High single/dual fund concentration risk")
        elif fund_count > 12:
            adjustments -= 5.0
            notes.append(f"Portfolio clutter ({fund_count} schemes)")

        avg_expense = cas_portfolio.get("avg_expense_ratio")
        if avg_expense is not None and avg_expense <= 1.0:
            adjustments += 5.0
            notes.append(f"Cost-efficient direct funds (Avg Expense: {avg_expense:.2f}%)")

    # Consider risk profile alignment
    if risk_assessment:
        classification = risk_assessment.get("classification")
        if classification == "Aggressive" and total_inv == 0:
            adjustments -= 10.0
            notes.append("Aggressive risk tolerance but zero investment assets deployed")
        elif classification in ("Moderate", "Conservative") and total_inv > 0:
            adjustments += 5.0
            notes.append(f"Investments aligned with {classification} profile")

    final_score = max(10.0, min(100.0, round(base_score + adjustments, 1)))

    summary_note = "; ".join(notes) if notes else "Portfolio accumulation in progress."
    explanation = f"Investments of ₹{total_inv:,.2f}. {summary_note}"

    return {
        "name": "Investment Health",
        "score": final_score,
        "is_available": True,
        "actual_value": round(total_inv, 2),
        "display_metric": f"₹{total_inv:,.0f}",
        "status": status,
        "explanation": explanation,
    }


def calculate_goal_progress_score(
    goals: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Evaluate financial goal progress across recorded milestones.
    Aggregates percentage progress per valid goal.
    """
    if not goals:
        return {
            "name": "Goal Progress",
            "score": 0.0,
            "is_available": False,
            "actual_value": None,
            "display_metric": "No Goals Set",
            "status": "Unavailable",
            "explanation": "No financial goals configured. Set milestone targets in your Financial Profile.",
        }

    valid_progresses = []
    for g in goals:
        target = float(g.get("target_amount") or 0.0)
        saved = max(0.0, float(g.get("current_amount") or 0.0))
        if target > 0:
            pct = min(100.0, (saved / target) * 100.0)
            valid_progresses.append(pct)

    if not valid_progresses:
        return {
            "name": "Goal Progress",
            "score": 0.0,
            "is_available": False,
            "actual_value": None,
            "display_metric": "Invalid Goals",
            "status": "Unavailable",
            "explanation": "Recorded goals have missing or zero target amounts.",
        }

    avg_pct = sum(valid_progresses) / len(valid_progresses)
    score = max(0.0, min(100.0, round(avg_pct, 1)))

    if score == 0.0:
        status = "Just Starting"
        explanation = f"{len(valid_progresses)} goals tracked with 0% saved so far."
    elif score < 30.0:
        status = "Early Progress"
        explanation = f"Average progress of {score:.1f}% across {len(valid_progresses)} milestone goals."
    elif score < 70.0:
        status = "On Track"
        explanation = f"Average progress of {score:.1f}% across {len(valid_progresses)} milestone goals."
    else:
        status = "Advanced Progress"
        explanation = f"Strong average progress of {score:.1f}% toward your targets."

    return {
        "name": "Goal Progress",
        "score": score,
        "is_available": True,
        "actual_value": round(avg_pct, 2),
        "display_metric": f"{score:.1f}% Avg",
        "status": status,
        "explanation": explanation,
    }


def generate_financial_insights(
    components: Dict[str, Dict[str, Any]],
    profile_metrics: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Generate deterministic, rule-based insights based on verified financial metrics.
    """
    insights: List[str] = []

    # 1. Savings & Cash flow
    sav = components.get("savings_rate", {})
    if sav.get("is_available"):
        sav_val = sav.get("actual_value") or 0.0
        if sav_val < 0:
            insights.append("🔴 Monthly expenses exceed your income, leading to a monthly deficit.")
        elif sav_val < 10.0:
            insights.append("🟡 Savings rate is below 10%, limiting funds available for future compounding.")
        elif sav_val >= 25.0:
            insights.append("🟢 Strong savings rate of over 25% provides excellent investment fuel.")

    # 2. Debt Burden
    debt = components.get("debt_burden", {})
    if debt.get("is_available"):
        dti = debt.get("actual_value") or 0.0
        if dti == 0.0 and debt.get("score") == 100.0:
            insights.append("🟢 Fully debt-free: zero EMI obligations leave your full surplus accessible.")
        elif dti > 50.0:
            insights.append("🔴 Debt repayments consume over 50% of your take-home pay (critical debt burden).")
        elif dti > 36.0:
            insights.append("🟡 Debt-to-income ratio exceeds 36%, which lenders view as high risk.")

    # 3. Emergency Fund
    emg = components.get("emergency_fund", {})
    if emg.get("is_available"):
        months = emg.get("actual_value") or 0.0
        if months < 1.0:
            insights.append("🔴 Emergency fund covers less than 1 month of living expenses.")
        elif months < 3.0:
            insights.append("🟡 Emergency fund covers less than the recommended 3-month baseline.")
        elif months >= 6.0:
            insights.append("🟢 Emergency reserve covers 6+ months of living costs, providing robust safety.")

    # 4. Investment & Goals
    inv = components.get("investment_health", {})
    if inv.get("is_available") and inv.get("score", 0.0) <= 30.0:
        insights.append("🟡 Investment accumulation is in early stages relative to your earning capacity.")

    goals = components.get("goal_progress", {})
    if not goals.get("is_available"):
        insights.append("ℹ️ Milestone financial goals are not yet tracked.")

    # 5. Combined Commitments Check (without double-counting)
    if profile_metrics:
        inc = float(profile_metrics.get("monthly_income") or 0.0)
        ess = float(profile_metrics.get("essential_expenses") or 0.0)
        disc = float(profile_metrics.get("discretionary_expenses") or 0.0)
        oth = float(profile_metrics.get("other_expenses") or 0.0)
        d_repay = float(profile_metrics.get("monthly_debt_repayment") or 0.0)
        living = ess + disc + oth
        total_commit = living + d_repay
        if inc > 0 and total_commit > inc and d_repay > 0:
            deficit_amt = total_commit - inc
            insights.append(
                f"⚠️ Combined living expenses (₹{living:,.0f}) and debt repayments (₹{d_repay:,.0f}) "
                f"exceed monthly take-home pay by ₹{deficit_amt:,.0f}. "
                "(Note: Living expenses and debt repayments are tracked distinctly without double-counting)."
            )

    return insights


def generate_prioritized_recommendations(
    components: Dict[str, Dict[str, Any]],
) -> List[Dict[str, str]]:
    """
    Generate prioritized actionable recommendations ranked by the lowest-scoring components.
    """
    recommendations: List[Dict[str, str]] = []

    # Collect available components and sort by score ascending
    ranked = sorted(
        [
            (key, comp)
            for key, comp in components.items()
            if comp.get("is_available") and comp.get("score") is not None
        ],
        key=lambda x: x[1]["score"],
    )

    for key, comp in ranked:
        score = comp["score"]
        if key == "savings_rate" and score < 50.0:
            recommendations.append({
                "area": "Cash Flow Optimization",
                "priority": "High" if score < 20.0 else "Medium",
                "action": "Audit discretionary spending and set an automated monthly savings transfer of at least 15% on payday.",
            })
        elif key == "debt_burden" and score < 60.0:
            recommendations.append({
                "area": "Debt Reduction",
                "priority": "High" if score < 40.0 else "Medium",
                "action": "Prioritize paying down high-interest liabilities using the debt avalanche or snowball method.",
            })
        elif key == "emergency_fund" and score < 60.0:
            recommendations.append({
                "area": "Emergency Liquidity",
                "priority": "High" if score < 25.0 else "Medium",
                "action": "Allocate a portion of monthly surplus to liquid funds or recurring deposits until reaching 3–6 months of essential expenses.",
            })
        elif key == "investment_health" and score < 60.0:
            recommendations.append({
                "area": "Investment Strategy",
                "priority": "Medium",
                "action": "Establish systematic monthly investments (SIPs) in diversified broad-market mutual funds.",
            })
        elif key == "goal_progress" and score < 50.0:
            recommendations.append({
                "area": "Goal Planning",
                "priority": "Low",
                "action": "Map specific monthly SIP contributions directly to target goals to accelerate milestone completion.",
            })

    # If goals or investments are unavailable
    if not components.get("goal_progress", {}).get("is_available"):
        recommendations.append({
            "area": "Milestone Setting",
            "priority": "Low",
            "action": "Set up tangible financial goals (e.g. emergency fund, house downpayment) in your Financial Profile.",
        })

    return recommendations[:4]  # Return top 4 prioritized actions


def calculate_money_health_score(
    profile_data: Optional[Dict[str, Any]],
    goals: Optional[List[Dict[str, Any]]] = None,
    risk_assessment: Optional[Dict[str, Any]] = None,
    cas_portfolio: Optional[Dict[str, Any]] = None,
    custom_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Main orchestration function to calculate Money Health Score.
    Handles weight normalization for missing components and returns structured diagnostics.
    """
    weights = custom_weights or DEFAULT_WEIGHTS

    if not profile_data:
        return {
            "overall_score": None,
            "rating": "Incomplete Data",
            "is_sufficient_data": False,
            "data_completeness": 0.0,
            "components": {},
            "excluded_components": list(weights.keys()),
            "insights": ["Profile data is missing. Please create your Financial Profile first."],
            "recommendations": [{
                "area": "Profile Setup",
                "priority": "High",
                "action": "Complete your basic Financial Profile to unlock your Money Health Score.",
            }],
            "disclaimer": _get_disclaimer(),
        }

    # Extract metrics safely
    income = profile_data.get("monthly_income")
    essential = profile_data.get("essential_expenses")
    discretionary = profile_data.get("discretionary_expenses") or 0.0
    other = profile_data.get("other_expenses") or 0.0
    raw_debt_repay = profile_data.get("monthly_debt_repayment")
    debt_repay = float(raw_debt_repay or 0.0)

    # Living expenses exclude debt repayments to prevent double-counting
    living_expenses = (
        (essential + discretionary + other)
        if essential is not None
        else None
    )

    # Total expenses = living expenses + monthly debt repayments
    total_expenses = (
        (living_expenses + debt_repay)
        if living_expenses is not None
        else None
    )

    savings_liquid = profile_data.get("savings_liquid")
    outstanding_debt = profile_data.get("outstanding_debt")
    existing_investments = profile_data.get("existing_investments")

    # Evaluate individual components
    c_savings = calculate_savings_rate_score(income, total_expenses)
    c_debt = calculate_debt_burden_score(income, raw_debt_repay, outstanding_debt)
    c_emg = calculate_emergency_fund_score(savings_liquid, essential)
    c_inv = calculate_investment_health_score(existing_investments, income, cas_portfolio, risk_assessment)
    c_goals = calculate_goal_progress_score(goals or profile_data.get("goals"))

    components = {
        "savings_rate": c_savings,
        "debt_burden": c_debt,
        "emergency_fund": c_emg,
        "investment_health": c_inv,
        "goal_progress": c_goals,
    }

    # Weight normalization
    available_weight_sum = 0.0
    weighted_score_sum = 0.0
    excluded_components = []

    for key, comp in components.items():
        w = weights.get(key, 0.20)
        comp["weight"] = w
        if comp["is_available"] and comp["score"] is not None:
            available_weight_sum += w
            weighted_score_sum += comp["score"] * w
            comp["weighted_contribution"] = round(comp["score"] * w, 2)
        else:
            comp["weighted_contribution"] = 0.0
            excluded_components.append(comp["name"])

    data_completeness = round(available_weight_sum * 100.0, 1)

    # Require at least 40% data completeness for a reliable overall score
    is_sufficient_data = available_weight_sum >= 0.40 and (income is not None and income > 0)

    if is_sufficient_data and available_weight_sum > 0:
        # Normalize weights so available components sum to 100%
        normalized_overall_score = round(weighted_score_sum / available_weight_sum)
        normalized_overall_score = max(0, min(100, normalized_overall_score))
        rating = classify_rating(normalized_overall_score)
    else:
        normalized_overall_score = None
        rating = "Incomplete Data"

    insights = generate_financial_insights(components, profile_data.get("metrics") or profile_data)
    recommendations = generate_prioritized_recommendations(components)

    return {
        "overall_score": normalized_overall_score,
        "rating": rating,
        "is_sufficient_data": is_sufficient_data,
        "data_completeness": data_completeness,
        "components": components,
        "excluded_components": excluded_components,
        "insights": insights,
        "recommendations": recommendations,
        "disclaimer": _get_disclaimer(),
    }


def _get_disclaimer() -> str:
    return (
        "Educational Financial Health Notice: The Money Health Score is a deterministic educational indicator "
        "designed to highlight personal finance patterns and general best practices. It does not constitute official "
        "SEBI investment advice, credit scoring, or a guarantee of investment results. Actual financial planning should "
        "be customized to your individual tax status and personal goals."
    )
