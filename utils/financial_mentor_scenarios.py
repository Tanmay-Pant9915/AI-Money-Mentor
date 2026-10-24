"""
utils/financial_mentor_scenarios.py
Deterministic simulation of user what-if scenarios asked during conversational chat.
Invokes existing financial calculation utilities with temporary parameters without altering persistent profile data.
"""
import re
from typing import Any, Dict, Optional

from services.profile_service import format_inr, get_profile
from services.retirement_planning_service import evaluate_retirement_and_fire_plan
from utils.emergency_fund_calculator import (
    calculate_emergency_fund_gap,
    calculate_emergency_fund_target,
    calculate_months_to_target,
)


def detect_and_simulate_scenario(
    query: str,
    user_id: str = "default_user",
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Check if the user query requests a supported what-if calculation and execute it deterministically.
    Returns structured simulation result or None if query is not a structured what-if request.
    """
    q_lower = query.lower()
    prof = get_profile(user_id=user_id, db_path=db_path)
    if not prof:
        metrics = {}
        monthly_inc = 100000.0
        essential_exp = 40000.0
        current_surplus = 40000.0
        liquid_sav = 100000.0
        current_age = 30
    else:
        metrics = prof.get("metrics", {})
        monthly_inc = float(metrics.get("monthly_income", 0.0))
        essential_exp = float(metrics.get("essential_expenses", 0.0))
        current_surplus = float(metrics.get("monthly_surplus", 0.0))
        liquid_sav = float(metrics.get("savings_liquid", 0.0))
        current_age = int(prof.get("age", 30))

    # Scenario 1: Additional monthly savings / investment
    # Pattern: "save ₹5,000 more", "save 5000 more each month", "invest 10000 more"
    match_savings = re.search(r"(?:save|invest)\s*(?:₹|rs\.?|inr)?\s*([\d,]+)\s*(?:more|extra)", q_lower)
    if match_savings:
        amt_str = match_savings.group(1).replace(",", "")
        try:
            extra_amt = float(amt_str)
            if extra_amt > 0:
                tgt_6m = calculate_emergency_fund_target(essential_exp, 6.0)
                gap_6m = calculate_emergency_fund_gap(tgt_6m, liquid_sav)

                base_pace = max(1000.0, current_surplus * 0.5) if current_surplus > 0 else 0.0
                sim_pace = base_pace + extra_amt

                timing_before = calculate_months_to_target(gap_6m, base_pace)
                timing_after = calculate_months_to_target(gap_6m, sim_pace)

                # 5-year wealth projection at 10% CAGR
                r_m = 0.10 / 12.0
                n = 60
                fv_5yr = extra_amt * (((1 + r_m) ** n - 1) / r_m) * (1 + r_m)

                return {
                    "scenario_type": "EXTRA_MONTHLY_SAVINGS",
                    "extra_monthly_amount": format_inr(extra_amt),
                    "current_surplus": format_inr(current_surplus),
                    "new_potential_surplus": format_inr(current_surplus + extra_amt),
                    "annual_cash_addition": format_inr(extra_amt * 12.0),
                    "five_year_wealth_projection_at_10pct": format_inr(fv_5yr),
                    "emergency_fund_months_to_target_before": f"{timing_before.get('months')} months" if timing_before.get("months") else "N/A",
                    "emergency_fund_months_to_target_after": f"{timing_after.get('months')} months" if timing_after.get("months") else "N/A",
                    "note": "Simulation is temporary and does not alter your persistent profile.",
                }
        except ValueError:
            pass

    # Scenario 2: Change retirement age
    # Pattern: "retire at 55", "retire at age 50", "retire 5 years earlier"
    match_retire = re.search(r"retire\s+(?:at\s+(?:age\s+)?)?(\d{2})", q_lower)
    if match_retire:
        try:
            target_age = int(match_retire.group(1))
            if 35 <= target_age <= 75 and target_age > current_age:
                ret_inputs = {
                    "current_age": current_age,
                    "target_retirement_age": target_age,
                    "planning_age": 85,
                    "monthly_expenses_today": essential_exp + float(metrics.get("discretionary_expenses", 0.0)),
                    "annual_inflation_rate": 6.0,
                    "pre_retirement_return": 10.0,
                    "post_retirement_return": 7.0,
                    "safe_withdrawal_rate": 4.0,
                    "current_corpus": float(metrics.get("existing_investments", 0.0)),
                    "monthly_contribution": max(0.0, current_surplus * 0.5),
                    "available_monthly_surplus": current_surplus,
                }
                sim_ret = evaluate_retirement_and_fire_plan(ret_inputs)
                return {
                    "scenario_type": "RETIREMENT_AGE_ADJUSTMENT",
                    "simulated_retirement_age": target_age,
                    "current_age": current_age,
                    "target_corpus_required": format_inr(sim_ret.get("target_corpus", 0.0)),
                    "projected_corpus_accumulated": format_inr(sim_ret.get("projected_corpus", 0.0)),
                    "monthly_sip_required": format_inr(sim_ret.get("required_monthly_contribution", 0.0)),
                    "shortfall_or_surplus": format_inr(sim_ret.get("corpus_gap", 0.0)),
                    "note": f"Retiring at age {target_age} gives {target_age - current_age} years of accumulation.",
                }
        except ValueError:
            pass

    # Scenario 3: Change emergency fund target months
    # Pattern: "emergency fund target is 9 months", "emergency fund for 12 months"
    match_ef = re.search(r"emergency\s+(?:fund|runway)\s+(?:target\s+)?(?:of\s+|is\s+|for\s+)?(\d{1,2})\s*months?", q_lower)
    if match_ef:
        try:
            target_months = int(match_ef.group(1))
            if 1 <= target_months <= 36:
                tgt_amt = calculate_emergency_fund_target(essential_exp, float(target_months))
                gap_amt = calculate_emergency_fund_gap(tgt_amt, liquid_sav)
                contrib = max(1000.0, current_surplus * 0.5) if current_surplus > 0 else 0.0
                timing = calculate_months_to_target(gap_amt, contrib)

                return {
                    "scenario_type": "EMERGENCY_TARGET_MONTHS",
                    "simulated_target_months": f"{target_months} months",
                    "monthly_essential_expenses": format_inr(essential_exp),
                    "simulated_target_amount": format_inr(tgt_amt),
                    "current_savings": format_inr(liquid_sav),
                    "remaining_gap": format_inr(gap_amt),
                    "estimated_months_to_reach": f"{timing.get('months')} months" if timing.get("months") else "Met",
                    "note": f"Coverage target adjusted to {target_months} months of essential expenses.",
                }
        except ValueError:
            pass

    return None
