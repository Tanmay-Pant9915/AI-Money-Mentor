"""
utils/tax_calculator.py
Deterministic Indian Income Tax calculator supporting Old and New Tax Regimes.
Complies with official Finance Act 2024 / Income-tax Act, 1961 provisions.
"""
from dataclasses import dataclass, field
from math import ceil, floor
from typing import Any, Dict, List, Optional, Tuple

from data.tax_rules import (
    DEDUCTION_LIMITS,
    RegimeRules,
    TaxSlab,
    get_tax_rules,
)


def round_to_nearest_ten(amount: float) -> float:
    """
    Round income/tax to the nearest ₹10 as per Section 288A/288B of Income-tax Act.
    If the last digit is 5 or more, rounded up to next multiple of 10, else rounded down.
    """
    if amount is None or amount <= 0:
        return 0.0
    return float(round(amount / 10.0) * 10)


@dataclass
class IncomeBreakdown:
    """Detailed income breakdown across supported heads of income."""
    salary_gross: float = 0.0
    house_property_net: float = 0.0
    other_sources_interest: float = 0.0
    other_sources_other: float = 0.0
    business_profession_net: float = 0.0
    special_capital_gains: float = 0.0  # Handled with special tax rates separately

    @property
    def gross_total_income(self) -> float:
        """Total gross income before deductions."""
        return max(
            0.0,
            self.salary_gross
            + self.house_property_net
            + self.other_sources_interest
            + self.other_sources_other
            + self.business_profession_net
        )


@dataclass
class DeductionBreakdown:
    """Itemized deductions claimed under Chapter VI-A and other provisions."""
    sec_80c: float = 0.0              # PPF, EPF, ELSS, Life insurance, Principal
    sec_80d_self: float = 0.0         # Health insurance for self, spouse, kids
    sec_80d_parents: float = 0.0      # Health insurance for parents
    is_self_senior: bool = False      # Whether taxpayer/spouse is senior citizen (60+)
    is_parents_senior: bool = False   # Whether parents are senior citizens (60+)
    sec_80ccd_1b: float = 0.0         # Additional voluntary NPS Tier 1
    sec_80ccd_2: float = 0.0          # Employer NPS contribution
    sec_24b: float = 0.0              # Home loan interest (self-occupied)
    sec_80e: float = 0.0              # Higher education loan interest
    sec_80g: float = 0.0              # Approved charitable donations
    hra_exemption: float = 0.0        # Calculated HRA exemption


@dataclass
class TaxRegimeResult:
    """Computation summary for a specific tax regime."""
    regime_name: str
    financial_year: str
    gross_total_income: float
    standard_deduction: float
    chapter_via_deductions: float
    hra_exemption: float
    sec_24b_deduction: float
    total_deductions_exemptions: float
    taxable_income: float
    tax_at_slab_rates: float
    sec_87a_rebate: float
    marginal_relief_87a: float
    tax_after_rebate: float
    surcharge: float
    health_education_cess: float
    total_tax_liability: float
    tds_and_taxes_paid: float
    net_tax_payable: float
    potential_refund: float
    deduction_details: Dict[str, Any] = field(default_factory=dict)
    slab_breakdown: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RegimeComparisonResult:
    """Side-by-side comparison between Old and New regimes."""
    financial_year: str
    old_regime: TaxRegimeResult
    new_regime: TaxRegimeResult
    recommended_regime: str             # "New Regime", "Old Regime", or "Both Equal"
    tax_difference: float               # Absolute difference in total tax
    percentage_savings: float           # Savings as % of higher tax liability
    break_even_deductions: float        # Deductions needed under Old to match New
    summary_explanation: str


def calculate_hra_exemption(
    actual_hra_received: float,
    basic_salary: float,
    rent_paid: float,
    is_metro_city: bool = False,
) -> Dict[str, Any]:
    """
    Calculate eligible HRA exemption under Section 10(13A) of Income-tax Act.
    Exemption is minimum of:
    1. Actual HRA received
    2. Rent paid in excess of 10% of basic salary (max(0, rent_paid - 0.10 * basic_salary))
    3. 50% of basic salary for metro cities (Delhi, Mumbai, Kolkata, Chennai) or 40% for non-metro.
    """
    if actual_hra_received <= 0 or rent_paid <= 0 or basic_salary <= 0:
        return {
            "eligible_exemption": 0.0,
            "taxable_hra": max(0.0, actual_hra_received),
            "actual_hra": actual_hra_received,
            "rent_minus_10pct": 0.0,
            "salary_percentage_limit": 0.0,
        }

    condition_1 = actual_hra_received
    condition_2 = max(0.0, rent_paid - (0.10 * basic_salary))
    condition_3 = (0.50 if is_metro_city else 0.40) * basic_salary

    eligible = min(condition_1, condition_2, condition_3)
    taxable = max(0.0, actual_hra_received - eligible)

    return {
        "eligible_exemption": eligible,
        "taxable_hra": taxable,
        "actual_hra": condition_1,
        "rent_minus_10pct": condition_2,
        "salary_percentage_limit": condition_3,
    }


