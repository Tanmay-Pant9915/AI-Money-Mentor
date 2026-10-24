"""
utils/retirement_calculator.py
Deterministic mathematical calculations for retirement planning in AI Money Mentor.
Includes inflation adjustment of expenses, required retirement corpus calculation
(both simplified withdrawal-rate baseline and detailed growing-annuity cash flows with pension),
accumulation projections, required monthly contributions, and retirement decumulation schedules.
"""
from typing import Any, Dict, List, Optional, Tuple


def calculate_inflation_adjusted_expenses(
    monthly_expenses_today: float,
    annual_inflation_rate: float,
    years_until_retirement: float,
    is_already_future_rupees: bool = False,
) -> Dict[str, Any]:
    """
    Calculate inflation-adjusted monthly and annual expenses at the retirement date.

    Formula:
        Future Monthly Expenses = E * (1 + i)^t
        Future Annual Expenses = 12 * Future Monthly Expenses

    Args:
        monthly_expenses_today: Current estimated monthly living expense in today's INR.
        annual_inflation_rate: Expected annual inflation rate in % (e.g. 6.0 for 6%).
        years_until_retirement: Number of years remaining until retirement (t).
        is_already_future_rupees: If True, inputs are already in future rupees; do not inflate twice.

    Returns:
        Dictionary with nominal and today's value figures, inflation multiplier, and assumptions.
    """
    e_today = max(0.0, float(monthly_expenses_today or 0.0))
    inf_rate = max(0.0, float(annual_inflation_rate or 0.0))
    t = max(0.0, float(years_until_retirement or 0.0))

    if is_already_future_rupees or t == 0.0 or inf_rate == 0.0:
        multiplier = 1.0
        monthly_at_retirement = e_today
    else:
        i = inf_rate / 100.0
        multiplier = (1.0 + i) ** t
        monthly_at_retirement = e_today * multiplier

    annual_today = e_today * 12.0
    annual_at_retirement = monthly_at_retirement * 12.0

    return {
        "monthly_expenses_today": round(e_today, 2),
        "annual_expenses_today": round(annual_today, 2),
        "monthly_expenses_at_retirement": round(monthly_at_retirement, 2),
        "annual_expenses_at_retirement": round(annual_at_retirement, 2),
        "inflation_multiplier": round(multiplier, 4),
        "annual_inflation_rate": inf_rate,
        "years_until_retirement": t,
        "is_already_future_rupees": is_already_future_rupees,
        "assumptions": [
            f"Annual inflation assumption: {inf_rate:.1f}% compounded annually.",
            f"Time horizon to retirement: {t:.1f} years.",
            "Living expenses are assumed to adjust annually with inflation.",
        ],
    }


