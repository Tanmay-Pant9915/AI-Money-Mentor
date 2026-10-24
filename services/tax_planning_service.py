"""
services/tax_planning_service.py
Service layer for tax planning, profile context integration, regime comparisons,
scenario simulations, and SQLite persistence in AI Money Mentor.
"""
from datetime import datetime
import json
from typing import Any, Dict, List, Optional, Tuple

from data.database import get_connection, init_db
from data.tax_rules import SUPPORTED_FINANCIAL_YEARS, get_tax_rules
from services.profile_service import get_profile
from services.emergency_fund_service import get_latest_emergency_fund_plan
from utils.tax_calculator import (
    DeductionBreakdown,
    IncomeBreakdown,
    RegimeComparisonResult,
    TaxRegimeResult,
    compare_tax_regimes,
)
from utils.tax_recommendations import TaxRecommendation, generate_tax_recommendations
from utils.tax_scenario_calculator import (
    ProposedTaxMove,
    ScenarioSimulationResult,
    simulate_tax_scenario,
)


def get_user_tax_context(user_id: str = "default_user", db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load financial profile and liquidity context to pre-populate tax inputs.
    Normalizes monthly amounts to annual figures safely.
    """
    profile = get_profile(user_id=user_id, db_path=db_path)
    ef_plan = get_latest_emergency_fund_plan(user_id=user_id, db_path=db_path)

    if not profile:
        return {
            "has_profile": False,
            "age": 30,
            "annual_salary": 0.0,
            "monthly_income": 0.0,
            "monthly_expenses": 0.0,
            "monthly_surplus": 0.0,
            "emergency_runway_months": 0.0,
        }

    monthly_inc = float(profile.get("monthly_income", 0.0) or 0.0)
    essential = float(profile.get("essential_expenses", 0.0) or 0.0)
    discretionary = float(profile.get("discretionary_expenses", 0.0) or 0.0)
    other = float(profile.get("other_expenses", 0.0) or 0.0)
    monthly_debt = float(profile.get("monthly_debt_repayment", 0.0) or 0.0)

    total_monthly_exp = essential + discretionary + other + monthly_debt
    surplus = monthly_inc - total_monthly_exp
    annual_salary = monthly_inc * 12.0

    emergency_months = 0.0
    if ef_plan:
        emergency_months = float(ef_plan.get("coverage_months", 0.0) or 0.0)
    elif essential > 0:
        liquid_savings = float(profile.get("savings_liquid", 0.0) or 0.0)
        emergency_months = liquid_savings / essential

    return {
        "has_profile": True,
        "age": int(profile.get("age", 30) or 30),
        "annual_salary": annual_salary,
        "monthly_income": monthly_inc,
        "monthly_expenses": total_monthly_exp,
        "monthly_surplus": surplus,
        "emergency_runway_months": emergency_months,
    }


def save_tax_profile(
    user_id: str,
    financial_year: str,
    age: int,
    income: IncomeBreakdown,
    deductions: DeductionBreakdown,
    taxes_paid: float = 0.0,
    db_path: Optional[str] = None,
) -> bool:
    """
    Save or update user tax profile in SQLite database.
    """
    init_db(db_path)
    now_str = datetime.now().isoformat()

    deductions_dict = {
        "sec_80c": deductions.sec_80c,
        "sec_80d_self": deductions.sec_80d_self,
        "sec_80d_parents": deductions.sec_80d_parents,
        "is_self_senior": deductions.is_self_senior,
        "is_parents_senior": deductions.is_parents_senior,
        "sec_80ccd_1b": deductions.sec_80ccd_1b,
        "sec_80ccd_2": deductions.sec_80ccd_2,
        "sec_24b": deductions.sec_24b,
        "sec_80e": deductions.sec_80e,
        "sec_80g": deductions.sec_80g,
        "hra_exemption": deductions.hra_exemption,
    }
    deductions_json = json.dumps(deductions_dict)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tax_profiles (
                user_id, financial_year, age, salary_gross, house_property_net,
                other_sources_interest, other_sources_other, business_profession_net,
                deductions_json, taxes_paid, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, financial_year) DO UPDATE SET
                age = excluded.age,
                salary_gross = excluded.salary_gross,
                house_property_net = excluded.house_property_net,
                other_sources_interest = excluded.other_sources_interest,
                other_sources_other = excluded.other_sources_other,
                business_profession_net = excluded.business_profession_net,
                deductions_json = excluded.deductions_json,
                taxes_paid = excluded.taxes_paid,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                financial_year,
                age,
                income.salary_gross,
                income.house_property_net,
                income.other_sources_interest,
                income.other_sources_other,
                income.business_profession_net,
                deductions_json,
                taxes_paid,
                now_str,
                now_str,
            ),
        )
        conn.commit()
    return True


def get_tax_profile(
    user_id: str = "default_user",
    financial_year: str = "2024-25",
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve stored tax profile for a given user and financial year.
    """
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM tax_profiles
            WHERE user_id = ? AND financial_year = ?
            """,
            (user_id, financial_year),
        )
        row = cursor.fetchone()
        if not row:
            return None

        res = dict(row)
        try:
            res["deductions"] = json.loads(res["deductions_json"])
        except Exception:
            res["deductions"] = {}
        return res


def save_tax_assessment(
    user_id: str,
    comparison: RegimeComparisonResult,
    recommendations: List[TaxRecommendation],
    db_path: Optional[str] = None,
) -> int:
    """
    Persist tax assessment snapshot and mark earlier assessments as is_latest = 0.
    """
    init_db(db_path)
    now_str = datetime.now().isoformat()

    recs_serialized = [
        {
            "priority": r.priority,
            "title": r.title,
            "category": r.category,
            "reason": r.reason,
            "suggested_action": r.suggested_action,
            "potential_tax_saving": r.potential_tax_saving,
            "assumptions_note": r.assumptions_note,
        }
        for r in recommendations
    ]

    details = {
        "financial_year": comparison.financial_year,
        "recommended_regime": comparison.recommended_regime,
        "tax_difference": comparison.tax_difference,
        "break_even_deductions": comparison.break_even_deductions,
        "summary_explanation": comparison.summary_explanation,
        "old_regime": {
            "gross_total_income": comparison.old_regime.gross_total_income,
            "standard_deduction": comparison.old_regime.standard_deduction,
            "chapter_via_deductions": comparison.old_regime.chapter_via_deductions,
            "total_deductions_exemptions": comparison.old_regime.total_deductions_exemptions,
            "taxable_income": comparison.old_regime.taxable_income,
            "tax_at_slab_rates": comparison.old_regime.tax_at_slab_rates,
            "sec_87a_rebate": comparison.old_regime.sec_87a_rebate,
            "surcharge": comparison.old_regime.surcharge,
            "health_education_cess": comparison.old_regime.health_education_cess,
            "total_tax_liability": comparison.old_regime.total_tax_liability,
            "tds_and_taxes_paid": comparison.old_regime.tds_and_taxes_paid,
            "net_tax_payable": comparison.old_regime.net_tax_payable,
            "potential_refund": comparison.old_regime.potential_refund,
            "deduction_details": comparison.old_regime.deduction_details,
            "slab_breakdown": comparison.old_regime.slab_breakdown,
        },
        "new_regime": {
            "gross_total_income": comparison.new_regime.gross_total_income,
            "standard_deduction": comparison.new_regime.standard_deduction,
            "chapter_via_deductions": comparison.new_regime.chapter_via_deductions,
            "total_deductions_exemptions": comparison.new_regime.total_deductions_exemptions,
            "taxable_income": comparison.new_regime.taxable_income,
            "tax_at_slab_rates": comparison.new_regime.tax_at_slab_rates,
            "sec_87a_rebate": comparison.new_regime.sec_87a_rebate,
            "marginal_relief_87a": comparison.new_regime.marginal_relief_87a,
            "surcharge": comparison.new_regime.surcharge,
            "health_education_cess": comparison.new_regime.health_education_cess,
            "total_tax_liability": comparison.new_regime.total_tax_liability,
            "tds_and_taxes_paid": comparison.new_regime.tds_and_taxes_paid,
            "net_tax_payable": comparison.new_regime.net_tax_payable,
            "potential_refund": comparison.new_regime.potential_refund,
            "deduction_details": comparison.new_regime.deduction_details,
            "slab_breakdown": comparison.new_regime.slab_breakdown,
        },
        "recommendations": recs_serialized,
    }

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE tax_assessments
            SET is_latest = 0
            WHERE user_id = ? AND financial_year = ?
            """,
            (user_id, comparison.financial_year),
        )

        cursor.execute(
            """
            INSERT INTO tax_assessments (
                user_id, financial_year, recommended_regime, tax_difference,
                old_taxable_income, old_total_tax, new_taxable_income, new_total_tax,
                assessment_details_json, created_at, is_latest
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                user_id,
                comparison.financial_year,
                comparison.recommended_regime,
                comparison.tax_difference,
                comparison.old_regime.taxable_income,
                comparison.old_regime.total_tax_liability,
                comparison.new_regime.taxable_income,
                comparison.new_regime.total_tax_liability,
                json.dumps(details),
                now_str,
            ),
        )
        plan_id = cursor.lastrowid
        conn.commit()

    return plan_id


def get_latest_tax_assessment(
    user_id: str = "default_user",
    financial_year: str = "2024-25",
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve latest stored tax assessment snapshot for a given user.
    """
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM tax_assessments
            WHERE user_id = ? AND financial_year = ? AND is_latest = 1
            ORDER BY id DESC LIMIT 1
            """,
            (user_id, financial_year),
        )
        row = cursor.fetchone()
        if not row:
            return None

        res = dict(row)
        try:
            res["details"] = json.loads(res["assessment_details_json"])
        except Exception:
            res["details"] = {}
        return res


def save_tax_scenario(
    user_id: str,
    scenario_result: ScenarioSimulationResult,
    db_path: Optional[str] = None,
) -> int:
    """
    Save a named what-if tax planning scenario.
    """
    init_db(db_path)
    now_str = datetime.now().isoformat()

    details = {
        "scenario_name": scenario_result.scenario_name,
        "financial_year": scenario_result.financial_year,
        "total_proposed_outflow": scenario_result.total_proposed_outflow,
        "effective_tax_saved": scenario_result.effective_tax_saved,
        "net_cash_outflow": scenario_result.net_cash_outflow,
        "tax_savings_roi_pct": scenario_result.tax_savings_roi_pct,
        "baseline_old_tax": scenario_result.baseline_old_tax,
        "baseline_new_tax": scenario_result.baseline_new_tax,
        "revised_old_tax": scenario_result.revised_old_tax,
        "revised_new_tax": scenario_result.revised_new_tax,
        "revised_recommended": scenario_result.revised_recommended,
        "affordability_warning": scenario_result.affordability_warning,
        "lock_in_warnings": scenario_result.lock_in_warnings,
        "actionable_summary": scenario_result.actionable_summary,
        "proposed_moves": [
            {
                "category": m.category,
                "description": m.description,
                "proposed_amount": m.proposed_amount,
                "lock_in_note": m.lock_in_note,
            }
            for m in scenario_result.proposed_moves
        ],
    }

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tax_scenarios (
                user_id, scenario_name, financial_year, total_outflow,
                tax_saved, scenario_details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                scenario_result.scenario_name,
                scenario_result.financial_year,
                scenario_result.total_proposed_outflow,
                scenario_result.effective_tax_saved,
                json.dumps(details),
                now_str,
            ),
        )
        scen_id = cursor.lastrowid
        conn.commit()

    return scen_id


def get_saved_tax_scenarios(
    user_id: str = "default_user",
    financial_year: str = "2024-25",
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve all saved what-if tax scenarios for a user.
    """
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM tax_scenarios
            WHERE user_id = ? AND financial_year = ?
            ORDER BY id DESC
            """,
            (user_id, financial_year),
        )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            try:
                d["details"] = json.loads(d["scenario_details_json"])
            except Exception:
                d["details"] = {}
            results.append(d)
        return results


def delete_tax_scenario(
    scenario_id: int,
    user_id: str = "default_user",
    db_path: Optional[str] = None,
) -> bool:
    """
    Delete a specific saved tax scenario.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM tax_scenarios WHERE id = ? AND user_id = ?",
            (scenario_id, user_id),
        )
        conn.commit()
    return True
