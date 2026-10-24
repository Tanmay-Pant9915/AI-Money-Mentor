"""
utils/fire_calculator.py
Deterministic mathematical calculations for Financial Independence, Retire Early (FIRE).
Implements the withdrawal-rate method, extended early-retirement growing-annuity modeling,
iterative month-by-month timeline and FIRE age solver, and savings-rate scenario analysis.
"""
import math
from typing import Any, Dict, List, Optional, Tuple

from utils.retirement_calculator import (
    calculate_monthly_effective_rate,
    calculate_retirement_accumulation,
    calculate_retirement_corpus,
)


def calculate_fire_corpus(
    annual_expenses_today: float,
    safe_withdrawal_rate: float = 3.5,
    years_to_fire: float = 0.0,
    annual_inflation_rate: float = 6.0,
) -> Dict[str, Any]:
    """
    Calculate the target FIRE corpus required to sustain financial independence.
    Provides both:
      1. Real FIRE corpus in today's purchasing power: Annual Expenses Today / SWR
      2. Nominal FIRE corpus at FIRE milestone date: (Annual Expenses Today * (1+i)^t) / SWR

    Args:
        annual_expenses_today: Anticipated annual living expenses post-FIRE in today's INR.
        safe_withdrawal_rate: Assumed safe annual withdrawal rate (SWR, e.g. 3.5% or 4.0%).
        years_to_fire: Projected timeline in years until FIRE is reached (t).
        annual_inflation_rate: Annual inflation rate in % (i).

    Returns:
        Structured dictionary with real and nominal corpus targets, expenses, and multipliers.
    """
    ann_exp = max(0.0, float(annual_expenses_today or 0.0))
    swr = max(0.1, float(safe_withdrawal_rate or 3.5))
    swr_dec = swr / 100.0
    inf_rate = max(0.0, float(annual_inflation_rate or 0.0))
    t = max(0.0, float(years_to_fire or 0.0))

    # Real target in today's rupees: E / swr
    real_corpus = round(ann_exp / swr_dec, 2) if swr_dec > 0 else 0.0
    corpus_multiple = round(1.0 / swr_dec, 1) if swr_dec > 0 else 0.0

    # Inflation multiplier to FIRE date: (1 + i)^t
    i_dec = inf_rate / 100.0
    inf_multiplier = (1.0 + i_dec) ** t if (t > 0 and inf_rate > 0) else 1.0
    nominal_expenses_at_fire = ann_exp * inf_multiplier
    nominal_corpus_at_fire = round(nominal_expenses_at_fire / swr_dec, 2) if swr_dec > 0 else 0.0

    return {
        "annual_expenses_today": round(ann_exp, 2),
        "monthly_expenses_today": round(ann_exp / 12.0, 2),
        "nominal_annual_expenses_at_fire": round(nominal_expenses_at_fire, 2),
        "nominal_monthly_expenses_at_fire": round(nominal_expenses_at_fire / 12.0, 2),
        "safe_withdrawal_rate": swr,
        "corpus_multiple": corpus_multiple,
        "real_fire_corpus_today": real_corpus,
        "nominal_fire_corpus_at_fire": nominal_corpus_at_fire,
        "inflation_multiplier": round(inf_multiplier, 4),
        "years_to_fire": t,
        "annual_inflation_rate": inf_rate,
        "assumptions": [
            f"Assumes an initial withdrawal rate of {swr:.1f}% ({corpus_multiple:.0f}x annual expenses).",
            f"Inflation rate assumed at {inf_rate:.1f}% per annum.",
            "Withdrawals in retirement must be periodically rebalanced to preserve capital across market cycles.",
        ],
    }