def calculate_retirement_corpus(
    annual_expenses_at_retirement: float,
    retirement_duration_years: int,
    post_retirement_annual_return: float = 7.0,
    annual_inflation_rate: float = 6.0,
    annual_pension_at_retirement: float = 0.0,
    is_pension_inflation_indexed: bool = False,
    safe_withdrawal_rate: float = 4.0,
) -> Dict[str, Any]:
    """
    Calculate required retirement corpus using both:
      1. Approach 1 (Simplified baseline): Net Annual Expenses / SWR
      2. Approach 2 (Detailed growing annuity cash flow model):
         Discounted starting corpus needed to fund inflation-growing withdrawals
         over the retirement duration net of pension income.

    Args:
        annual_expenses_at_retirement: Expected gross living expenses in year 1 of retirement.
        retirement_duration_years: Expected duration of retirement in years (e.g. 25-35 years).
        post_retirement_annual_return: Assumed annualized investment return during retirement (%).
        annual_inflation_rate: Expected annual inflation rate during retirement (%).
        annual_pension_at_retirement: Reliable annual pension or guaranteed income in year 1.
        is_pension_inflation_indexed: Whether pension increases with inflation or is fixed nominal.
        safe_withdrawal_rate: Configurable annual withdrawal rate baseline (default 4.0%).

    Returns:
        Structured dictionary with simplified corpus, detailed corpus, cash-flow schedule, and notes.
    """
    exp_y1 = max(0.0, float(annual_expenses_at_retirement or 0.0))
    duration = max(1, int(retirement_duration_years or 1))
    r_post = float(post_retirement_annual_return or 0.0)
    inf_rate = max(0.0, float(annual_inflation_rate or 0.0))
    pension_y1 = max(0.0, float(annual_pension_at_retirement or 0.0))
    swr = max(0.1, float(safe_withdrawal_rate or 4.0))

    # Net annual withdrawal required from investment portfolio in Year 1
    net_expense_y1 = max(0.0, exp_y1 - pension_y1)

    # 1. Approach 1: Simplified SWR Baseline
    swr_decimal = swr / 100.0
    simplified_corpus = round(net_expense_y1 / swr_decimal, 2) if swr_decimal > 0 else 0.0

    # 2. Approach 2: Detailed Growing Annuity Cash Flow Model
    # We simulate year-by-year cash flow from t=1 to duration.
    # At beginning of Year t, net expenses are withdrawn. The remaining balance earns r_post.
    # We solve for the exact starting corpus using present-value discounting:
    # PV = sum_{t=0}^{duration-1} [ NetWithdrawal(t) / (1 + r)^t ]
    r_dec = r_post / 100.0
    i_dec = inf_rate / 100.0

    detailed_pv = 0.0
    cash_flows: List[Dict[str, Any]] = []
    
    # Pre-calculate year-by-year net withdrawals discounted to retirement date
    for year_idx in range(duration):
        # Gross expenses grow with inflation: E_t = E_1 * (1 + i)^t
        gross_exp_t = exp_y1 * ((1.0 + i_dec) ** year_idx)

        # Pension: inflation-indexed or fixed nominal
        if is_pension_inflation_indexed:
            pension_t = pension_y1 * ((1.0 + i_dec) ** year_idx)
        else:
            pension_t = pension_y1

        net_withdrawal_t = max(0.0, gross_exp_t - pension_t)

        # Discount factor for beginning-of-year withdrawal:
        # Year 0 withdrawal happens at t=0 (no discount: factor = 1.0)
        # Year t withdrawal discounted by (1 + r_post)^t
        if r_dec <= -1.0:
            disc_factor = 1.0
        else:
            try:
                disc_factor = 1.0 / ((1.0 + r_dec) ** year_idx)
            except (OverflowError, ZeroDivisionError):
                disc_factor = 1.0

        pv_withdrawal_t = net_withdrawal_t * disc_factor
        detailed_pv += pv_withdrawal_t

    detailed_corpus = round(max(0.0, detailed_pv), 2)

    # Generate complete year-by-year schedule starting with detailed_corpus
    current_balance = detailed_corpus
    for year_idx in range(duration):
        start_bal = current_balance
        gross_exp_t = exp_y1 * ((1.0 + i_dec) ** year_idx)
        pension_t = pension_y1 * ((1.0 + i_dec) ** year_idx) if is_pension_inflation_indexed else pension_y1
        net_withdrawal_t = min(start_bal, max(0.0, gross_exp_t - pension_t))
        bal_after_withdrawal = max(0.0, start_bal - net_withdrawal_t)
        investment_earnings = bal_after_withdrawal * r_dec if r_dec > -1.0 else 0.0
        end_bal = max(0.0, bal_after_withdrawal + investment_earnings)
        current_balance = end_bal

        cash_flows.append({
            "year": year_idx + 1,
            "starting_balance": round(start_bal, 2),
            "gross_expenses": round(gross_exp_t, 2),
            "pension_income": round(pension_t, 2),
            "net_withdrawal": round(net_withdrawal_t, 2),
            "investment_earnings": round(investment_earnings, 2),
            "ending_balance": round(end_bal, 2),
        })

    # Net real return rate: ((1 + R) / (1 + i)) - 1
    real_rate = ((1.0 + r_dec) / (1.0 + i_dec) - 1.0) * 100.0 if (1.0 + i_dec) > 0 else (r_post - inf_rate)

    return {
        "annual_expenses_at_retirement": round(exp_y1, 2),
        "annual_pension_at_retirement": round(pension_y1, 2),
        "net_annual_withdrawal_year_1": round(net_expense_y1, 2),
        "retirement_duration_years": duration,
        "post_retirement_annual_return": r_post,
        "annual_inflation_rate": inf_rate,
        "real_return_in_retirement": round(real_rate, 2),
        "safe_withdrawal_rate": swr,
        "simplified_corpus": simplified_corpus,
        "detailed_corpus": detailed_corpus,
        "recommended_target_corpus": detailed_corpus if duration > 0 else simplified_corpus,
        "is_pension_inflation_indexed": is_pension_inflation_indexed,
        "cash_flow_schedule": cash_flows,
        "assumptions": [
            f"Simplified baseline uses {swr:.1f}% annual withdrawal rate.",
            f"Detailed model assumes {r_post:.1f}% annualized return and {inf_rate:.1f}% inflation over {duration} years.",
            f"Net real portfolio return during retirement: {real_rate:.2f}% p.a.",
            (
                "Pension income is assumed to increase with inflation annually."
                if is_pension_inflation_indexed and pension_y1 > 0
                else (
                    "Pension income is assumed fixed in nominal rupees (purchasing power declines with inflation)."
                    if pension_y1 > 0
                    else "No pension or reliable retirement income assumed."
                )
            ),
            "Withdrawals are assumed to occur at the beginning of each retirement year.",
        ],
    }


