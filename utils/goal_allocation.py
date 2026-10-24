"""
utils/goal_allocation.py
Deterministic, risk-aware, and time-horizon-aligned category-level asset allocation engine.
Produces 100% normalized allocations across broad asset classes with educational rationale.
Separates psychological risk tolerance from objective financial risk capacity.
"""
from typing import Any, Dict, List, Optional

ASSET_CLASSES = [
    {
        "key": "liquid_savings",
        "name": "Liquid Reserves & Savings",
        "role": "Capital Preservation & Instant Liquidity",
        "instruments": "Savings bank accounts, overnight & instant-access liquid mutual funds",
        "risk_level": "Lowest Risk",
    },
    {
        "key": "fixed_deposits",
        "name": "Fixed Deposits & Low-Volatility Debt",
        "role": "Predictable Capital Shielding",
        "instruments": "Bank fixed deposits (DICGC insured up to ₹5L), ultra-short debt funds",
        "risk_level": "Low Risk",
    },
    {
        "key": "debt_funds",
        "name": "Debt-Oriented Mutual Funds",
        "role": "Accrual Yield & Low-Duration Fixed Income",
        "instruments": "Corporate bond funds, banking & PSU debt funds, short duration funds",
        "risk_level": "Low-to-Moderate Risk (Subject to credit & duration risk)",
    },
    {
        "key": "hybrid_funds",
        "name": "Hybrid & Multi-Asset Categories",
        "role": "Dynamic Volatility Cushion & Moderate Growth",
        "instruments": "Balanced advantage funds (dynamic asset allocation), aggressive hybrid, multi-asset allocation funds",
        "risk_level": "Moderate Risk",
    },
    {
        "key": "equity_funds",
        "name": "Equity-Oriented Mutual Funds",
        "role": "Long-Term Inflation-Beating Capital Growth",
        "instruments": "Broad-market index funds (Nifty 50, Nifty Next 50), flexicap and diversified equity funds",
        "risk_level": "High Risk (Subject to short-term market volatility)",
    },
]


def determine_horizon_category(remaining_months: int) -> str:
    """Classify investment horizon into Short-Term, Medium-Term, or Long-Term."""
    if remaining_months <= 36:
        return "Short-Term (< 3 Years)"
    elif remaining_months <= 60:
        return "Medium-Term (3–5 Years)"
    else:
        return "Long-Term (5+ Years)"


