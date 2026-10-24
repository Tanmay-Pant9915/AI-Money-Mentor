"""
services/financial_mentor_context.py
Context extraction layer for AI Financial Mentor.
Safely extracts structured, normalized financial data from existing modules (Tasks 1-7).
Distinguishes verified data from missing fields without fabricating numbers.
"""
from typing import Any, Dict, List, Optional

from services.profile_service import format_inr, get_profile
from services.risk_profile_service import get_latest_risk_assessment
from services.money_health_service import get_latest_health_score
from services.financial_planning_service import get_latest_saved_plan as get_latest_budget_plan
from services.retirement_planning_service import get_latest_saved_plan as get_latest_retirement_plan
from services.emergency_fund_service import get_latest_emergency_fund_plan
from services.insurance_planning_service import get_latest_insurance_assessment
from services.tax_planning_service import get_latest_tax_assessment, get_tax_profile


def extract_profile_context(user_id: str = "default_user", db_path: Optional[str] = None) -> Dict[str, Any]:
    """Extract financial profile and core cash flow metrics."""
    prof = get_profile(user_id=user_id, db_path=db_path)
    if not prof:
        return {"status": "unavailable", "message": "Financial Profile has not been created yet."}

    metrics = prof.get("metrics", {})
    return {
        "status": "available",
        "name": prof.get("name", "User"),
        "age": prof.get("age"),
        "employment_status": prof.get("employment_status"),
        "monthly_income": format_inr(metrics.get("monthly_income", 0.0)),
        "essential_expenses": format_inr(metrics.get("essential_expenses", 0.0)),
        "discretionary_expenses": format_inr(metrics.get("discretionary_expenses", 0.0)),
        "other_expenses": format_inr(metrics.get("other_expenses", 0.0)),
        "monthly_debt_repayment": format_inr(metrics.get("monthly_debt_repayment", 0.0)),
        "total_monthly_expenses": format_inr(metrics.get("total_monthly_expenses", 0.0)),
        "monthly_surplus": format_inr(metrics.get("monthly_surplus", 0.0)),
        "is_deficit": metrics.get("is_deficit", False),
        "liquid_savings": format_inr(metrics.get("savings_liquid", 0.0)),
        "outstanding_debt": format_inr(metrics.get("outstanding_debt", 0.0)),
        "existing_investments": format_inr(metrics.get("existing_investments", 0.0)),
        "net_worth": format_inr(metrics.get("net_worth", 0.0)),
        "dependents": prof.get("dependents", 0),
        "goals_count": metrics.get("num_goals", 0),
        "emergency_months": f"{metrics.get('emergency_months', 0.0):.1f} months",
    }


def extract_risk_context(user_id: str = "default_user", db_path: Optional[str] = None) -> Dict[str, Any]:
    """Extract latest risk profiling score and classification."""
    risk = get_latest_risk_assessment(user_id=user_id, db_path=db_path)
    if not risk:
        return {"status": "unavailable", "message": "Risk assessment not completed yet."}

    return {
        "status": "available",
        "risk_category": risk.get("classification", "Unknown"),
        "risk_score": f"{risk.get('score', 0):.1f}/100",
        "tolerance_score": f"{risk.get('tolerance_score', 0):.1f}",
        "capacity_score": f"{risk.get('capacity_score', 0):.1f}",
    }


def extract_health_score_context(user_id: str = "default_user", db_path: Optional[str] = None) -> Dict[str, Any]:
    """Extract latest Money Health Score and component metrics."""
    score_data = get_latest_health_score(user_id=user_id, db_path=db_path)
    if not score_data or score_data.get("overall_score") is None:
        return {"status": "unavailable", "message": "Money Health Score has not been calculated yet."}

    breakdown = score_data.get("components") or score_data.get("breakdown") or {}
    return {
        "status": "available",
        "overall_score": f"{score_data.get('overall_score')}/100",
        "rating": score_data.get("rating", "N/A"),
        "sub_scores": {
            "savings_ratio": f"{breakdown.get('savings_ratio', {}).get('score', 0)}/25",
            "debt_burden": f"{breakdown.get('debt_burden', {}).get('score', 0)}/20",
            "emergency_runway": f"{breakdown.get('emergency_runway', {}).get('score', 0)}/20",
            "investment_allocation": f"{breakdown.get('investment_allocation', {}).get('score', 0)}/20",
            "goal_progress": f"{breakdown.get('goal_progress', {}).get('score', 0)}/15",
        },
        "key_insights": score_data.get("insights", [])[:3],
        "top_recommendations": score_data.get("recommendations", [])[:3],
    }


