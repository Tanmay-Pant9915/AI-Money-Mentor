"""
utils/tax_recommendations.py
Deterministic recommendation engine generating prioritized, explainable tax-planning actions.
Complies with Indian tax regulations and cross-references user's emergency fund and budget.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from utils.tax_calculator import (
    DeductionBreakdown,
    IncomeBreakdown,
    RegimeComparisonResult,
)


@dataclass
class TaxRecommendation:
    """Actionable tax-planning recommendation."""
    priority: str          # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    title: str
    category: str          # "REGIME", "DEDUCTION", "PROTECTION", "ADVANCE_TAX", "CAPITAL_GAINS", "LIQUIDITY"
    reason: str
    suggested_action: str
    potential_tax_saving: Optional[float] = None
    assumptions_note: str = ""


def generate_tax_recommendations(
    comparison: RegimeComparisonResult,
    income: IncomeBreakdown,
    deductions: DeductionBreakdown,
    taxes_paid: float = 0.0,
    emergency_months: float = 6.0,
    monthly_surplus: float = 0.0,
    has_capital_gains: bool = False,
    capital_gains_summary: Optional[Dict[str, Any]] = None,
) -> List[TaxRecommendation]:
    """
    Generate deterministic, ranked tax-planning recommendations based on user's exact numbers.
    """
    recs: List[TaxRecommendation] = []

    old_res = comparison.old_regime
    new_res = comparison.new_regime
    tax_diff = comparison.tax_difference

    # 1. Regime Choice Recommendation
    if comparison.recommended_regime == "New Regime" and tax_diff > 500:
        recs.append(TaxRecommendation(
            priority="CRITICAL",
            title=f"Choose the New Tax Regime (Saves ₹{tax_diff:,.0f})",
            category="REGIME",
            reason=(
                f"Under the New Regime (Section 115BAC), your total tax is ₹{new_res.total_tax_liability:,.0f} "
                f"versus ₹{old_res.total_tax_liability:,.0f} in the Old Regime. You save ₹{tax_diff:,.0f} due to "
                f"concessional slabs, ₹75,000 standard deduction, and full rebate up to ₹7,00,000."
            ),
            suggested_action="Select the New Tax Regime when filing your ITR and declaring tax regime to your employer.",
            potential_tax_saving=tax_diff,
            assumptions_note="Assumes current reported income and deductions remain unchanged.",
        ))
    elif comparison.recommended_regime == "Old Regime" and tax_diff > 500:
        recs.append(TaxRecommendation(
            priority="CRITICAL",
            title=f"Opt for the Old Tax Regime (Saves ₹{tax_diff:,.0f})",
            category="REGIME",
            reason=(
                f"Your itemized deductions and exemptions total ₹{old_res.total_deductions_exemptions:,.0f}, "
                f"reducing your tax under the Old Regime to ₹{old_res.total_tax_liability:,.0f} compared to "
                f"₹{new_res.total_tax_liability:,.0f} in the New Regime."
            ),
            suggested_action="Submit Section 80C, 80D, HRA, and housing loan proofs to your employer and file under Old Regime.",
            potential_tax_saving=tax_diff,
            assumptions_note="Requires submitting valid documentary proof for all claimed deductions.",
        ))

    # 2. Advance Tax Liability Warning
    best_tax = min(old_res.total_tax_liability, new_res.total_tax_liability)
    remaining_tax_payable = max(0.0, best_tax - taxes_paid)
    if remaining_tax_payable >= 10000.0:
        recs.append(TaxRecommendation(
            priority="HIGH",
            title=f"Review Advance Tax Installments (Remaining Tax: ₹{remaining_tax_payable:,.0f})",
            category="ADVANCE_TAX",
            reason=(
                f"Your estimated tax payable after TDS is ₹{remaining_tax_payable:,.0f}. Under Section 208 of the "
                "Income-tax Act, if net tax liability exceeds ₹10,000, advance tax must be paid in quarterly installments."
            ),
            suggested_action=(
                "Pay advance tax before statutory due dates (15 June: 15%, 15 Sept: 45%, 15 Dec: 75%, 15 March: 100%) "
                "to avoid interest penalties under Section 234B and 234C."
            ),
            potential_tax_saving=None,
            assumptions_note="Applicable if your employer has not deducted sufficient TDS on other sources of income.",
        ))

    # 3. Cash Flow / Liquidity Pre-requisite Check
    if monthly_surplus <= 0:
        recs.append(TaxRecommendation(
            priority="HIGH",
            title="Avoid Locking Cash in Tax Instruments During Monthly Deficit",
            category="LIQUIDITY",
            reason=(
                "Your current monthly budget indicates zero surplus or deficit. Locking money in long-term "
                "tax-saving schemes (PPF: 15 years, ELSS: 3 years, NPS: age 60) may induce a cash-flow crunch."
            ),
            suggested_action="Focus on stabilizing monthly cash flow and building liquid reserves before committing to illiquid tax products.",
            potential_tax_saving=None,
            assumptions_note="Tax savings should not compromise immediate liquidity and emergency buffer.",
        ))
    elif emergency_months < 3.0:
        recs.append(TaxRecommendation(
            priority="MEDIUM",
            title="Maintain 3+ Months Liquid Buffer Before Long Lock-In Investments",
            category="LIQUIDITY",
            reason=(
                f"Your emergency fund is currently at {emergency_months:.1f} months. Investing large amounts in "
                "multi-year locked-in tax instruments leaves you vulnerable to emergency borrowing."
            ),
            suggested_action="Consider liquid or short-term options (like ELSS 3-year lock-in or health insurance) over 15-year PPF commitments.",
            potential_tax_saving=None,
            assumptions_note="Emergency fund runway takes priority over multi-decade lock-ins.",
        ))

    # 4. Employer NPS Section 80CCD(2) Opportunity (Works in BOTH Regimes!)
    if income.salary_gross > 500000.0 and deductions.sec_80ccd_2 <= 0:
        indicative_emp_nps = min(50000.0, income.salary_gross * 0.10)
        indicative_tax_save = indicative_emp_nps * 0.20  # ~20% slab rate
        recs.append(TaxRecommendation(
            priority="MEDIUM",
            title="Request Employer NPS Restructuring under Section 80CCD(2)",
            category="DEDUCTION",
            reason=(
                "Employer contribution to NPS Tier 1 (up to 14% of basic salary) is tax-exempt under BOTH Old and "
                "New Regimes. Most employees overlook this valuable cross-regime deduction."
            ),
            suggested_action=(
                f"Check with your HR/payroll if your corporate compensation structure permits employer NPS. "
                f"A ₹{indicative_emp_nps:,.0f} annual allocation could save approx ₹{indicative_tax_save:,.0f} in tax."
            ),
            potential_tax_saving=indicative_tax_save,
            assumptions_note="Subject to employer corporate NPS tie-up and salary restructuring terms.",
        ))

    # 5. Section 80C Headroom (If Old Regime preferred or close)
    if comparison.recommended_regime == "Old Regime" and deductions.sec_80c < 150000.0:
        headroom_80c = 150000.0 - deductions.sec_80c
        est_save = headroom_80c * 0.20  # estimated at 20% slab
        recs.append(TaxRecommendation(
            priority="MEDIUM",
            title=f"Utilize Remaining Section 80C Headroom (₹{headroom_80c:,.0f} Unused)",
            category="DEDUCTION",
            reason=(
                f"You have claimed ₹{deductions.sec_80c:,.0f} out of the ₹1,50,000 statutory limit under Section 80C. "
                f"Investing the remaining ₹{headroom_80c:,.0f} can reduce your taxable income under the Old Regime."
            ),
            suggested_action="Consider ELSS mutual funds (3-year lock-in) or PPF based on your asset allocation.",
            potential_tax_saving=est_save,
            assumptions_note="Only benefits you if you file under the Old Tax Regime.",
        ))

    # 6. Section 80CCD(1B) Additional NPS (If Old Regime preferred)
    if comparison.recommended_regime == "Old Regime" and deductions.sec_80ccd_1b < 50000.0:
        headroom_nps = 50000.0 - deductions.sec_80ccd_1b
        est_save_nps = headroom_nps * 0.20
        recs.append(TaxRecommendation(
            priority="LOW",
            title=f"Evaluate Section 80CCD(1B) NPS Tier 1 (Up to ₹{headroom_nps:,.0f} Headroom)",
            category="DEDUCTION",
            reason=(
                "Section 80CCD(1B) allows an exclusive additional deduction of up to ₹50,000 for NPS Tier 1, "
                "over and above the Section 80C limit (Old Regime only)."
            ),
            suggested_action="Contribute to voluntary NPS Tier 1 if you seek supplementary retirement corpus.",
            potential_tax_saving=est_save_nps,
            assumptions_note="Note the lock-in until age 60 and mandatory 40% annuity purchase.",
        ))

    # 7. Section 80D Health Insurance Dual Benefit
    if deductions.sec_80d_self <= 0:
        recs.append(TaxRecommendation(
            priority="MEDIUM",
            title="Obtain Health Insurance for Dual Protection and 80D Tax Benefit",
            category="PROTECTION",
            reason=(
                "Health insurance provides crucial protection against hospital bills, while qualifying for up to "
                "₹25,000 (₹50,000 for seniors) tax deduction under Section 80D in the Old Regime."
            ),
            suggested_action="Secure an adequate personal health cover to protect savings and optimize tax liability.",
            potential_tax_saving=5000.0,
            assumptions_note="Protects against catastrophic medical expenses while providing tax relief.",
        ))

    # 8. Capital Gains Annual LTCG Harvesting (If CAS data available)
    if capital_gains_summary and capital_gains_summary.get("has_data"):
        ltcg_gains = capital_gains_summary.get("total_ltcg_equity_gains", 0.0)
        exemption_limit = capital_gains_summary.get("equity_ltcg_exemption_limit", 125000.0)
        exemption_rem = capital_gains_summary.get("exemption_remaining", 0.0)

        if exemption_rem > 10000.0 and ltcg_gains > 0:
            recs.append(TaxRecommendation(
                priority="LOW",
                title=f"Harvest Tax-Free Equity LTCG (₹{exemption_rem:,.0f} Exemption Remaining)",
                category="CAPITAL_GAINS",
                reason=(
                    f"Under Section 112A, long-term equity gains up to ₹{exemption_limit:,.0f} are 100% tax-free "
                    f"every financial year. You still have ₹{exemption_rem:,.0f} unutilized exemption."
                ),
                suggested_action="Consider selling and re-investing eligible long-term equity units to step up your cost basis tax-free.",
                potential_tax_saving=exemption_rem * 0.125,
                assumptions_note="Account for fund exit loads and market timing before executing tax-gain harvesting.",
            ))

    # Priority sorting order: CRITICAL > HIGH > MEDIUM > LOW
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    recs.sort(key=lambda r: priority_order.get(r.priority, 99))

    return recs
