"""
utils/insurance_calculator.py
Deterministic mathematical calculations for Health and Life Insurance needs assessment,
along with educational personal accident & disability protection guidelines in AI Money Mentor.
Follows human life value / capital needs analysis without selling or promoting specific products.
"""
from typing import Any, Dict, List, Optional


def calculate_health_insurance_gap(
    personal_coverage: float = 0.0,
    employer_coverage: float = 0.0,
    target_coverage: float = 1000000.0,
    number_of_members: int = 1,
    policy_type: str = "Individual",
) -> Dict[str, Any]:
    """
    Calculate health insurance coverage and evaluate gaps against target coverage.
    Distinguishes employer-provided group coverage from personally owned coverage.

    Args:
        personal_coverage: Current personal / family floater sum insured in ₹.
        employer_coverage: Current employer-provided group health sum insured in ₹.
        target_coverage: Desired health protection target in ₹ (default ₹10 Lakhs).
        number_of_members: Total people covered.
        policy_type: "Individual" or "Family Floater".

    Returns:
        Structured dictionary with coverage sums, gaps, status, and policy checklist.
    """
    personal = max(0.0, float(personal_coverage or 0.0))
    employer = max(0.0, float(employer_coverage or 0.0))
    target = max(0.0, float(target_coverage or 0.0))
    members = max(1, int(number_of_members or 1))

    total_current = round(personal + employer, 2)
    total_gap = round(max(0.0, target - total_current), 2)
    personal_gap = round(max(0.0, target - personal), 2)

    is_adequate_total = total_current >= target and target > 0
    is_adequate_personal = personal >= target and target > 0

    # Categorize status
    if total_current <= 0.0:
        status = "No Coverage"
        tier = "critical"
        badge = "🚨 Uninsured"
        color = "#ef4444"
        summary = "No health insurance coverage reported. Hospitalization costs pose severe out-of-pocket risk."
    elif personal <= 0.0 and employer > 0.0:
        status = "Employer Only"
        tier = "warning"
        badge = "⚠️ Employer Only"
        color = "#f59e0b"
        summary = (
            f"You have ₹{employer:,.0f} employer coverage, but no personal policy. "
            "Employer cover is contingent on employment and terminates during job changes, layoffs, or retirement."
        )
    elif total_gap > 0.0:
        status = "Under-Insured"
        tier = "warning"
        badge = f"⚠️ Gap of ₹{total_gap:,.0f}"
        color = "#f59e0b"
        summary = f"Total coverage (₹{total_current:,.0f}) is below your stated target of ₹{target:,.0f}."
    elif not is_adequate_personal:
        status = "Adequate with Employer Cover"
        tier = "info"
        badge = "ℹ️ Met via Employer"
        color = "#3b82f6"
        summary = f"Total coverage meets target (₹{total_current:,.0f}), but personal standalone cover is ₹{personal:,.0f}."
    else:
        status = "Adequately Covered"
        tier = "safe"
        badge = "✅ Adequately Covered"
        color = "#10b981"
        summary = f"Your personal coverage (₹{personal:,.0f}) fully meets your stated protection target of ₹{target:,.0f}."

    checklist = [
        "Room Rent Sub-limits: Check if room rent is capped (e.g. 1% of sum insured) which can trigger proportionate deductions.",
        "Pre-Existing Disease (PED) Waiting Period: Verify waiting periods (typically 1 to 3 years) for chronic conditions.",
        "Co-payment Clauses: Confirm if your policy mandates a percentage payment (e.g. 10-20% for senior citizens).",
        "Restoration Benefits: Check if your policy automatically restores sum insured after a claim in the same policy year.",
        "Super Top-up Feasibility: Consider a super top-up policy with a deductible matching your base cover for cost-effective protection.",
    ]

    return {
        "personal_coverage": round(personal, 2),
        "employer_coverage": round(employer, 2),
        "total_current_coverage": total_current,
        "target_coverage": round(target, 2),
        "total_coverage_gap": total_gap,
        "personal_coverage_gap": personal_gap,
        "is_adequate_total": is_adequate_total,
        "is_adequate_personal": is_adequate_personal,
        "number_of_members": members,
        "policy_type": policy_type,
        "status": status,
        "tier": tier,
        "badge": badge,
        "color": color,
        "summary": summary,
        "checklist": checklist,
    }