def compute_eligible_deductions(
    deductions: DeductionBreakdown,
    regime_type: str,  # "old" or "new"
    interest_income: float = 0.0,
    age: int = 30,
) -> Tuple[float, Dict[str, Any]]:
    """
    Filter and apply statutory legal caps to claimed deductions.
    Returns (total_eligible_deduction, breakdown_dict).
    """
    is_old = regime_type.lower() == "old"
    details: Dict[str, Any] = {}
    total = 0.0

    # 1. Section 80C (Old regime only)
    if is_old:
        claimed_80c = max(0.0, deductions.sec_80c)
        limit_80c = DEDUCTION_LIMITS["80c"]["max_limit"]
        eligible_80c = min(claimed_80c, limit_80c)
        disallowed_80c = max(0.0, claimed_80c - eligible_80c)
        total += eligible_80c
        details["80c"] = {
            "name": "Section 80C",
            "claimed": claimed_80c,
            "eligible": eligible_80c,
            "limit": limit_80c,
            "disallowed": disallowed_80c,
            "allowed_in_regime": True,
        }
    else:
        details["80c"] = {
            "name": "Section 80C",
            "claimed": deductions.sec_80c,
            "eligible": 0.0,
            "limit": 0.0,
            "disallowed": deductions.sec_80c,
            "allowed_in_regime": False,
        }

    # 2. Section 80D Health Insurance (Old regime only)
    if is_old:
        # Self & Family
        self_cap = 50000.0 if (deductions.is_self_senior or age >= 60) else 25000.0
        eligible_80d_self = min(max(0.0, deductions.sec_80d_self), self_cap)

        # Parents
        parents_cap = 50000.0 if deductions.is_parents_senior else 25000.0
        eligible_80d_parents = min(max(0.0, deductions.sec_80d_parents), parents_cap)

        total_80d = eligible_80d_self + eligible_80d_parents
        total += total_80d
        details["80d"] = {
            "name": "Section 80D",
            "claimed": deductions.sec_80d_self + deductions.sec_80d_parents,
            "eligible": total_80d,
            "limit": self_cap + parents_cap,
            "disallowed": max(0.0, (deductions.sec_80d_self + deductions.sec_80d_parents) - total_80d),
            "allowed_in_regime": True,
        }
    else:
        details["80d"] = {
            "name": "Section 80D",
            "claimed": deductions.sec_80d_self + deductions.sec_80d_parents,
            "eligible": 0.0,
            "limit": 0.0,
            "disallowed": deductions.sec_80d_self + deductions.sec_80d_parents,
            "allowed_in_regime": False,
        }

    # 3. Section 80CCD(1B) Additional NPS (Old regime only)
    if is_old:
        claimed_nps = max(0.0, deductions.sec_80ccd_1b)
        limit_nps = DEDUCTION_LIMITS["80ccd_1b"]["max_limit"]
        eligible_nps = min(claimed_nps, limit_nps)
        total += eligible_nps
        details["80ccd_1b"] = {
            "name": "Section 80CCD(1B)",
            "claimed": claimed_nps,
            "eligible": eligible_nps,
            "limit": limit_nps,
            "disallowed": max(0.0, claimed_nps - eligible_nps),
            "allowed_in_regime": True,
        }
    else:
        details["80ccd_1b"] = {
            "name": "Section 80CCD(1B)",
            "claimed": deductions.sec_80ccd_1b,
            "eligible": 0.0,
            "limit": 0.0,
            "disallowed": deductions.sec_80ccd_1b,
            "allowed_in_regime": False,
        }

    # 4. Section 80CCD(2) Employer NPS (BOTH Old and New regimes!)
    claimed_emp_nps = max(0.0, deductions.sec_80ccd_2)
    # Employer contribution is fully deductible up to statutory ceiling (14% of basic)
    total += claimed_emp_nps
    details["80ccd_2"] = {
        "name": "Section 80CCD(2) Employer NPS",
        "claimed": claimed_emp_nps,
        "eligible": claimed_emp_nps,
        "limit": claimed_emp_nps,
        "disallowed": 0.0,
        "allowed_in_regime": True,
    }

    # 5. Section 80TTA / 80TTB Savings Interest (Old regime only)
    if is_old and interest_income > 0:
        if age >= 60:
            limit_ttb = DEDUCTION_LIMITS["80ttb"]["max_limit"]
            eligible_interest = min(interest_income, limit_ttb)
            sec_name = "80ttb"
            display_name = "Section 80TTB (Senior Deposits Interest)"
        else:
            limit_tta = DEDUCTION_LIMITS["80tta"]["max_limit"]
            eligible_interest = min(interest_income, limit_tta)
            sec_name = "80tta"
            display_name = "Section 80TTA (Savings Bank Interest)"
        total += eligible_interest
        details[sec_name] = {
            "name": display_name,
            "claimed": interest_income,
            "eligible": eligible_interest,
            "limit": limit_ttb if age >= 60 else limit_tta,
            "disallowed": max(0.0, interest_income - eligible_interest),
            "allowed_in_regime": True,
        }

    # 6. Section 80E (Education loan interest - Old regime only)
    if is_old and deductions.sec_80e > 0:
        eligible_80e = max(0.0, deductions.sec_80e)
        total += eligible_80e
        details["80e"] = {
            "name": "Section 80E (Education Loan Interest)",
            "claimed": eligible_80e,
            "eligible": eligible_80e,
            "limit": float("inf"),
            "disallowed": 0.0,
            "allowed_in_regime": True,
        }

    # 7. Section 80G (Charitable Donations - Old regime only)
    if is_old and deductions.sec_80g > 0:
        eligible_80g = max(0.0, deductions.sec_80g)
        total += eligible_80g
        details["80g"] = {
            "name": "Section 80G (Donations)",
            "claimed": eligible_80g,
            "eligible": eligible_80g,
            "limit": float("inf"),
            "disallowed": 0.0,
            "allowed_in_regime": True,
        }

    return total, details