def extract_budget_context(user_id: str = "default_user", db_path: Optional[str] = None) -> Dict[str, Any]:
    """Extract 50/30/20 budget allocations and financial plan details."""
    plan = get_latest_budget_plan(user_id=user_id, db_path=db_path)
    if plan:
        summary = plan.get("summary", {})
        rec_budget = plan.get("budget", {}).get("recommended_50_30_20", {})
        return {
            "status": "available",
            "plan_name": plan.get("plan_name", "Monthly Financial Plan"),
            "monthly_income": format_inr(summary.get("monthly_income", 0.0)),
            "current_essential": format_inr(summary.get("essential_expenses", 0.0)),
            "current_discretionary": format_inr(summary.get("discretionary_expenses", 0.0)),
            "current_savings_surplus": format_inr(summary.get("monthly_surplus", 0.0)),
            "recommended_50_30_20": {
                "needs_target": format_inr(rec_budget.get("essential_expenses", {}).get("target_amount", 0.0)),
                "wants_target": format_inr(rec_budget.get("discretionary_expenses", {}).get("target_amount", 0.0)),
                "savings_target": format_inr(rec_budget.get("savings_investments", {}).get("target_amount", 0.0)),
            },
            "priorities": [a.get("action") for a in plan.get("actions", [])[:3] if isinstance(a, dict)],
        }

    # Fallback to base profile cash flow if no full plan saved yet
    prof = get_profile(user_id=user_id, db_path=db_path)
    if not prof:
        return {"status": "unavailable", "message": "No financial profile or budget plan found."}

    metrics = prof.get("metrics", {})
    inc = float(metrics.get("monthly_income", 0.0))
    return {
        "status": "available",
        "plan_name": "Standard 50/30/20 Framework",
        "monthly_income": format_inr(inc),
        "current_essential": format_inr(metrics.get("essential_expenses", 0.0)),
        "current_discretionary": format_inr(metrics.get("discretionary_expenses", 0.0)),
        "current_savings_surplus": format_inr(metrics.get("monthly_surplus", 0.0)),
        "recommended_50_30_20": {
            "needs_target": format_inr(inc * 0.50),
            "wants_target": format_inr(inc * 0.30),
            "savings_target": format_inr(inc * 0.20),
        },
        "priorities": ["Maintain living expenses within 50% of income", "Save at least 20% toward financial goals"],
    }


def extract_goals_context(user_id: str = "default_user", db_path: Optional[str] = None) -> Dict[str, Any]:
    """Extract active financial goals and funding status."""
    prof = get_profile(user_id=user_id, db_path=db_path)
    if not prof or not prof.get("goals"):
        return {"status": "unavailable", "message": "No financial goals configured."}

    goals_list = []
    for g in prof.get("goals", []):
        goals_list.append({
            "name": g.get("name"),
            "category": g.get("category", "General"),
            "target_amount": format_inr(g.get("target_amount", 0.0)),
            "target_date": g.get("target_date"),
            "current_amount": format_inr(g.get("current_amount", 0.0)),
            "monthly_contribution": format_inr(g.get("monthly_contribution", 0.0)),
            "priority": g.get("priority", "Medium"),
        })

    return {
        "status": "available",
        "goal_count": len(goals_list),
        "goals": goals_list,
    }


def extract_retirement_context(user_id: str = "default_user", db_path: Optional[str] = None) -> Dict[str, Any]:
    """Extract retirement and FIRE projection parameters."""
    ret_plan = get_latest_retirement_plan(user_id=user_id, db_path=db_path)
    if not ret_plan:
        return {"status": "unavailable", "message": "Retirement / FIRE plan has not been generated yet."}

    fire_age = ret_plan.get("estimated_fire_age")
    years_to_fire = ret_plan.get("years_to_fire")

    return {
        "status": "available",
        "current_age": ret_plan.get("current_age"),
        "target_retirement_age": ret_plan.get("target_retirement_age"),
        "current_corpus": format_inr(ret_plan.get("current_corpus", 0.0)),
        "monthly_contribution": format_inr(ret_plan.get("monthly_contribution", 0.0)),
        "target_retirement_corpus": format_inr(ret_plan.get("target_corpus", 0.0)),
        "projected_corpus_at_retirement": format_inr(ret_plan.get("projected_corpus", 0.0)),
        "required_monthly_investment": format_inr(ret_plan.get("required_monthly", 0.0)),
        "estimated_fire_age": f"{fire_age:.1f} years" if fire_age is not None else "Not achieved under current savings",
        "years_to_fire": f"{years_to_fire:.1f} years" if years_to_fire is not None else "N/A",
    }


