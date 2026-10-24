"""
utils/tax_scenario_calculator.py
What-If Tax-Saving Scenario Simulator for comparing proposed financial moves.
Evaluates incremental tax savings, cash-flow impact, lock-in terms, and surplus affordability.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from utils.tax_calculator import (
    DeductionBreakdown,
    IncomeBreakdown,
    TaxRegimeResult,
    calculate_regime_tax,
    compare_tax_regimes,
)
from data.tax_rules import get_tax_rules


@dataclass
class ProposedTaxMove:
    """A proposed tax-saving contribution or move."""
    category: str             # "80C", "80CCD_1B", "80D", "80CCD_2", "24B", "CUSTOM"
    description: str
    proposed_amount: float
    lock_in_years: Optional[int] = None
    lock_in_note: str = ""
    is_liquid: bool = False


@dataclass
class ScenarioSimulationResult:
    """Output comparing baseline tax against revised scenario."""
    scenario_name: str
    financial_year: str
    proposed_moves: List[ProposedTaxMove]
    total_proposed_outflow: float

    baseline_old_tax: float
    baseline_new_tax: float
    baseline_recommended: str

    revised_old_tax: float
    revised_new_tax: float
    revised_recommended: str

    old_regime_tax_saved: float
    new_regime_tax_saved: float

    effective_tax_saved: float        # Tax saved under best regime
    net_cash_outflow: float           # proposed_outflow - effective_tax_saved
    tax_savings_roi_pct: float        # (tax_saved / proposed_outflow) * 100

    affordability_warning: Optional[str] = None
    lock_in_warnings: List[str] = field(default_factory=list)
    actionable_summary: str = ""


PRESET_TAX_SAVING_MOVES = {
    "ELSS_MAX": ProposedTaxMove(
        category="80C",
        description="Invest in ELSS (Tax Saving Mutual Fund) under Section 80C",
        proposed_amount=50000.0,
        lock_in_years=3,
        lock_in_note="3-year mandatory statutory lock-in (shortest among 80C instruments). Equity market risk applies.",
    ),
    "PPF_MAX": ProposedTaxMove(
        category="80C",
        description="Contribute to Public Provident Fund (PPF) under Section 80C",
        proposed_amount=50000.0,
        lock_in_years=15,
        lock_in_note="15-year statutory lock-in with partial withdrawal after 5 years. Sovereign guarantee with EEE tax status.",
    ),
    "NPS_80CCD_1B": ProposedTaxMove(
        category="80CCD_1B",
        description="Voluntary NPS Tier 1 Contribution under Section 80CCD(1B)",
        proposed_amount=50000.0,
        lock_in_years=None,
        lock_in_note="Locked in until retirement age 60. Market-linked pension with 60% tax-free lump sum and 40% mandatory annuity.",
    ),
    "HEALTH_INSURANCE_SELF": ProposedTaxMove(
        category="80D",
        description="Health Insurance for Self & Family under Section 80D",
        proposed_amount=25000.0,
        lock_in_years=0,
        lock_in_note="Annual insurance protection premium (no lock-in, non-refundable). Enhances medical security.",
    ),
    "HEALTH_INSURANCE_PARENTS": ProposedTaxMove(
        category="80D",
        description="Health Insurance for Senior Parents under Section 80D",
        proposed_amount=50000.0,
        lock_in_years=0,
        lock_in_note="Annual premium for senior citizen parents (deduction limit up to ₹50,000).",
    ),
    "EMPLOYER_NPS_80CCD_2": ProposedTaxMove(
        category="80CCD_2",
        description="Employer NPS Restructuring under Section 80CCD(2)",
        proposed_amount=50000.0,
        lock_in_years=None,
        lock_in_note="Salary restructuring via employer (saves tax under BOTH Old and New regimes!).",
    ),
}


def simulate_tax_scenario(
    scenario_name: str,
    baseline_income: IncomeBreakdown,
    baseline_deductions: DeductionBreakdown,
    proposed_moves: List[ProposedTaxMove],
    financial_year: str = "2024-25",
    age: int = 30,
    monthly_surplus: float = 0.0,
    emergency_fund_months: float = 6.0,
) -> ScenarioSimulationResult:
    """
    Simulate a what-if tax planning scenario without modifying the original financial profile.
    Calculates tax savings under both regimes, liquidity constraints, and surplus feasibility.
    """
    # 1. Baseline comparison
    baseline_comp = compare_tax_regimes(
        income=baseline_income,
        deductions=baseline_deductions,
        financial_year=financial_year,
        age=age,
    )

    # 2. Build revised deductions
    revised_ded = DeductionBreakdown(
        sec_80c=baseline_deductions.sec_80c,
        sec_80d_self=baseline_deductions.sec_80d_self,
        sec_80d_parents=baseline_deductions.sec_80d_parents,
        is_self_senior=baseline_deductions.is_self_senior,
        is_parents_senior=baseline_deductions.is_parents_senior,
        sec_80ccd_1b=baseline_deductions.sec_80ccd_1b,
        sec_80ccd_2=baseline_deductions.sec_80ccd_2,
        sec_24b=baseline_deductions.sec_24b,
        sec_80e=baseline_deductions.sec_80e,
        sec_80g=baseline_deductions.sec_80g,
        hra_exemption=baseline_deductions.hra_exemption,
    )

    total_outflow = 0.0
    lock_in_warnings: List[str] = []

    for move in proposed_moves:
        amt = max(0.0, move.proposed_amount)
        total_outflow += amt
        cat = move.category.upper()

        if "80C" in cat and "80CCD" not in cat:
            revised_ded.sec_80c += amt
        elif "80CCD_1B" in cat or "80CCD(1B)" in cat:
            revised_ded.sec_80ccd_1b += amt
        elif "80CCD_2" in cat or "80CCD(2)" in cat:
            revised_ded.sec_80ccd_2 += amt
        elif "80D_PARENTS" in cat:
            revised_ded.sec_80d_parents += amt
        elif "80D" in cat:
            revised_ded.sec_80d_self += amt
        elif "24B" in cat:
            revised_ded.sec_24b += amt

        if move.lock_in_note:
            lock_in_warnings.append(f"{move.description}: {move.lock_in_note}")

    # 3. Revised comparison
    revised_comp = compare_tax_regimes(
        income=baseline_income,
        deductions=revised_ded,
        financial_year=financial_year,
        age=age,
    )

    old_tax_saved = max(0.0, baseline_comp.old_regime.total_tax_liability - revised_comp.old_regime.total_tax_liability)
    new_tax_saved = max(0.0, baseline_comp.new_regime.total_tax_liability - revised_comp.new_regime.total_tax_liability)

    # Effective tax saved is based on the best revised regime compared to best baseline regime
    baseline_best_tax = min(baseline_comp.old_regime.total_tax_liability, baseline_comp.new_regime.total_tax_liability)
    revised_best_tax = min(revised_comp.old_regime.total_tax_liability, revised_comp.new_regime.total_tax_liability)
    effective_tax_saved = max(0.0, baseline_best_tax - revised_best_tax)

    net_outflow = max(0.0, total_outflow - effective_tax_saved)
    roi_pct = (effective_tax_saved / total_outflow * 100.0) if total_outflow > 0 else 0.0

    # 4. Affordability and Cash Flow Check
    affordability_warning: Optional[str] = None
    annual_surplus = monthly_surplus * 12.0

    if monthly_surplus <= 0:
        affordability_warning = (
            "Caution: You currently have a monthly deficit or zero surplus. Investing extra funds solely "
            "for tax savings may strain your liquid cash flow."
        )
    elif total_outflow > annual_surplus:
        affordability_warning = (
            f"Caution: Proposed total outflow (₹{total_outflow:,.0f}) exceeds your estimated annual surplus "
            f"(₹{annual_surplus:,.0f}). Consider staging your investments across the financial year."
        )
    elif emergency_fund_months < 3.0:
        affordability_warning = (
            f"Advisory: Your emergency fund coverage ({emergency_fund_months:.1f} months) is low. "
            "Prioritize liquid emergency reserves before locking funds in multi-year tax-saving schemes."
        )

    # 5. Actionable summary
    if effective_tax_saved > 0:
        summary = (
            f"By committing ₹{total_outflow:,.0f} across proposed tax moves, you reduce your tax liability by "
            f"₹{effective_tax_saved:,.0f} (an effective return of {roi_pct:.1f}% on tax savings). "
            f"Your net out-of-pocket cost is ₹{net_outflow:,.0f}."
        )
    else:
        summary = (
            f"The proposed moves of ₹{total_outflow:,.0f} yield ₹0 in tax reduction under the "
            f"{revised_comp.recommended_regime} because deductions have either exceeded statutory caps "
            "or do not apply to your optimal regime."
        )

    return ScenarioSimulationResult(
        scenario_name=scenario_name,
        financial_year=financial_year,
        proposed_moves=proposed_moves,
        total_proposed_outflow=total_outflow,
        baseline_old_tax=baseline_comp.old_regime.total_tax_liability,
        baseline_new_tax=baseline_comp.new_regime.total_tax_liability,
        baseline_recommended=baseline_comp.recommended_regime,
        revised_old_tax=revised_comp.old_regime.total_tax_liability,
        revised_new_tax=revised_comp.new_regime.total_tax_liability,
        revised_recommended=revised_comp.recommended_regime,
        old_regime_tax_saved=old_tax_saved,
        new_regime_tax_saved=new_tax_saved,
        effective_tax_saved=effective_tax_saved,
        net_cash_outflow=net_outflow,
        tax_savings_roi_pct=roi_pct,
        affordability_warning=affordability_warning,
        lock_in_warnings=lock_in_warnings,
        actionable_summary=summary,
    )