def calculate_monthly_effective_rate(annual_rate_percent: float) -> float:
    """
    Convert an effective annual return (R) to its equivalent monthly effective return (r).
    Formula: r = (1 + R)^(1/12) - 1
    """
    R = float(annual_rate_percent or 0.0) / 100.0
    if R <= -1.0:
        return -1.0
    return ((1.0 + R) ** (1.0 / 12.0)) - 1.0


def calculate_retirement_accumulation(
    current_corpus: float,
    monthly_contribution: float,
    years_until_retirement: float,
    assumed_annual_return: float,
    contribution_timing: str = "end_of_period",
) -> Dict[str, Any]:
    """
    Deterministic accumulation calculator projecting retirement corpus at retirement age.
    Uses documented monthly effective compounding: r = (1 + R)^(1/12) - 1.

    Args:
        current_corpus: Existing lump sum investment savings (PV).
        monthly_contribution: Regular monthly contribution/SIP (PMT).
        years_until_retirement: Years remaining until retirement date (t).
        assumed_annual_return: Annualized return in % (R).
        contribution_timing: 'end_of_period' (ordinary annuity) or 'beginning_of_period' (annuity due).

    Returns:
        Structured dictionary with FV of existing savings, FV of contributions, total FV,
        principal invested, growth, and chronological trajectory.
    """
    pv = max(0.0, float(current_corpus or 0.0))
    pmt = max(0.0, float(monthly_contribution or 0.0))
    t = max(0.0, float(years_until_retirement or 0.0))
    months = int(round(t * 12.0))
    annual_r = float(assumed_annual_return or 0.0)

    if months <= 0:
        return {
            "future_value": round(pv, 2),
            "fv_existing_corpus": round(pv, 2),
            "fv_contributions": 0.0,
            "total_principal_invested": round(pv, 2),
            "total_contributions_paid": 0.0,
            "projected_growth": 0.0,
            "baseline_no_return_fv": round(pv, 2),
            "years_until_retirement": 0.0,
            "total_months": 0,
            "assumed_annual_return": annual_r,
            "monthly_rate": 0.0,
            "trajectory": [{"year": 0.0, "month": 0, "principal": round(pv, 2), "growth": 0.0, "total_fv": round(pv, 2)}],
        }

    monthly_r = calculate_monthly_effective_rate(annual_r)

    # 1. FV of existing lump sum: PV * (1 + monthly_r)^n
    if monthly_r <= -1.0:
        fv_pv = 0.0
    elif abs(monthly_r) < 1e-12:
        fv_pv = pv
    else:
        try:
            fv_pv = pv * ((1.0 + monthly_r) ** months)
        except OverflowError:
            fv_pv = pv

    # 2. FV of monthly contributions (SIP)
    if abs(monthly_r) < 1e-12:
        fv_pmt = pmt * months
    else:
        try:
            compound_factor = ((1.0 + monthly_r) ** months) - 1.0
            fv_pmt_ordinary = pmt * (compound_factor / monthly_r)
            if contribution_timing == "beginning_of_period":
                fv_pmt = fv_pmt_ordinary * (1.0 + monthly_r)
            else:
                fv_pmt = fv_pmt_ordinary
        except OverflowError:
            fv_pmt = pmt * months

    fv_pv = max(0.0, fv_pv)
    fv_pmt = max(0.0, fv_pmt)
    total_fv = fv_pv + fv_pmt

    total_contributions = pmt * months
    total_principal = pv + total_contributions
    projected_growth = round(total_fv - total_principal, 2)
    baseline_fv = round(total_principal, 2)

    # Trajectory points sampled annually
    trajectory: List[Dict[str, Any]] = []
    sample_months = sorted(set(list(range(0, months + 1, 12)) + [months]))
    for m in sample_months:
        if m == 0:
            m_fv = pv
            m_prin = pv
        elif abs(monthly_r) < 1e-12:
            m_prin = pv + (pmt * m)
            m_fv = m_prin
        else:
            try:
                m_pv = pv * ((1.0 + monthly_r) ** m) if monthly_r > -1.0 else 0.0
                m_cfactor = ((1.0 + monthly_r) ** m) - 1.0
                m_ord = pmt * (m_cfactor / monthly_r)
                m_pmt = m_ord * (1.0 + monthly_r) if contribution_timing == "beginning_of_period" else m_ord
                m_fv = max(0.0, m_pv + m_pmt)
            except OverflowError:
                m_fv = pv + (pmt * m)
            m_prin = pv + (pmt * m)

        m_growth = max(0.0, m_fv - m_prin) if m_fv >= m_prin else (m_fv - m_prin)
        trajectory.append({
            "month": m,
            "year": round(m / 12.0, 1),
            "principal": round(m_prin, 2),
            "growth": round(m_growth, 2),
            "total_fv": round(m_fv, 2),
        })

    return {
        "future_value": round(total_fv, 2),
        "fv_existing_corpus": round(fv_pv, 2),
        "fv_contributions": round(fv_pmt, 2),
        "total_principal_invested": round(total_principal, 2),
        "total_contributions_paid": round(total_contributions, 2),
        "projected_growth": projected_growth,
        "baseline_no_return_fv": baseline_fv,
        "years_until_retirement": t,
        "total_months": months,
        "assumed_annual_return": annual_r,
        "monthly_rate": round(monthly_r, 6),
        "contribution_timing": contribution_timing,
        "trajectory": trajectory,
    }