def calculate_life_insurance_needs(
    annual_income: float,
    number_of_dependents: int = 0,
    income_replacement_years: float = 10.0,
    outstanding_liabilities: float = 0.0,
    future_family_obligations: float = 0.0,
    specified_goals: float = 0.0,
    existing_eligible_assets: float = 0.0,
    existing_life_insurance: float = 0.0,
) -> Dict[str, Any]:
    """
    Needs-based Life Insurance estimation (Human Life Value / Capital Needs Analysis).

    Formula:
        Estimated Need = Outstanding Liabilities
                         + Future Family Obligations
                         + Specified Goals
                         + Income Replacement Reserve
                         - Existing Eligible Assets
                         - Existing Life Insurance Coverage

    Args:
        annual_income: User's annual take-home income in ₹.
        number_of_dependents: Count of financial dependents.
        income_replacement_years: Configurable multiplier years (e.g. 5 to 15, default 10).
        outstanding_liabilities: Mortgages, loans, and other debts.
        future_family_obligations: Living costs support for dependents.
        specified_goals: Children's education, marriage, or other committed goals.
        existing_eligible_assets: Liquid savings & investments meant for dependents.
        existing_life_insurance: Existing term life sum assured.

    Returns:
        Structured dictionary with breakdown of each component, additional gap, and notes.
    """
    income = max(0.0, float(annual_income or 0.0))
    deps = max(0, int(number_of_dependents or 0))
    multiplier = max(0.0, float(income_replacement_years or 0.0))
    debts = max(0.0, float(outstanding_liabilities or 0.0))
    obligations = max(0.0, float(future_family_obligations or 0.0))
    goals = max(0.0, float(specified_goals or 0.0))
    assets = max(0.0, float(existing_eligible_assets or 0.0))
    existing_cover = max(0.0, float(existing_life_insurance or 0.0))

    # If user has NO dependents and NO obligations/debts:
    if deps == 0 and obligations == 0.0 and goals == 0.0 and debts == 0.0:
        return {
            "has_dependents": False,
            "number_of_dependents": 0,
            "income_replacement_years": multiplier,
            "income_replacement_reserve": 0.0,
            "outstanding_liabilities": 0.0,
            "future_family_obligations": 0.0,
            "specified_goals": 0.0,
            "gross_protection_need": 0.0,
            "existing_eligible_assets": round(assets, 2),
            "existing_life_insurance": round(existing_cover, 2),
            "total_existing_resources": round(assets + existing_cover, 2),
            "net_additional_need": 0.0,
            "is_adequately_covered": True,
            "status": "No Life Cover Needed",
            "tier": "safe",
            "badge": "✅ No Dependents",
            "color": "#10b981",
            "summary": (
                "You have no financial dependents or outstanding liabilities reported. "
                "Pure term life insurance is typically unnecessary when nobody relies on your income for survival."
            ),
            "assumptions": [
                "Life insurance protects dependents against loss of breadwinner income.",
                "Without financial dependents or debts, long-term savings should be prioritized over term insurance.",
            ],
        }

    # Income replacement reserve only applies if there are dependents or family obligations
    income_reserve = round(income * multiplier, 2) if (deps > 0 or obligations > 0) else 0.0

    gross_need = round(debts + obligations + goals + income_reserve, 2)
    total_resources = round(assets + existing_cover, 2)

    raw_gap = gross_need - total_resources
    additional_gap = round(max(0.0, raw_gap), 2)
    is_adequate = additional_gap <= 0.0

    if is_adequate:
        status = "Adequately Protected"
        tier = "safe"
        badge = "✅ Sufficiently Covered"
        color = "#10b981"
        summary = (
            f"Your existing life insurance (₹{existing_cover:,.0f}) and eligible assets (₹{assets:,.0f}) "
            f"meet or exceed your calculated need of ₹{gross_need:,.0f}."
        )
    elif existing_cover <= 0.0:
        status = "Critical Life Gap"
        tier = "critical"
        badge = f"🚨 Need ₹{additional_gap:,.0f}"
        color = "#ef4444"
        summary = (
            f"You have {deps} dependent(s) and outstanding obligations, but no active life insurance. "
            f"Estimated protection gap is ₹{additional_gap:,.0f}."
        )
    else:
        status = "Under-Insured"
        tier = "warning"
        badge = f"⚠️ Gap of ₹{additional_gap:,.0f}"
        color = "#f59e0b"
        summary = (
            f"Current life cover of ₹{existing_cover:,.0f} falls short of gross obligations. "
            f"Additional term insurance gap: ₹{additional_gap:,.0f}."
        )

    return {
        "has_dependents": deps > 0,
        "number_of_dependents": deps,
        "income_replacement_years": multiplier,
        "income_replacement_reserve": income_reserve,
        "outstanding_liabilities": round(debts, 2),
        "future_family_obligations": round(obligations, 2),
        "specified_goals": round(goals, 2),
        "gross_protection_need": gross_need,
        "existing_eligible_assets": round(assets, 2),
        "existing_life_insurance": round(existing_cover, 2),
        "total_existing_resources": total_resources,
        "net_additional_need": additional_gap,
        "is_adequately_covered": is_adequate,
        "status": status,
        "tier": tier,
        "badge": badge,
        "color": color,
        "summary": summary,
        "assumptions": [
            f"Income replacement assumed at {multiplier:.0f}x annual income (₹{income_reserve:,.0f}).",
            f"Outstanding debt liabilities: ₹{debts:,.0f}.",
            f"Future education & family obligations: ₹{obligations + goals:,.0f}.",
            f"Eligible non-retirement assets deducted: ₹{assets:,.0f}.",
            "Pure term life insurance is recommended rather than investment-linked policies (ULIP/Endowment).",
        ],
    }