def calculate_fire_timeline(
    current_age: int,
    current_invested_assets: float,
    monthly_investment_contribution: float,
    annual_expenses_today: float,
    assumed_annual_return: float = 10.0,
    annual_inflation_rate: float = 6.0,
    safe_withdrawal_rate: float = 3.5,
    max_search_age: int = 100,
) -> Dict[str, Any]:
    """
    Deterministically solve for the exact month and age when accumulated investments
    meet or exceed the inflation-adjusted FIRE corpus.

    At month m (year y = m / 12):
        Accumulated Corpus = PV*(1+r)^m + PMT*(((1+r)^m - 1)/r)
        Target Nominal Corpus = (Annual Expenses Today * (1+i)^y) / SWR
    Condition:
        Accumulated Corpus >= Target Nominal Corpus

    Returns:
        Structured dictionary with years to FIRE, FIRE age, target corpus, feasibility flag,
        and chronological trajectory data.
    """
    age = max(18, int(current_age or 30))
    pv = max(0.0, float(current_invested_assets or 0.0))
    pmt = max(0.0, float(monthly_investment_contribution or 0.0))
    ann_exp = max(0.0, float(annual_expenses_today or 0.0))
    annual_r = float(assumed_annual_return or 10.0)
    inf_rate = max(0.0, float(annual_inflation_rate or 6.0))
    swr = max(0.1, float(safe_withdrawal_rate or 3.5))
    swr_dec = swr / 100.0

    # Real baseline target today
    target_today = ann_exp / swr_dec if swr_dec > 0 else 0.0

    # Zero expenses edge case
    if target_today <= 0.0:
        return {
            "is_feasible": True,
            "is_already_fire": True,
            "years_to_fire": 0.0,
            "months_to_fire": 0,
            "fire_age": age,
            "nominal_fire_corpus": 0.0,
            "real_fire_corpus": 0.0,
            "accumulated_corpus_at_fire": round(pv, 2),
            "surplus_at_fire": round(pv, 2),
            "trajectory": [{"month": 0, "year": 0.0, "age": float(age), "accumulated": round(pv, 2), "target": 0.0}],
            "message": "With zero expenses, financial independence is achieved immediately.",
            "target_fire_age_analysis": None,
        }

    # Immediate Freedom Edge Case: already at or above target
    if pv >= target_today and target_today > 0:
        return {
            "is_feasible": True,
            "is_already_fire": True,
            "years_to_fire": 0.0,
            "months_to_fire": 0,
            "fire_age": age,
            "nominal_fire_corpus": round(target_today, 2),
            "real_fire_corpus": round(target_today, 2),
            "accumulated_corpus_at_fire": round(pv, 2),
            "surplus_at_fire": round(pv - target_today, 2),
            "trajectory": [{"month": 0, "year": 0.0, "age": float(age), "accumulated": round(pv, 2), "target": round(target_today, 2)}],
            "message": "Congratulations! Your current invested portfolio already meets your FIRE corpus target today.",
            "target_fire_age_analysis": None,
        }

    monthly_r = calculate_monthly_effective_rate(annual_r)
    annual_i_dec = inf_rate / 100.0

    max_years = max(1, max_search_age - age)
    max_months = max_years * 12

    found_month = None
    trajectory: List[Dict[str, Any]] = []

    # Run deterministic simulation month-by-month
    # Record annual trajectory points for charting
    for m in range(max_months + 1):
        y = m / 12.0
        # 1. Target corpus grows with inflation
        nom_exp_m = ann_exp * ((1.0 + annual_i_dec) ** y)
        target_m = nom_exp_m / swr_dec if swr_dec > 0 else 0.0

        # 2. Accumulated investment portfolio
        if m == 0:
            accum_m = pv
        elif abs(monthly_r) < 1e-12:
            accum_m = pv + (pmt * m)
        else:
            try:
                m_pv = pv * ((1.0 + monthly_r) ** m) if monthly_r > -1.0 else 0.0
                m_factor = ((1.0 + monthly_r) ** m) - 1.0
                m_pmt = pmt * (m_factor / monthly_r)
                accum_m = max(0.0, m_pv + m_pmt)
            except OverflowError:
                accum_m = pv + (pmt * m)

        # Record trajectory at yearly intervals or at month 0
        if m % 12 == 0 or m == max_months:
            trajectory.append({
                "month": m,
                "year": round(y, 1),
                "age": round(age + y, 1),
                "accumulated": round(accum_m, 2),
                "target": round(target_m, 2),
            })

        # Check crossing condition
        if accum_m >= target_m and target_m > 0 and found_month is None:
            found_month = m

        # Continue 5 years past crossover so charts display crossing runway cleanly
        if found_month is not None and (y >= (found_month / 12.0) + 5.0 or m == max_months):
            break

    if found_month is not None:
        years_to_fire = round(found_month / 12.0, 1)
        fire_age = round(age + years_to_fire, 1)
        final_y = found_month / 12.0
        final_nom_exp = ann_exp * ((1.0 + annual_i_dec) ** final_y)
        final_target = round(final_nom_exp / swr_dec, 2)

        # Recalculate exact accumulation at found_month
        if abs(monthly_r) < 1e-12:
            exact_accum = pv + (pmt * found_month)
        else:
            try:
                m_pv = pv * ((1.0 + monthly_r) ** found_month) if monthly_r > -1.0 else 0.0
                m_factor = ((1.0 + monthly_r) ** found_month) - 1.0
                m_pmt = pmt * (m_factor / monthly_r)
                exact_accum = m_pv + m_pmt
            except OverflowError:
                exact_accum = pv + (pmt * found_month)

        # Ensure exact crossing point is in trajectory
        if not any(pt["month"] == found_month for pt in trajectory):
            trajectory.append({
                "month": found_month,
                "year": round(final_y, 1),
                "age": fire_age,
                "accumulated": round(exact_accum, 2),
                "target": final_target,
            })
            trajectory.sort(key=lambda pt: pt["month"])

        return {
            "is_feasible": True,
            "is_already_fire": False,
            "years_to_fire": years_to_fire,
            "months_to_fire": found_month,
            "fire_age": fire_age,
            "nominal_fire_corpus": final_target,
            "real_fire_corpus": round(target_today, 2),
            "accumulated_corpus_at_fire": round(exact_accum, 2),
            "surplus_at_fire": round(max(0.0, exact_accum - final_target), 2),
            "trajectory": trajectory,
            "message": f"At your current contribution of ₹{pmt:,.0f}/mo, FIRE is projected at age {fire_age:.0f} ({years_to_fire:.1f} years).",
        }
    else:
        # Infeasible within timeframe
        # Calculate terminal corpus at retirement age 60 or max search age
        term_y = min(30, max_years)
        term_m = term_y * 12
        term_target = (ann_exp * ((1.0 + annual_i_dec) ** term_y)) / swr_dec
        if abs(monthly_r) < 1e-12:
            term_accum = pv + (pmt * term_m)
        else:
            try:
                m_pv = pv * ((1.0 + monthly_r) ** term_m) if monthly_r > -1.0 else 0.0
                m_pmt = pmt * ((((1.0 + monthly_r) ** term_m) - 1.0) / monthly_r)
                term_accum = m_pv + m_pmt
            except OverflowError:
                term_accum = pv + (pmt * term_m)

        shortfall = max(0.0, term_target - term_accum)

        return {
            "is_feasible": False,
            "is_already_fire": False,
            "years_to_fire": None,
            "months_to_fire": None,
            "fire_age": None,
            "nominal_fire_corpus": round(term_target, 2),
            "real_fire_corpus": round(target_today, 2),
            "accumulated_corpus_at_fire": round(term_accum, 2),
            "surplus_at_fire": 0.0,
            "projected_shortfall": round(shortfall, 2),
            "trajectory": trajectory,
            "message": (
                f"FIRE is mathematically not reachable within {max_years} years under current savings rate. "
                "Increasing your monthly investment, extending timeline, or trimming post-FIRE expenses is required."
            ),
        }