def compute_slab_tax(
    taxable_income: float,
    slabs: List[TaxSlab],
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Compute progressive income tax across tax slabs.
    Returns (total_slab_tax, list_of_slab_computations).
    """
    total_tax = 0.0
    breakdown: List[Dict[str, Any]] = []

    for slab in slabs:
        if taxable_income <= slab.min_income:
            continue

        if slab.max_income is not None:
            taxable_in_slab = min(taxable_income, slab.max_income) - slab.min_income
        else:
            taxable_in_slab = taxable_income - slab.min_income

        slab_tax = taxable_in_slab * slab.rate
        total_tax += slab_tax

        breakdown.append({
            "min_income": slab.min_income,
            "max_income": slab.max_income,
            "rate_pct": slab.rate * 100.0,
            "taxable_amount": taxable_in_slab,
            "tax_amount": slab_tax,
        })

    return total_tax, breakdown


def calculate_surcharge(
    taxable_income: float,
    tax_before_surcharge: float,
    surcharge_slabs: List[Any],
) -> float:
    """
    Calculate progressive surcharge with marginal relief for high-income earners.
    """
    if not surcharge_slabs or taxable_income <= surcharge_slabs[0].min_income or tax_before_surcharge <= 0:
        return 0.0

    matched_rate = 0.0
    matched_threshold = 0.0
    for slab in surcharge_slabs:
        if taxable_income > slab.min_income:
            matched_rate = slab.rate
            matched_threshold = slab.min_income

    if matched_rate <= 0.0:
        return 0.0

    raw_surcharge = tax_before_surcharge * matched_rate

    # Marginal Relief: (Tax + Surcharge) cannot exceed (Tax on threshold) + (Income above threshold)
    # Surcharge capped if income is just above the threshold
    excess_income = taxable_income - matched_threshold
    # As an approximation compliant with Indian rules, surcharge cannot cause tax to exceed threshold tax + excess income
    max_total_liability = tax_before_surcharge + excess_income
    if (tax_before_surcharge + raw_surcharge) > max_total_liability:
        surcharge = max(0.0, excess_income)
    else:
        surcharge = raw_surcharge

    return surcharge


def calculate_regime_tax(
    income: IncomeBreakdown,
    deductions: DeductionBreakdown,
    regime_rules: RegimeRules,
    financial_year: str,
    age: int = 30,
    taxes_paid: float = 0.0,
) -> TaxRegimeResult:
    """
    Compute comprehensive tax under a specific regime (Old or New).
    Follows official calculation pipeline:
    Gross Income -> Deductions -> Taxable Income (rounded 288A) -> Slab Tax ->
    Rebate & Marginal Relief 87A -> Surcharge -> Cess (4%) -> Net Tax (rounded 288B) -> TDS offset.
    """
    is_old = "old" in regime_rules.regime_name.lower()

    # 1. Standard deduction for salaried income
    eligible_std_deduction = 0.0
    if income.salary_gross > 0:
        eligible_std_deduction = min(income.salary_gross, regime_rules.standard_deduction_salary)

    # 2. HRA exemption (Old regime only, capped at salary)
    hra_exempt = 0.0
    if is_old and deductions.hra_exemption > 0 and income.salary_gross > 0:
        hra_exempt = min(deductions.hra_exemption, max(0.0, income.salary_gross - eligible_std_deduction))

    # 3. Section 24(b) Home loan interest (Old regime only, max ₹2,00,000 for self-occupied)
    sec_24b_ded = 0.0
    if is_old and deductions.sec_24b > 0:
        sec_24b_ded = min(max(0.0, deductions.sec_24b), DEDUCTION_LIMITS["24b"]["max_limit"])

    # 4. Chapter VI-A Deductions
    chapter_via, deduction_details = compute_eligible_deductions(
        deductions=deductions,
        regime_type="old" if is_old else "new",
        interest_income=income.other_sources_interest,
        age=age,
    )

    total_deductions_exemptions = eligible_std_deduction + hra_exempt + sec_24b_ded + chapter_via

    # 5. Taxable income computation (rounded to nearest 10 under Section 288A)
    raw_taxable = max(0.0, income.gross_total_income - total_deductions_exemptions)
    taxable_income = round_to_nearest_ten(raw_taxable)

    # 6. Slab selection (Age considerations for Old regime)
    if is_old:
        if age >= 80 and regime_rules.super_senior_slabs:
            slabs_to_use = regime_rules.super_senior_slabs
        elif age >= 60 and regime_rules.senior_slabs:
            slabs_to_use = regime_rules.senior_slabs
        else:
            slabs_to_use = regime_rules.slabs
    else:
        slabs_to_use = regime_rules.slabs

    # 7. Compute tax at slab rates
    slab_tax, slab_breakdown = compute_slab_tax(taxable_income, slabs_to_use)

    # 8. Section 87A Rebate & Marginal Relief
    rebate_87a = 0.0
    marginal_relief_87a = 0.0

    if taxable_income <= regime_rules.sec_87a_max_taxable_income:
        # Full rebate up to cap
        rebate_87a = min(slab_tax, regime_rules.sec_87a_rebate_limit)
        tax_after_rebate = max(0.0, slab_tax - rebate_87a)
    elif not is_old and regime_rules.has_marginal_relief_87a:
        # Marginal relief under Section 87A for New Regime (Finance Act 2024 / proviso to 87A):
        # Tax payable cannot exceed excess income over ₹7,00,000
        excess_income = taxable_income - regime_rules.sec_87a_max_taxable_income
        if slab_tax > excess_income:
            marginal_relief_87a = slab_tax - excess_income
            tax_after_rebate = excess_income
        else:
            tax_after_rebate = slab_tax
    else:
        tax_after_rebate = slab_tax

    # 9. Surcharge computation
    surcharge = calculate_surcharge(taxable_income, tax_after_rebate, regime_rules.surcharge_slabs)

    # 10. Health & Education Cess (4%)
    cess = (tax_after_rebate + surcharge) * regime_rules.cess_rate

    # 11. Total tax liability (rounded to nearest 10 under Section 288B)
    raw_total_tax = tax_after_rebate + surcharge + cess
    total_tax_liability = round_to_nearest_ten(raw_total_tax)

    # 12. Taxes paid offset
    taxes_paid_clean = max(0.0, taxes_paid)
    net_tax_payable = max(0.0, total_tax_liability - taxes_paid_clean)
    potential_refund = max(0.0, taxes_paid_clean - total_tax_liability)

    return TaxRegimeResult(
        regime_name=regime_rules.regime_name,
        financial_year=financial_year,
        gross_total_income=income.gross_total_income,
        standard_deduction=eligible_std_deduction,
        chapter_via_deductions=chapter_via,
        hra_exemption=hra_exempt,
        sec_24b_deduction=sec_24b_ded,
        total_deductions_exemptions=total_deductions_exemptions,
        taxable_income=taxable_income,
        tax_at_slab_rates=slab_tax,
        sec_87a_rebate=rebate_87a,
        marginal_relief_87a=marginal_relief_87a,
        tax_after_rebate=tax_after_rebate,
        surcharge=surcharge,
        health_education_cess=cess,
        total_tax_liability=total_tax_liability,
        tds_and_taxes_paid=taxes_paid_clean,
        net_tax_payable=net_tax_payable,
        potential_refund=potential_refund,
        deduction_details=deduction_details,
        slab_breakdown=slab_breakdown,
    )


def compare_tax_regimes(
    income: IncomeBreakdown,
    deductions: DeductionBreakdown,
    financial_year: str = "2024-25",
    age: int = 30,
    taxes_paid: float = 0.0,
) -> RegimeComparisonResult:
    """
    Perform a complete side-by-side comparison of Old and New Tax Regimes.
    Calculates exact tax difference, percentage savings, and break-even deductions.
    """
    rules = get_tax_rules(financial_year)
    old_res = calculate_regime_tax(
        income=income,
        deductions=deductions,
        regime_rules=rules["old_regime"],
        financial_year=financial_year,
        age=age,
        taxes_paid=taxes_paid,
    )
    new_res = calculate_regime_tax(
        income=income,
        deductions=deductions,
        regime_rules=rules["new_regime"],
        financial_year=financial_year,
        age=age,
        taxes_paid=taxes_paid,
    )

    diff = abs(old_res.total_tax_liability - new_res.total_tax_liability)
    higher_tax = max(old_res.total_tax_liability, new_res.total_tax_liability)
    pct_savings = (diff / higher_tax * 100.0) if higher_tax > 0 else 0.0

    if old_res.total_tax_liability < new_res.total_tax_liability:
        recommended = "Old Regime"
        summary = (
            f"The Old Regime saves ₹{diff:,.0f} ({pct_savings:.1f}% less tax) because your eligible deductions and "
            f"exemptions (₹{old_res.total_deductions_exemptions:,.0f}) substantially reduce your taxable income."
        )
    elif new_res.total_tax_liability < old_res.total_tax_liability:
        recommended = "New Regime"
        summary = (
            f"The New Regime saves ₹{diff:,.0f} ({pct_savings:.1f}% less tax) due to lower slab rates, higher standard "
            f"deduction (₹{new_res.standard_deduction:,.0f}), and full rebate up to ₹7,00,000 under Section 87A."
        )
    else:
        recommended = "Both Equal"
        summary = "Both regimes result in the identical tax liability under your current financial profile."

    # Calculate Break-Even Deductions under Old Regime
    # (How much total deduction under Old Regime is required so that Old Tax == New Tax)
    break_even = _calculate_break_even_deductions(
        income=income,
        target_tax=new_res.total_tax_liability,
        old_rules=rules["old_regime"],
        financial_year=financial_year,
        age=age,
    )

    return RegimeComparisonResult(
        financial_year=financial_year,
        old_regime=old_res,
        new_regime=new_res,
        recommended_regime=recommended,
        tax_difference=diff,
        percentage_savings=pct_savings,
        break_even_deductions=break_even,
        summary_explanation=summary,
    )


def _calculate_break_even_deductions(
    income: IncomeBreakdown,
    target_tax: float,
    old_rules: RegimeRules,
    financial_year: str,
    age: int,
) -> float:
    """
    Binary search for the required total deductions under Old Regime to match target_tax.
    """
    if target_tax <= 0:
        # If target tax is 0, old regime needs taxable income <= 5L (or 3L for basic exemption)
        return max(0.0, income.gross_total_income - 500000.0)

    low = 0.0
    high = income.gross_total_income
    best_deduction = high

    for _ in range(25):  # 25 iterations gives precision within ₹1
        mid = (low + high) / 2.0
        # Dummy test deduction breakdown
        test_ded = DeductionBreakdown(sec_80c=mid)
        res = calculate_regime_tax(
            income=income,
            deductions=test_ded,
            regime_rules=old_rules,
            financial_year=financial_year,
            age=age,
        )
        if res.total_tax_liability <= target_tax:
            best_deduction = mid
            high = mid  # try smaller deduction
        else:
            low = mid

    return round(best_deduction)