def evaluate_personal_accident_coverage(
    annual_income: float,
    has_accident_cover: bool = False,
    current_sum_insured: float = 0.0,
) -> Dict[str, Any]:
    """
    Educational assessment of Personal Accident and Disability protection.
    Explains the role of Accidental Death, Permanent Total Disability (PTD),
    and Permanent Partial Disability (PPD).
    """
    income = max(0.0, float(annual_income or 0.0))
    monthly_inc = income / 12.0
    has_cover = bool(has_accident_cover)
    sum_insured = max(0.0, float(current_sum_insured or 0.0))

    # Benchmark: 5x to 10x annual income (50x-100x monthly income)
    benchmark_min = round(income * 5.0, 2)
    benchmark_max = round(income * 10.0, 2)

    if not has_cover:
        status = "No Accident/Disability Cover"
        tier = "warning"
        badge = "⚠️ Unprotected"
        color = "#f59e0b"
        summary = (
            "You reported no personal accident or disability protection. "
            "Neither health insurance nor life insurance covers living income loss caused by permanent disability."
        )
    elif sum_insured < benchmark_min and benchmark_min > 0:
        status = "Limited Coverage"
        tier = "info"
        badge = "ℹ️ Modest Cover"
        color = "#3b82f6"
        summary = (
            f"You have ₹{sum_insured:,.0f} personal accident cover. "
            f"For your income level, financial planners generally benchmark 5x–10x annual income (₹{benchmark_min:,.0f}–₹{benchmark_max:,.0f})."
        )
    else:
        status = "Protected"
        tier = "safe"
        badge = "✅ Covered"
        color = "#10b981"
        summary = f"You hold ₹{sum_insured:,.0f} in personal accident & disability protection."

    checklist = [
        "Permanent Total Disability (PTD): Ensures 100% to 150% sum insured payout on loss of limbs, sight, or complete inability to work.",
        "Permanent Partial Disability (PPD): Ensures percentage payout based on defined disability schedule.",
        "Temporary Total Disability (TTD): Provides weekly cash compensation (e.g. up to 100 weeks) during temporary bedrest.",
        "Worldwide Coverage: Confirms 24x7 coverage globally for accidents.",
    ]

    return {
        "has_accident_cover": has_cover,
        "current_sum_insured": round(sum_insured, 2),
        "benchmark_recommended_range": f"₹{benchmark_min:,.0f} – ₹{benchmark_max:,.0f}" if income > 0 else "N/A",
        "status": status,
        "tier": tier,
        "badge": badge,
        "color": color,
        "summary": summary,
        "checklist": checklist,
    }