def calculate_target_fire_age_analysis(
    current_age: int,
    current_invested_assets: float,
    monthly_investment_contribution: float,
    annual_expenses_today: float,
    target_fire_age: int,
    assumed_annual_return: float = 10.0,
    annual_inflation_rate: float = 6.0,
    safe_withdrawal_rate: float = 3.5,
) -> Dict[str, Any]:
    """
    Analyze retirement readiness for a specifically chosen target FIRE age.
    Calculates the nominal corpus needed at that age, projected portfolio accumulation,
    funding surplus/shortfall, and required monthly SIP.
    """
    cur_age = max(18, int(current_age or 30))
    tgt_age = max(cur_age, int(target_fire_age or 50))
    pv = max(0.0, float(current_invested_assets or 0.0))
    pmt = max(0.0, float(monthly_investment_contribution or 0.0))
    ann_exp = max(0.0, float(annual_expenses_today or 0.0))
    r_ann = float(assumed_annual_return or 10.0)
    inf_rate = max(0.0, float(annual_inflation_rate or 6.0))
    swr = max(0.1, float(safe_withdrawal_rate or 3.5))
    swr_dec = swr / 100.0

    target_years = max(0.0, float(tgt_age - cur_age))
    inf_dec = inf_rate / 100.0
    nom_exp_at_target = ann_exp * ((1.0 + inf_dec) ** target_years)
    nom_target_corpus = round(nom_exp_at_target / swr_dec, 2) if swr_dec > 0 else 0.0
    real_target_corpus = round(ann_exp / swr_dec, 2) if swr_dec > 0 else 0.0

    accum = calculate_retirement_accumulation(
        current_corpus=pv,
        monthly_contribution=pmt,
        years_until_retirement=target_years,
        assumed_annual_return=r_ann,
    )
    projected_corpus = accum["future_value"]
    gap = round(projected_corpus - nom_target_corpus, 2)
    is_funded = gap >= 0.0

    from utils.retirement_calculator import calculate_required_monthly_contribution
    req_contrib_calc = calculate_required_monthly_contribution(
        target_corpus=nom_target_corpus,
        current_corpus=pv,
        years_until_retirement=target_years,
        assumed_annual_return=r_ann,
    )
    req_monthly = req_contrib_calc["required_monthly_contribution"]

    return {
        "target_fire_age": tgt_age,
        "years_to_target_fire": target_years,
        "nominal_fire_target": nom_target_corpus,
        "real_fire_target": real_target_corpus,
        "projected_corpus_at_target_age": projected_corpus,
        "shortfall_or_surplus": gap,
        "is_funded": is_funded,
        "required_monthly_contribution": req_monthly,
        "current_monthly_contribution": pmt,
        "monthly_contribution_gap": max(0.0, round(req_monthly - pmt, 2)),
    }