def calculate_required_monthly_contribution(
    target_corpus: float,
    current_corpus: float,
    years_until_retirement: float,
    assumed_annual_return: float,
    contribution_timing: str = "end_of_period",
) -> Dict[str, Any]:
    """
    Calculate the monthly investment contribution needed to achieve target retirement corpus.
    Formula:
        Target Gap = Target Corpus - FV(current_corpus)
        Required PMT = Target Gap / [ ((1+r)^n - 1) / r ]

    Args:
        target_corpus: Required corpus at retirement.
        current_corpus: Existing savings already accumulated.
        years_until_retirement: Years remaining until retirement date (t).
        assumed_annual_return: Annual return assumption in % (R).
        contribution_timing: 'end_of_period' or 'beginning_of_period'.

    Returns:
        Structured dictionary with required monthly contribution, gap, and zero-return baseline.
    """
    target = max(0.0, float(target_corpus or 0.0))
    pv = max(0.0, float(current_corpus or 0.0))
    t = max(0.0, float(years_until_retirement or 0.0))
    months = int(round(t * 12.0))
    annual_r = float(assumed_annual_return or 0.0)

    if months <= 0:
        gap = max(0.0, target - pv)
        return {
            "required_monthly": round(gap, 2),
            "required_monthly_contribution": round(gap, 2),
            "target_gap_to_fund": round(gap, 2),
            "fv_existing_corpus": round(pv, 2),
            "is_horizon_zero": True,
            "zero_return_required_monthly": round(gap, 2),
            "assumed_annual_return": annual_r,
        }

    monthly_r = calculate_monthly_effective_rate(annual_r)

    # FV of current corpus
    if abs(monthly_r) < 1e-12:
        fv_pv = pv
    else:
        try:
            fv_pv = pv * ((1.0 + monthly_r) ** months) if monthly_r > -1.0 else 0.0
        except OverflowError:
            fv_pv = pv

    gap = max(0.0, target - fv_pv)

    # If current savings already compound to reach or exceed target:
    if gap <= 0.0:
        return {
            "required_monthly": 0.0,
            "required_monthly_contribution": 0.0,
            "target_gap_to_fund": 0.0,
            "fv_existing_corpus": round(fv_pv, 2),
            "is_horizon_zero": False,
            "zero_return_required_monthly": 0.0,
            "assumed_annual_return": annual_r,
        }

    # Zero-return baseline required monthly
    zero_return_pmt = round(max(0.0, target - pv) / months, 2)

    if abs(monthly_r) < 1e-12:
        req_pmt = gap / months
    else:
        try:
            factor = ((1.0 + monthly_r) ** months) - 1.0
            denom = (factor / monthly_r) * (1.0 + monthly_r) if contribution_timing == "beginning_of_period" else (factor / monthly_r)
            req_pmt = (gap / denom) if denom > 0 else (gap / months)
        except (OverflowError, ZeroDivisionError):
            req_pmt = gap / months

    return {
        "required_monthly": round(max(0.0, req_pmt), 2),
        "required_monthly_contribution": round(max(0.0, req_pmt), 2),
        "target_gap_to_fund": round(gap, 2),
        "fv_existing_corpus": round(fv_pv, 2),
        "is_horizon_zero": False,
        "zero_return_required_monthly": zero_return_pmt,
        "assumed_annual_return": annual_r,
    }