def generate_goal_asset_allocation(
    remaining_months: int,
    risk_classification: Optional[str] = None,
    capacity_score: Optional[float] = None,
    tolerance_score: Optional[float] = None,
    is_deficit: bool = False,
    goal_priority: str = "Medium",
    assumed_return_override: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Generate deterministic educational category-level asset allocation totaling exactly 100%.

    Args:
        remaining_months: Months remaining until goal target date.
        risk_classification: User risk profile ('Conservative', 'Moderate', 'Aggressive', or None).
        capacity_score: Objective financial risk capacity (0–100 scale).
        tolerance_score: Psychological risk tolerance (0–100 scale).
        is_deficit: True if user currently operates in a monthly cash-flow deficit.
        goal_priority: 'High', 'Medium', or 'Low'.
        assumed_return_override: Optional custom annual return assumption.

    Returns:
        Structured dictionary with normalized percentages totaling 100%, expected blended return,
        guardrails applied, and educational rationales for each asset class.
    """
    months = max(0, int(remaining_months or 0))
    horizon_category = determine_horizon_category(months)

    # Normalize risk profile (default to Moderate if unrecorded)
    norm_risk = str(risk_classification or "Moderate").strip().capitalize()
    if norm_risk not in ["Conservative", "Moderate", "Aggressive"]:
        norm_risk = "Moderate"

    guardrails: List[str] = []

    # Capacity Guardrail: If user is classified as Aggressive, but their objective capacity
    # to absorb drawdowns is low (capacity_score < 40, cash flow deficit, or High priority short goal),
    # cap the profile at Moderate or Conservative to safeguard essential needs.
    effective_risk = norm_risk
    if norm_risk == "Aggressive":
        if is_deficit:
            effective_risk = "Conservative"
            guardrails.append(
                "Cash-Flow Deficit Guardrail: Operating with a monthly cash-flow deficit restricts aggressive market exposure. "
                "Capped at Conservative allocation to preserve capital."
            )
        elif capacity_score is not None and capacity_score < 40:
            effective_risk = "Moderate"
            guardrails.append(
                f"Financial Capacity Guardrail: Your objective risk capacity score ({capacity_score:.0f}/100) is low relative "
                "to your psychological tolerance. Equity exposure moderated to protect essential capital."
            )

    if goal_priority.capitalize() == "High" and months <= 48 and effective_risk == "Aggressive":
        effective_risk = "Moderate"
        guardrails.append(
            "High Goal Priority Protection: For vital goals due in under 4 years, high equity volatility risks timing shortfalls. "
            "Allocation adjusted toward capital preservation."
        )

    # Allocation Policy Table: defines baseline raw percentages based on (Horizon, Effective Risk)
    # Categories: [liquid_savings, fixed_deposits, debt_funds, hybrid_funds, equity_funds]
    if months <= 12:
        # Ultra-short (< 1 year): Zero equity exposure. Strictly liquid and guaranteed preservation.
        raw_alloc = {
            "liquid_savings": 50,
            "fixed_deposits": 40,
            "debt_funds": 10,
            "hybrid_funds": 0,
            "equity_funds": 0,
        }
        suggested_return = 6.0
        horizon_rationale = (
            "With less than 12 months remaining, zero market risk is recommended. "
            "Capital preservation in liquid reserves and bank deposits ensures funds are intact on deadline day."
        )
    elif months <= 36:
        # Short-term (1–3 years): Capital preservation primary. Minor hybrid/debt buffer.
        if effective_risk == "Conservative":
            raw_alloc = {"liquid_savings": 30, "fixed_deposits": 50, "debt_funds": 20, "hybrid_funds": 0, "equity_funds": 0}
            suggested_return = 6.5
        elif effective_risk == "Moderate":
            raw_alloc = {"liquid_savings": 20, "fixed_deposits": 40, "debt_funds": 30, "hybrid_funds": 10, "equity_funds": 0}
            suggested_return = 7.0
        else:  # Aggressive
            raw_alloc = {"liquid_savings": 15, "fixed_deposits": 35, "debt_funds": 35, "hybrid_funds": 15, "equity_funds": 0}
            suggested_return = 7.5

        horizon_rationale = (
            "For a 1–3 year horizon, direct equity exposure is avoided because a market correction could destroy capital "
            "without sufficient recovery time. Focus on stable deposits and accrual debt."
        )
    elif months <= 60:
        # Medium-term (3–5 years): Hybrid and balanced allocations.
        if effective_risk == "Conservative":
            raw_alloc = {"liquid_savings": 10, "fixed_deposits": 40, "debt_funds": 35, "hybrid_funds": 15, "equity_funds": 0}
            suggested_return = 7.5
        elif effective_risk == "Moderate":
            raw_alloc = {"liquid_savings": 10, "fixed_deposits": 25, "debt_funds": 35, "hybrid_funds": 20, "equity_funds": 10}
            suggested_return = 8.5
        else:  # Aggressive
            raw_alloc = {"liquid_savings": 5, "fixed_deposits": 15, "debt_funds": 30, "hybrid_funds": 30, "equity_funds": 20}
            suggested_return = 9.5

        horizon_rationale = (
            "Over a 3–5 year runway, balanced hybrid funds provide modest inflation-hedging while high debt/deposit buffers "
            "shield against sharp downside moves near redemption."
        )
    else:
        # Long-term (> 5 years / 60+ months): Equity compounding runway
        if effective_risk == "Conservative":
            raw_alloc = {"liquid_savings": 5, "fixed_deposits": 20, "debt_funds": 35, "hybrid_funds": 20, "equity_funds": 20}
            suggested_return = 9.0
        elif effective_risk == "Moderate":
            raw_alloc = {"liquid_savings": 5, "fixed_deposits": 10, "debt_funds": 25, "hybrid_funds": 20, "equity_funds": 40}
            suggested_return = 11.0
        else:  # Aggressive
            raw_alloc = {"liquid_savings": 5, "fixed_deposits": 5, "debt_funds": 15, "hybrid_funds": 15, "equity_funds": 60}
            suggested_return = 12.0

        horizon_rationale = (
            "With over 5 years of compounding runway, disciplined equity exposure outpaces inflation. "
            "Short-term market drawdowns are tolerated for multi-year wealth accumulation."
        )

    # Rounding and exact 100% total verification
    total_raw = sum(raw_alloc.values())
    if total_raw != 100:
        # Normalize strictly to 100%
        normalized = {}
        curr_sum = 0
        keys = list(raw_alloc.keys())
        for k in keys[:-1]:
            pct = round((raw_alloc[k] / total_raw) * 100.0)
            normalized[k] = pct
            curr_sum += pct
        normalized[keys[-1]] = 100 - curr_sum
        raw_alloc = normalized

    # Rationales for each asset class
    class_rationales = {
        "liquid_savings": (
            "Provides immediate access to cash with zero volatility, ideal for short-term liquidity buffers."
        ),
        "fixed_deposits": (
            "Guarantees predictable capital protection and shields accumulated savings from market corrections."
        ),
        "debt_funds": (
            "Generates steady bond accrual yield with modest duration risk, superior to simple savings accounts."
        ),
        "hybrid_funds": (
            "Dynamically balances debt and equity to participate in market upside with automated downside cushion."
        ),
        "equity_funds": (
            "Drives long-term purchasing power expansion and beats inflation through broad Indian index and flexicap compounding."
        ),
    }

    allocations: Dict[str, Dict[str, Any]] = {}
    category_breakdown = []
    for ac in ASSET_CLASSES:
        k = ac["key"]
        pct = raw_alloc.get(k, 0)
        item_data = {
            "key": k,
            "category": ac["name"],
            "percentage": pct,
            "role": ac["role"],
            "instruments": ac["instruments"],
            "risk_level": ac["risk_level"],
            "rationale": class_rationales.get(k, ""),
        }
        allocations[k] = item_data
        category_breakdown.append(item_data)

    blended_return = (
        assumed_return_override if assumed_return_override is not None else suggested_return
    )

    return {
        "remaining_months": months,
        "horizon_category": horizon_category,
        "user_risk_classification": norm_risk,
        "effective_risk_classification": effective_risk,
        "effective_risk": effective_risk,
        "guardrails_applied": guardrails,
        "allocations": allocations,
        "raw_percentages": raw_alloc,
        "category_breakdown": category_breakdown,
        "expected_return_benchmark": blended_return,
        "suggested_annual_return": blended_return,
        "horizon_rationale": horizon_rationale,
        "educational_notice": (
            "Educational Asset Allocation Notice: Category percentages are illustrative educational guidelines "
            "based on historical risk-return dynamics. They do not constitute SEBI-registered portfolio advice, "
            "nor do they guarantee that your financial goal target will be achieved. Debt mutual funds carry credit "
            "and interest-rate risks and are not insured like bank deposits."
        ),
    }