def calculate_savings_rate_table(
    monthly_income: float,
    current_age: int,
    current_invested_assets: float,
    assumed_annual_return: float = 10.0,
    annual_inflation_rate: float = 6.0,
    safe_withdrawal_rate: float = 3.5,
) -> List[Dict[str, Any]]:
    """
    Generate the classic FIRE savings-rate table comparing savings rates
    from 10% to 75% and their direct impact on time to financial independence.
    Expenses = Income * (1 - Savings Rate).
    """
    inc = max(1000.0, float(monthly_income or 50000.0))
    table: List[Dict[str, Any]] = []

    rates = [10, 20, 30, 40, 50, 60, 70]
    for sr in rates:
        sr_pct = sr / 100.0
        monthly_save = inc * sr_pct
        monthly_exp = inc * (1.0 - sr_pct)
        annual_exp = monthly_exp * 12.0

        timeline = calculate_fire_timeline(
            current_age=current_age,
            current_invested_assets=current_invested_assets,
            monthly_investment_contribution=monthly_save,
            annual_expenses_today=annual_exp,
            assumed_annual_return=assumed_annual_return,
            annual_inflation_rate=annual_inflation_rate,
            safe_withdrawal_rate=safe_withdrawal_rate,
        )

        table.append({
            "savings_rate_pct": sr,
            "monthly_investment": round(monthly_save, 2),
            "monthly_expenses": round(monthly_exp, 2),
            "annual_expenses": round(annual_exp, 2),
            "is_feasible": timeline["is_feasible"],
            "years_to_fire": timeline.get("years_to_fire"),
            "fire_age": timeline.get("fire_age"),
            "fire_corpus_today": timeline["real_fire_corpus"],
        })

    return table