def extract_emergency_fund_context(user_id: str = "default_user", db_path: Optional[str] = None) -> Dict[str, Any]:
    """Extract emergency fund targets and runway status."""
    ef = get_latest_emergency_fund_plan(user_id=user_id, db_path=db_path)
    if not ef:
        return {"status": "unavailable", "message": "Emergency fund plan not created yet."}

    return {
        "status": "available",
        "target_coverage_months": f"{ef.get('target_months', 6.0):.1f} months",
        "target_amount": format_inr(ef.get("target_amount", 0.0)),
        "current_savings": format_inr(ef.get("current_savings", 0.0)),
        "fund_gap": format_inr(ef.get("fund_gap", 0.0)),
        "actual_coverage_months": f"{ef.get('coverage_months', 0.0):.1f} months",
        "monthly_contribution": format_inr(ef.get("monthly_contribution", 0.0)),
        "estimated_months_to_target": f"{ef.get('estimated_months')} months" if ef.get("estimated_months") else "Target reached or contribution zero",
        "runway_status": ef.get("status", "Unknown"),
    }


def extract_insurance_context(user_id: str = "default_user", db_path: Optional[str] = None) -> Dict[str, Any]:
    """Extract health, life, and personal accident insurance assessment results."""
    ins = get_latest_insurance_assessment(user_id=user_id, db_path=db_path)
    if not ins:
        return {"status": "unavailable", "message": "Insurance needs assessment has not been completed."}

    return {
        "status": "available",
        "health_insurance": {
            "personal_cover": format_inr(ins.get("health_personal_cover", 0.0)),
            "employer_cover": format_inr(ins.get("health_employer_cover", 0.0)),
            "target_cover": format_inr(ins.get("health_target_cover", 0.0)),
            "gap": format_inr(ins.get("health_gap", 0.0)),
        },
        "life_insurance": {
            "existing_cover": format_inr(ins.get("life_existing_cover", 0.0)),
            "estimated_need": format_inr(ins.get("life_estimated_need", 0.0)),
            "coverage_gap": format_inr(ins.get("life_gap", 0.0)),
            "income_multiplier_years": f"{ins.get('life_income_multiplier_years', 10):.0f} years",
        },
        "accident_disability": {
            "has_cover": bool(ins.get("has_accident_disability_cover", 0)),
            "cover_amount": format_inr(ins.get("accident_cover_amount", 0.0)),
        },
    }


def extract_tax_context(user_id: str = "default_user", financial_year: str = "2024-25", db_path: Optional[str] = None) -> Dict[str, Any]:
    """Extract latest income tax comparison and profile estimates."""
    assess = get_latest_tax_assessment(user_id=user_id, financial_year=financial_year, db_path=db_path)
    prof = get_tax_profile(user_id=user_id, financial_year=financial_year, db_path=db_path)

    if not assess and not prof:
        return {"status": "unavailable", "message": f"Tax planning assessment for FY {financial_year} not created yet."}

    res: Dict[str, Any] = {"status": "available", "financial_year": financial_year}

    if assess:
        res["recommended_regime"] = assess.get("recommended_regime")
        res["tax_savings_difference"] = format_inr(assess.get("tax_difference", 0.0))
        res["old_regime_total_tax"] = format_inr(assess.get("old_total_tax", 0.0))
        res["old_regime_taxable_income"] = format_inr(assess.get("old_taxable_income", 0.0))
        res["new_regime_total_tax"] = format_inr(assess.get("new_total_tax", 0.0))
        res["new_regime_taxable_income"] = format_inr(assess.get("new_taxable_income", 0.0))
        det = assess.get("details", {})
        res["break_even_deductions"] = format_inr(det.get("break_even_deductions", 0.0))

    if prof:
        deds = prof.get("deductions", {})
        res["claimed_deductions"] = {
            "80C": format_inr(deds.get("sec_80c", 0.0)),
            "80D_self": format_inr(deds.get("sec_80d_self", 0.0)),
            "80CCD_1B_nps": format_inr(deds.get("sec_80ccd_1b", 0.0)),
            "80CCD_2_employer_nps": format_inr(deds.get("sec_80ccd_2", 0.0)),
            "24b_home_loan": format_inr(deds.get("sec_24b", 0.0)),
            "hra_exemption": format_inr(deds.get("hra_exemption", 0.0)),
        }
        res["taxes_already_paid"] = format_inr(prof.get("taxes_paid", 0.0))

    return res


