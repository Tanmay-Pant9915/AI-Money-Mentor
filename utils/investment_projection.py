"""
utils/investment_projection.py
Deterministic compound-interest and SIP growth projection utility for AI Money Mentor.
Calculates future values under explicitly stated rate of return and inflation assumptions.
Distinguishes principal investment from compound growth, and compares against 0% return baselines.
"""
from typing import Any, Dict, List, Optional


def project_investment_growth(
    current_savings: float = 0.0,
    monthly_contribution: float = 0.0,
    remaining_months: int = 0,
    assumed_annual_return: float = 0.0,
    contribution_timing: str = "end_of_period",
    annual_inflation_rate: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate deterministic future value projection for lump sum savings plus monthly contributions.

    Args:
        current_savings: Existing corpus saved toward the goal (PV).
        monthly_contribution: Regular monthly SIP contribution amount (PMT).
        remaining_months: Total investment duration in months (n).
        assumed_annual_return: Assumed nominal annualized return in % (e.g. 10.0 for 10% p.a.).
        contribution_timing: 'end_of_period' (ordinary annuity) or 'beginning_of_period' (annuity due).
        annual_inflation_rate: Optional annual inflation rate in % to calculate real purchasing power.

    Returns:
        Structured dictionary with projected FV, principal breakdown, growth, baseline (0% return),
        inflation-adjusted real value, and chronological trajectory data.
    """
    pv = max(0.0, float(current_savings or 0.0))
    pmt = max(0.0, float(monthly_contribution or 0.0))
    n = max(0, int(remaining_months or 0))
    annual_r = float(assumed_annual_return or 0.0)
    inflation_r = max(0.0, float(annual_inflation_rate or 0.0))

    # Guard: duration zero
    if n == 0:
        return {
            "future_value": round(pv, 2),
            "fv_current_savings": round(pv, 2),
            "fv_contributions": 0.0,
            "total_principal_invested": round(pv, 2),
            "total_contributions_paid": 0.0,
            "projected_growth": 0.0,
            "baseline_no_return_fv": round(pv, 2),
            "real_purchasing_power": round(pv, 2),
            "assumed_annual_return": annual_r,
            "monthly_rate": 0.0,
            "annual_inflation_rate": inflation_r,
            "contribution_timing": contribution_timing,
            "remaining_months": 0,
            "trajectory": [{"month": 0, "principal": round(pv, 2), "growth": 0.0, "total_fv": round(pv, 2)}],
            "assumptions_disclaimer": (
                "Returns are projected based on assumed annualized growth and are neither guaranteed nor fixed. "
                "Actual market performance fluctuates and may result in paper drawdowns or negative returns."
            ),
        }

    # Monthly compounding interest rate: r = R / (12 * 100)
    monthly_r = annual_r / (12.0 * 100.0)

    # 1. Future value of existing lump sum savings: FV_pv = PV * (1 + r)^n
    # Guard against negative returns exceeding -100% per month
    if monthly_r <= -1.0:
        fv_savings = 0.0
    else:
        try:
            fv_savings = pv * ((1.0 + monthly_r) ** n)
        except OverflowError:
            fv_savings = pv

    # 2. Future value of regular monthly contributions (SIP)
    if abs(monthly_r) < 1e-12:
        # 0% return edge case: strictly PMT * n
        fv_contrib = pmt * n
    else:
        try:
            compound_factor = ((1.0 + monthly_r) ** n) - 1.0
            fv_contrib_ordinary = pmt * (compound_factor / monthly_r)
            if contribution_timing == "beginning_of_period":
                fv_contrib = fv_contrib_ordinary * (1.0 + monthly_r)
            else:
                fv_contrib = fv_contrib_ordinary
        except OverflowError:
            fv_contrib = pmt * n

    fv_savings = max(0.0, fv_savings)
    fv_contrib = max(0.0, fv_contrib)
    total_fv = fv_savings + fv_contrib

    # Principal vs. Growth Breakdown
    total_contributions = pmt * n
    total_principal = pv + total_contributions
    projected_growth = round(total_fv - total_principal, 2)

    # 0% return baseline (pure savings without growth)
    baseline_fv = total_principal

    # Real purchasing power inflation adjustment: Real FV = Nominal FV / (1 + i)^n
    if inflation_r > 0:
        monthly_inf = inflation_r / (12.0 * 100.0)
        try:
            inf_factor = (1.0 + monthly_inf) ** n
            real_fv = total_fv / inf_factor if inf_factor > 0 else total_fv
        except OverflowError:
            real_fv = total_fv
    else:
        real_fv = total_fv

    # Generate chronological trajectory points (sample points for charts)
    trajectory: List[Dict[str, Any]] = []
    # Determine sample step (every month for <= 36 months, quarterly/annual for longer)
    step = 1 if n <= 36 else (3 if n <= 72 else 6)
    months_to_sample = list(range(0, n + 1, step))
    if n not in months_to_sample:
        months_to_sample.append(n)

    for m in sorted(set(months_to_sample)):
        if m == 0:
            m_fv_pv = pv
            m_fv_pmt = 0.0
            m_principal = pv
        elif abs(monthly_r) < 1e-12:
            m_fv_pv = pv
            m_fv_pmt = pmt * m
            m_principal = pv + (pmt * m)
        else:
            try:
                m_fv_pv = pv * ((1.0 + monthly_r) ** m) if monthly_r > -1.0 else 0.0
                m_factor = ((1.0 + monthly_r) ** m) - 1.0
                m_ord = pmt * (m_factor / monthly_r)
                m_fv_pmt = m_ord * (1.0 + monthly_r) if contribution_timing == "beginning_of_period" else m_ord
            except OverflowError:
                m_fv_pv = pv
                m_fv_pmt = pmt * m
            m_principal = pv + (pmt * m)

        m_total_fv = max(0.0, m_fv_pv + m_fv_pmt)
        m_growth = max(0.0, m_total_fv - m_principal)
        trajectory.append({
            "month": m,
            "year": round(m / 12.0, 1),
            "principal": round(m_principal, 2),
            "growth": round(m_growth, 2),
            "total_fv": round(m_total_fv, 2),
        })

    return {
        "future_value": round(total_fv, 2),
        "fv_current_savings": round(fv_savings, 2),
        "fv_contributions": round(fv_contrib, 2),
        "total_principal_invested": round(total_principal, 2),
        "total_contributions_paid": round(total_contributions, 2),
        "projected_growth": round(projected_growth, 2),
        "baseline_no_return_fv": round(baseline_fv, 2),
        "real_purchasing_power": round(real_fv, 2),
        "assumed_annual_return": annual_r,
        "monthly_rate": round(monthly_r, 6),
        "annual_inflation_rate": inflation_r,
        "contribution_timing": contribution_timing,
        "remaining_months": n,
        "trajectory": trajectory,
        "assumptions_disclaimer": (
            f"Assumes an explicit {annual_r:.1f}% annual return with monthly compounding. "
            "Returns are illustrative projections for educational planning only and are not guaranteed. "
            "Actual mutual fund returns fluctuate with market conditions."
        ),
    }


def calculate_required_contribution_for_target(
    target_amount: float,
    current_savings: float,
    remaining_months: int,
    assumed_annual_return: float = 0.0,
    contribution_timing: str = "end_of_period",
) -> Dict[str, Any]:
    """
    Calculate required monthly contribution to reach target amount given an assumed annual return.
    PMT = (Target - FV_savings) / [ ((1+r)^n - 1) / r ]
    """
    target = max(0.0, float(target_amount or 0.0))
    pv = max(0.0, float(current_savings or 0.0))
    n = max(0, int(remaining_months or 0))
    annual_r = float(assumed_annual_return or 0.0)

    if n <= 0 or target <= 0:
        return {
            "required_monthly": 0.0,
            "required_monthly_contribution": 0.0,
            "fv_savings": round(pv, 2),
            "target_gap_to_fund": 0.0,
            "assumed_annual_return": annual_r,
        }

    monthly_r = annual_r / (12.0 * 100.0)

    # Future value of current savings
    if abs(monthly_r) < 1e-12:
        fv_savings = pv
    else:
        try:
            fv_savings = pv * ((1.0 + monthly_r) ** n) if monthly_r > -1.0 else 0.0
        except OverflowError:
            fv_savings = pv

    gap = max(0.0, target - fv_savings)

    if gap <= 0:
        # Existing savings already compound to reach the target!
        return {
            "required_monthly": 0.0,
            "required_monthly_contribution": 0.0,
            "fv_savings": round(fv_savings, 2),
            "target_gap_to_fund": 0.0,
            "assumed_annual_return": annual_r,
        }

    if abs(monthly_r) < 1e-12:
        required_pmt = gap / n
    else:
        try:
            denom_factor = ((1.0 + monthly_r) ** n) - 1.0
            if contribution_timing == "beginning_of_period":
                denom = (denom_factor / monthly_r) * (1.0 + monthly_r)
            else:
                denom = denom_factor / monthly_r
            required_pmt = (gap / denom) if denom > 0 else (gap / n)
        except (OverflowError, ZeroDivisionError):
            required_pmt = gap / n

    return {
        "required_monthly": round(max(0.0, required_pmt), 2),
        "required_monthly_contribution": round(max(0.0, required_pmt), 2),
        "fv_savings": round(fv_savings, 2),
        "target_gap_to_fund": round(gap, 2),
        "assumed_annual_return": annual_r,
    }
