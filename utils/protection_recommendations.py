"""
utils/protection_recommendations.py
Deterministic recommendation engine and protection summary evaluator for AI Money Mentor.
Prioritizes financial resilience, emergency buffers, and insurance coverage gaps
based strictly on user-supplied financial data.
"""
from typing import Any, Dict, List, Optional


def generate_protection_recommendations(
    emergency_plan: Dict[str, Any],
    health_assessment: Dict[str, Any],
    life_assessment: Dict[str, Any],
    accident_assessment: Dict[str, Any],
    available_surplus: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Generate deterministic, prioritized actionable recommendations based on actual user protection data.
    """
    recs: List[Dict[str, Any]] = []

    # 1. EMERGENCY FUND CHECKS
    ef_status = emergency_plan.get("status")
    ef_gap = float(emergency_plan.get("gap", 0.0))
    ef_coverage = float(emergency_plan.get("coverage_months", 0.0))

    if ef_coverage < 1.0:
        recs.append({
            "priority": "High",
            "category": "Emergency Fund",
            "title": "Establish an Immediate 1-Month Cash Buffer",
            "reason": f"Liquid savings cover only {ef_coverage:.1f} months of essential expenses. Any unexpected expense or job gap will force high-cost debt or distress asset liquidation.",
            "suggested_action": "Pause non-essential discretionary investments temporarily to accumulate an immediate 1-month cash buffer in a high-yield savings account.",
            "assumptions": "Assumes liquid savings reported accurately reflect immediate withdrawal access.",
        })
    elif ef_gap > 0.0:
        if available_surplus is not None and available_surplus > 0:
            recs.append({
                "priority": "Medium",
                "category": "Emergency Fund",
                "title": "Build Emergency Fund to Full Target",
                "reason": f"Remaining emergency fund gap is ₹{ef_gap:,.0f} to reach your {emergency_plan.get('target_months', 6):.0f}-month safety target.",
                "suggested_action": f"Automate a recurring monthly transfer from your surplus (suggested: ₹{emergency_plan.get('recommended_monthly', 0):,.0f}/mo) into a dedicated liquid account.",
                "assumptions": "Calculated based on current reported monthly essential expenses.",
            })
        else:
            recs.append({
                "priority": "Medium",
                "category": "Emergency Fund",
                "title": "Review Budget to Close Emergency Fund Gap",
                "reason": f"A gap of ₹{ef_gap:,.0f} remains, but available monthly surplus is zero or in deficit.",
                "suggested_action": "Audit essential vs. discretionary expenses to restore positive cash flow and build your emergency buffer.",
                "assumptions": "Requires positive monthly surplus to accumulate emergency reserves.",
            })

    # 2. HEALTH INSURANCE CHECKS
    h_total_current = float(health_assessment.get("total_current_coverage", 0.0))
    h_personal = float(health_assessment.get("personal_coverage", 0.0))
    h_employer = float(health_assessment.get("employer_coverage", 0.0))
    h_gap = float(health_assessment.get("total_coverage_gap", 0.0))

    if h_total_current <= 0.0:
        recs.append({
            "priority": "High",
            "category": "Health Insurance",
            "title": "Secure Basic Health Insurance Coverage",
            "reason": "You have zero health insurance reported. A single major hospitalization can wipe out years of savings.",
            "suggested_action": "Explore an individual or family floater base health policy (minimum ₹5–10 Lakhs) with no room-rent capping.",
            "assumptions": "Medical inflation in India averages 12–14% annually.",
        })
    elif h_personal <= 0.0 and h_employer > 0.0:
        recs.append({
            "priority": "High",
            "category": "Health Insurance",
            "title": "Procure a Standalone Personal Health Policy",
            "reason": f"All ₹{h_employer:,.0f} of health coverage is employer-provided. Group cover terminates immediately during job changes, layoffs, or retirement.",
            "suggested_action": "Establish an independent personal base cover (₹5–10 Lakhs) plus a high-deductible super top-up policy while you are young and healthy.",
            "assumptions": "Personal policies lock in lower premiums and start the clock on pre-existing condition waiting periods early.",
        })
    elif h_gap > 0.0:
        recs.append({
            "priority": "Medium",
            "category": "Health Insurance",
            "title": f"Bridge Health Insurance Gap of ₹{h_gap:,.0f}",
            "reason": f"Your current coverage is ₹{h_total_current:,.0f}, below your desired target of ₹{health_assessment.get('target_coverage', 0):,.0f}.",
            "suggested_action": "Evaluate a Super Top-up health plan with a deductible equal to your existing base cover to bridge the gap cost-effectively.",
            "assumptions": "Super top-up plans offer high sum insured at substantially lower premiums than separate base policies.",
        })

    # 3. LIFE INSURANCE CHECKS
    has_deps = bool(life_assessment.get("has_dependents", False))
    l_gap = float(life_assessment.get("net_additional_need", 0.0))
    l_existing = float(life_assessment.get("existing_life_insurance", 0.0))

    if has_deps and l_gap > 0.0:
        priority_lvl = "High" if l_existing <= 0.0 else "Medium"
        recs.append({
            "priority": priority_lvl,
            "category": "Life Insurance",
            "title": f"Secure ₹{l_gap:,.0f} Pure Term Life Cover",
            "reason": f"You have {life_assessment.get('number_of_dependents', 1)} dependent(s) and outstanding obligations, leaving a net coverage shortfall of ₹{l_gap:,.0f}.",
            "suggested_action": "Consider buying a pure term life insurance policy for the shortfall amount. Avoid investment-cum-insurance products (ULIPs/Endowments) which offer low cover at high cost.",
            "assumptions": f"Based on {life_assessment.get('income_replacement_years', 10):.0f} years of income replacement and reported liabilities.",
        })
    elif not has_deps and float(life_assessment.get("outstanding_liabilities", 0.0)) > 0 and l_gap > 0.0:
        recs.append({
            "priority": "Medium",
            "category": "Life Insurance",
            "title": "Protect Outstanding Liabilities with Term Cover",
            "reason": f"You reported ₹{life_assessment.get('outstanding_liabilities', 0):,.0f} in debt. In the event of death, lenders may repossess assets or burden co-signers.",
            "suggested_action": "Maintain term life cover at least matching outstanding loan liabilities until debts are fully repaid.",
            "assumptions": "Loan protection reduces financial risk for family co-signers.",
        })

    # 4. PERSONAL ACCIDENT & DISABILITY CHECKS
    has_acc = bool(accident_assessment.get("has_accident_cover", False))
    if not has_acc:
        recs.append({
            "priority": "Low",
            "category": "Personal Accident",
            "title": "Add Personal Accident & Disability Coverage",
            "reason": "Neither health insurance (which covers hospital bills) nor life insurance (which pays only upon death) compensates for loss of income caused by permanent disability.",
            "suggested_action": "Review a comprehensive personal accident policy covering Permanent Total Disability (PTD) and temporary income loss.",
            "assumptions": "Accident insurance premiums are very affordable (typically ₹1,500–₹3,000 per year per ₹25 Lakhs cover).",
        })

    # 5. GENERAL POLICY HYGIENE
    recs.append({
        "priority": "Low",
        "category": "Policy Management",
        "title": "Verify Policy Nominations and Documentation",
        "reason": "Outdated nominee records or missing e-insurance account (eIA) details cause severe delays during insurance claim settlement.",
        "suggested_action": "Check that policy beneficiaries are up to date and share policy numbers and insurer contact details with your family.",
        "assumptions": "Good record keeping expedites emergency claim processing.",
    })

    return recs


def evaluate_overall_protection_status(
    emergency_plan: Dict[str, Any],
    health_assessment: Dict[str, Any],
    life_assessment: Dict[str, Any],
    accident_assessment: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Produce a balanced multi-pillar scorecard of the user's overall financial protection,
    avoiding artificial single scores while clearly showing strengths and vulnerabilities.
    """
    ef_status = emergency_plan.get("status", "Unknown")
    h_status = health_assessment.get("status", "Unknown")
    l_status = life_assessment.get("status", "Unknown")
    acc_status = accident_assessment.get("status", "Unknown")

    ef_tier = emergency_plan.get("tier", "info")
    h_tier = health_assessment.get("tier", "info")
    l_tier = life_assessment.get("tier", "info")
    acc_tier = accident_assessment.get("tier", "info")

    tiers = [ef_tier, h_tier, l_tier, acc_tier]

    if "critical" in tiers:
        overall_status = "Vulnerable (Critical Gaps)"
        overall_badge = "🚨 Vulnerable"
        overall_color = "#ef4444"
        summary_text = "You have critical vulnerabilities in your financial defense (such as < 1 month emergency buffer or zero health/life cover). Prioritize resilience before aggressive investing."
    elif tiers.count("warning") >= 2:
        overall_status = "Partially Protected"
        overall_badge = "⚠️ Needs Attention"
        overall_color = "#f59e0b"
        summary_text = "Foundational safety is partially established, but noticeable gaps exist in emergency reserves or standalone insurance coverage."
    elif "warning" in tiers:
        overall_status = "Moderate Protection"
        overall_badge = "ℹ️ Moderate Protection"
        overall_color = "#3b82f6"
        summary_text = "Good protection foundation in place with minor areas for enhancement (such as extending emergency runway or bridging top-up insurance)."
    else:
        overall_status = "Strong Protection Foundation"
        overall_badge = "✅ Resilient"
        overall_color = "#10b981"
        summary_text = "Your emergency savings and insurance coverage appear well-aligned with your stated protection targets and family obligations."

    pillars = [
        {
            "pillar": "Emergency Fund",
            "metric": f"{emergency_plan.get('coverage_months', 0):.1f} Months",
            "status": ef_status,
            "badge": emergency_plan.get("badge", ""),
            "color": emergency_plan.get("color", "#94a3b8"),
        },
        {
            "pillar": "Health Insurance",
            "metric": f"₹{health_assessment.get('total_current_coverage', 0):,.0f}",
            "status": h_status,
            "badge": health_assessment.get("badge", ""),
            "color": health_assessment.get("color", "#94a3b8"),
        },
        {
            "pillar": "Life Insurance",
            "metric": f"₹{life_assessment.get('existing_life_insurance', 0):,.0f}" if life_assessment.get("has_dependents") else "Not Needed",
            "status": l_status,
            "badge": life_assessment.get("badge", ""),
            "color": life_assessment.get("color", "#94a3b8"),
        },
        {
            "pillar": "Accident & Disability",
            "metric": f"₹{accident_assessment.get('current_sum_insured', 0):,.0f}" if accident_assessment.get("has_accident_cover") else "No Cover",
            "status": acc_status,
            "badge": accident_assessment.get("badge", ""),
            "color": accident_assessment.get("color", "#94a3b8"),
        },
    ]

    return {
        "overall_status": overall_status,
        "overall_badge": overall_badge,
        "overall_color": overall_color,
        "summary_text": summary_text,
        "pillars": pillars,
    }