def extract_portfolio_context(portfolio_data: Optional[Any] = None) -> Dict[str, Any]:
    """Extract CAMS CAS mutual fund portfolio metrics if available."""
    if portfolio_data is None:
        return {"status": "unavailable", "message": "No CAMS CAS mutual fund portfolio uploaded."}

    # Handle DataFrame or list of dicts
    funds = []
    if hasattr(portfolio_data, "iterrows"):
        for _, row in portfolio_data.iterrows():
            funds.append({
                "scheme": str(row.get("scheme", "Unknown")),
                "current_value": float(row.get("current_value", 0.0) or 0.0),
                "expense_ratio": float(row.get("expense_ratio", 0.0) or 0.0) if row.get("expense_ratio") is not None else None,
                "xirr": float(row.get("xirr", 0.0) or 0.0) if row.get("xirr") is not None else None,
            })
    elif isinstance(portfolio_data, list):
        for f in portfolio_data:
            funds.append({
                "scheme": str(f.get("scheme", "Unknown")),
                "current_value": float(f.get("current_value", 0.0) or 0.0),
                "expense_ratio": float(f.get("expense_ratio", 0.0) or 0.0) if f.get("expense_ratio") is not None else None,
                "xirr": float(f.get("xirr", 0.0) or 0.0) if f.get("xirr") is not None else None,
            })

    if not funds:
        return {"status": "unavailable", "message": "No fund records found in portfolio."}

    total_val = sum(f["current_value"] for f in funds)
    valid_xirrs = [f["xirr"] for f in funds if f["xirr"] is not None]
    avg_xirr = (sum(valid_xirrs) / len(valid_xirrs)) if valid_xirrs else None

    valid_expenses = [f["expense_ratio"] for f in funds if f["expense_ratio"] is not None]
    avg_expense = (sum(valid_expenses) / len(valid_expenses)) if valid_expenses else None

    return {
        "status": "available",
        "fund_count": len(funds),
        "total_valuation": format_inr(total_val),
        "average_xirr": f"{avg_xirr * 100.0:.2f}%" if avg_xirr is not None else "Unavailable (needs more transactions)",
        "average_expense_ratio": f"{avg_expense:.2f}%" if avg_expense is not None else "N/A",
        "schemes": [
            {
                "scheme": f["scheme"],
                "value": format_inr(f["current_value"]),
                "xirr": f"{f['xirr'] * 100.0:.2f}%" if f["xirr"] is not None else "N/A",
                "expense_ratio": f"{f['expense_ratio']:.2f}%" if f["expense_ratio"] is not None else "N/A",
            }
            for f in funds[:5]
        ],
    }


def get_focused_context(
    intent: str,
    user_id: str = "default_user",
    portfolio_data: Optional[Any] = None,
    financial_year: str = "2024-25",
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve minimal, focused financial data based on question intent.
    Always includes baseline profile context for personalized anchoring.
    """
    ctx: Dict[str, Any] = {
        "intent": intent,
        "profile": extract_profile_context(user_id=user_id, db_path=db_path),
    }

    if intent in ("HEALTH_SCORE", "GENERAL_SUMMARY"):
        ctx["money_health"] = extract_health_score_context(user_id=user_id, db_path=db_path)
        ctx["risk"] = extract_risk_context(user_id=user_id, db_path=db_path)
        ctx["emergency_fund"] = extract_emergency_fund_context(user_id=user_id, db_path=db_path)
        ctx["budget"] = extract_budget_context(user_id=user_id, db_path=db_path)

    elif intent in ("BUDGET_SAVINGS", "CASH_FLOW"):
        ctx["budget"] = extract_budget_context(user_id=user_id, db_path=db_path)
        ctx["emergency_fund"] = extract_emergency_fund_context(user_id=user_id, db_path=db_path)

    elif intent in ("EMERGENCY_FUND", "LIQUIDITY"):
        ctx["emergency_fund"] = extract_emergency_fund_context(user_id=user_id, db_path=db_path)

    elif intent in ("GOALS_INVESTMENT", "GOALS"):
        ctx["goals"] = extract_goals_context(user_id=user_id, db_path=db_path)
        ctx["risk"] = extract_risk_context(user_id=user_id, db_path=db_path)

    elif intent in ("RETIREMENT_FIRE", "RETIREMENT", "FIRE"):
        ctx["retirement"] = extract_retirement_context(user_id=user_id, db_path=db_path)

    elif intent in ("INSURANCE_PROTECTION", "INSURANCE"):
        ctx["insurance"] = extract_insurance_context(user_id=user_id, db_path=db_path)

    elif intent in ("TAX_PLANNING", "TAX"):
        ctx["tax"] = extract_tax_context(user_id=user_id, financial_year=financial_year, db_path=db_path)

    elif intent in ("PORTFOLIO_CAS", "MUTUAL_FUNDS"):
        ctx["portfolio"] = extract_portfolio_context(portfolio_data=portfolio_data)

    elif intent == "WHAT_IF_SCENARIO":
        ctx["budget"] = extract_budget_context(user_id=user_id, db_path=db_path)
        ctx["emergency_fund"] = extract_emergency_fund_context(user_id=user_id, db_path=db_path)
        ctx["retirement"] = extract_retirement_context(user_id=user_id, db_path=db_path)
        ctx["tax"] = extract_tax_context(user_id=user_id, financial_year=financial_year, db_path=db_path)

    return ctx
