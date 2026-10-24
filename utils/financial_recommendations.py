"""
utils/financial_recommendations.py
Deterministic financial action prioritization engine for AI Money Mentor.
Orders financial next steps by solvency, obligation integrity, emergency liquidity,
debt alleviation, and milestone goals.
"""
from typing import Any, Dict, List, Optional


def generate_prioritized_financial_actions(
    summary: Dict[str, Any],
    budget: Dict[str, Any],
    goals_data: Optional[Dict[str, Any]] = None,
    risk_assessment: Optional[Dict[str, Any]] = None,
    health_score: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """
    Generate deterministic, rule-based prioritized action items ordered by financial urgency.
    """
    actions: List[Dict[str, str]] = []

    income = summary.get("monthly_income", 0.0)
    surplus = summary.get("monthly_surplus", 0.0)
    is_deficit = summary.get("is_deficit", False)
    dti = summary.get("debt_to_income", 0.0)
    debt_repay = summary.get("monthly_debt_repayment", 0.0)
    outstanding_debt = summary.get("outstanding_debt", 0.0)
    liquid = summary.get("savings_liquid", 0.0)
    essential = summary.get("essential_expenses", 0.0)
    emergency_months = (liquid / essential) if essential > 0 else 0.0

    # 1. PRIORITY 1: Cash Flow Solvency & Deficit Eradication
    if is_deficit:
        non_negotiable = essential + summary.get("other_expenses", 0.0) + debt_repay
        if non_negotiable > income:
            gap = non_negotiable - income
            actions.append({
                "priority": "High",
                "category": "Cash Flow Crisis",
                "title": "Address Structural Monthly Deficit",
                "action": (
                    f"Your fixed living essentials and debt repayments (₹{non_negotiable:,.0f}/mo) exceed take-home pay by ₹{gap:,.0f}/mo. "
                    "Cutting discretionary spending alone cannot eliminate this deficit. Focus immediately on loan restructuring, "
                    "downsizing fixed overhead, or exploring secondary income streams."
                ),
                "rationale": "Sustained deficits force reliance on high-interest credit lines, leading to rapid financial erosion.",
            })
        else:
            disc = summary.get("discretionary_expenses", 0.0)
            actions.append({
                "priority": "High",
                "category": "Cash Flow Rebalancing",
                "title": "Curtail Discretionary Outflows to Eliminate Deficit",
                "action": (
                    f"You are running a monthly deficit of ₹{abs(surplus):,.0f}. Audit current discretionary spending (₹{disc:,.0f}/mo) "
                    f"and cap it at ₹{budget['recommended_categories']['Discretionary Living']['recommended']:,.0f}/mo to restore positive cash flow."
                ),
                "rationale": "Balancing your monthly cash flow is the prerequisite for all savings and investment goals.",
            })

    # 2. PRIORITY 2: Emergency Fund Building
    dependents = summary.get("dependents", 0)
    target_runway_mo = 6.0 if dependents > 0 else 3.0

    if emergency_months < 1.0:
        dep_note = f" (amplified by having {dependents} dependent(s))" if dependents > 0 else ""
        actions.append({
            "priority": "High",
            "category": "Emergency Liquidity",
            "title": "Build a Starter Emergency Cushion (1 Month)",
            "action": (
                f"You currently have {emergency_months:.1f} months of emergency reserves (₹{liquid:,.0f}). "
                f"Prioritize building at least 1 month of essential expenses (₹{essential:,.0f}) in an instant-access liquid mutual fund or sweep-in account{dep_note}."
            ),
            "rationale": "Without a basic cash cushion, any unexpected medical or vehicle bill forces immediate borrowing.",
        })
    elif emergency_months < 3.0:
        dep_clause = f" Given {dependents} dependent(s), your recommended target is a 6-month safety runway." if dependents > 0 else ""
        actions.append({
            "priority": "Medium",
            "category": "Emergency Liquidity",
            "title": "Expand Emergency Reserve to Baseline 3 Months",
            "action": (
                f"Allocate ₹{budget['emergency_allocation']['recommended_monthly']:,.0f}/mo toward emergency savings "
                f"until reaching the baseline ₹{essential * 3:,.0f} (3 months of essential needs).{dep_clause}"
            ),
            "rationale": "Three months of living costs protects against temporary job transitions or localized disruptions.",
        })
    elif emergency_months < 6.0:
        prio_lvl = "Medium" if dependents > 0 else "Low"
        dep_reason = f"Essential protection for your household with {dependents} dependent(s)." if dependents > 0 else "Full 6-month runway provides maximum peace of mind during macroeconomic uncertainties."
        actions.append({
            "priority": prio_lvl,
            "category": "Emergency Liquidity",
            "title": "Top-up Emergency Runway to 6 Months",
            "action": (
                f"Gradually fund the remaining ₹{budget['emergency_allocation']['shortfall']:,.0f} buffer to complete "
                "your 6-month resilience target."
            ),
            "rationale": dep_reason,
        })

    # 3. PRIORITY 3: Debt Management & Payoff Strategy
    if dti > 50.0:
        actions.append({
            "priority": "High",
            "category": "Debt Reduction",
            "title": "Alleviate Critical Debt Burden (DTI > 50%)",
            "action": (
                f"Loan repayments consume {dti:.1f}% of your monthly take-home pay (₹{debt_repay:,.0f}/mo). "
                "Contact lenders to explore tenure extension or consolidation to lower monthly EMIs to sustainable levels."
            ),
            "rationale": "A DTI above 50% severely restricts savings flexibility and increases risk of loan default.",
        })
    elif dti > 36.0:
        actions.append({
            "priority": "Medium",
            "category": "Debt Reduction",
            "title": "Accelerate Debt Reduction (DTI > 36%)",
            "action": (
                f"Debt payments consume {dti:.1f}% of income. Adopt a structured debt payoff plan "
                "(Snowball for quick psychological wins or Avalanche for interest savings). "
                "Note: Because loan interest rates were not provided, debts cannot be ranked by exact APR borrowing cost."
            ),
            "rationale": "Bringing DTI below the conventional 36% lending threshold enhances borrowing power and free cash flow.",
        })
    elif outstanding_debt > 0 and debt_repay == 0:
        actions.append({
            "priority": "High",
            "category": "Debt Servicing",
            "title": "Establish Debt Servicing Plan for Outstanding Liabilities",
            "action": (
                f"You reported ₹{outstanding_debt:,.0f} in outstanding debt balance but ₹0 monthly repayments. "
                "Verify repayment schedules, moratorium conditions, or balloon payment requirements."
            ),
            "rationale": "Unserviced debts accumulate compounding penal interest and severely damage credit scores.",
        })

    # 4. PRIORITY 4: Financial Goal Funding & Competing Trade-offs
    goals_detail = (goals_data or {}).get("goals_detail", [])
    if goals_detail:
        shortfall = (goals_data or {}).get("surplus_shortfall", 0.0)
        if shortfall > 0:
            actions.append({
                "priority": "Medium",
                "category": "Goal Prioritization",
                "title": "Realign Competing Financial Goals",
                "action": (
                    f"Your target goals require ₹{(goals_data or {}).get('total_required_monthly', 0):,.0f}/mo, "
                    f"exceeding affordable surplus by ₹{shortfall:,.0f}/mo. Extend target timelines for lower-urgency goals "
                    "or adjust milestone target amounts to match available surplus."
                ),
                "rationale": "Spreading limited capital too thinly across too many goals risks achieving none of them on time.",
            })
        else:
            actions.append({
                "priority": "Medium",
                "category": "Goal Execution",
                "title": "Automate Systematic Goal Contributions",
                "action": (
                    f"Set up standing instructions on payday totaling ₹{(goals_data or {}).get('total_allocated_monthly', 0):,.0f}/mo "
                    f"across your {len(goals_detail)} active milestone goals."
                ),
                "rationale": "Automating contributions on salary day removes willpower friction and prevents lifestyle creep.",
            })
    else:
        actions.append({
            "priority": "Low",
            "category": "Goal Setting",
            "title": "Define Clear Financial Milestones",
            "action": "Set up tangible milestone goals (e.g., house down payment, education, vehicle) in your Financial Profile.",
            "rationale": "Clear targets with deadlines provide direction and motivation for budgeting discipline.",
        })

    # 5. PRIORITY 5: Long-Term Wealth Accumulation & SIPs
    rec_investments = budget.get("recommended_categories", {}).get("Long-Term Investments", {}).get("recommended", 0.0)
    if not is_deficit and emergency_months >= 1.0 and rec_investments > 0:
        actions.append({
            "priority": "Low",
            "category": "Wealth Building",
            "title": "Deploy Remaining Surplus into Broad-Market SIPs",
            "action": (
                f"Invest your remaining monthly surplus of ₹{rec_investments:,.0f} into diversified, low-cost index "
                "or broad-market flexicap mutual funds."
            ),
            "rationale": "Systematic long-term compounding in equities outpaces inflation and builds multi-year wealth.",
        })

    return actions
