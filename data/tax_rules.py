"""
data/tax_rules.py
Centralized Indian Income Tax rules and statutory thresholds by Financial Year.
Sources:
- Ministry of Finance, Government of India (Finance Act 2024 / Finance (No. 2) Act 2024)
- Income Tax Department of India (incometax.gov.in)
- Section 115BAC, Section 87A, Section 111A, Section 112A, Chapter VI-A of the Income-tax Act, 1961
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class TaxSlab:
    """Represents an income tax bracket with min, max, and rate."""
    min_income: float
    max_income: Optional[float]  # None indicates infinity / no upper ceiling
    rate: float                  # e.g., 0.05 for 5%


@dataclass(frozen=True)
class SurchargeSlab:
    """Represents a surcharge bracket."""
    min_income: float
    max_income: Optional[float]
    rate: float                  # e.g., 0.10 for 10%


@dataclass(frozen=True)
class RegimeRules:
    """Configuration rules for a specific tax regime within a Financial Year."""
    regime_name: str
    description: str
    standard_deduction_salary: float
    sec_87a_rebate_limit: float          # Max rebate amount in ₹
    sec_87a_max_taxable_income: float    # Income threshold for rebate in ₹
    has_marginal_relief_87a: bool        # True for new regime where tax <= excess over threshold
    cess_rate: float                     # Health & Education Cess, typically 0.04 (4%)
    slabs: List[TaxSlab]
    senior_slabs: Optional[List[TaxSlab]] = None       # Age 60 to 79 (Old regime)
    super_senior_slabs: Optional[List[TaxSlab]] = None # Age 80+ (Old regime)
    surcharge_slabs: List[SurchargeSlab] = field(default_factory=list)
    allowed_deductions: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CapitalGainsRules:
    """Statutory capital gains tax parameters for mutual funds & equities."""
    equity_stcg_rate: float               # Sec 111A, e.g. 0.20 (20%)
    equity_stcg_holding_months: int       # 12 months
    equity_ltcg_rate: float               # Sec 112A, e.g. 0.125 (12.5%)
    equity_ltcg_exemption: float          # ₹1,25,000 post July 2024
    debt_fund_tax_mode: str               # "SLAB" (taxed at regular slab rates under Sec 50AA)
    other_funds_stcg_holding_months: int  # 24 months
    other_funds_ltcg_rate: float          # 12.5% without indexation
    cess_rate: float                      # 0.04 (4%)
    effective_from_note: str


# ==============================================================================
# FINANCIAL YEAR 2024-25 (Assessment Year 2025-26)
# Updated as per Finance (No. 2) Act, 2024
# ==============================================================================

FY_2024_25_NEW_REGIME = RegimeRules(
    regime_name="New Regime (Section 115BAC)",
    description="Default regime under Section 115BAC(1A) with revised slabs under Finance Act 2024.",
    standard_deduction_salary=75000.0,  # Increased from ₹50,000 to ₹75,000 in Budget 2024
    sec_87a_rebate_limit=25000.0,
    sec_87a_max_taxable_income=700000.0,
    has_marginal_relief_87a=True,
    cess_rate=0.04,
    slabs=[
        TaxSlab(min_income=0.0, max_income=300000.0, rate=0.0),
        TaxSlab(min_income=300000.0, max_income=700000.0, rate=0.05),
        TaxSlab(min_income=700000.0, max_income=1000000.0, rate=0.10),
        TaxSlab(min_income=1000000.0, max_income=1200000.0, rate=0.15),
        TaxSlab(min_income=1200000.0, max_income=1500000.0, rate=0.20),
        TaxSlab(min_income=1500000.0, max_income=None, rate=0.30),
    ],
    surcharge_slabs=[
        SurchargeSlab(min_income=5000000.0, max_income=10000000.0, rate=0.10),
        SurchargeSlab(min_income=10000000.0, max_income=20000000.0, rate=0.15),
        SurchargeSlab(min_income=20000000.0, max_income=None, rate=0.25),  # Capped at 25% in new regime
    ],
    allowed_deductions=[
        "standard_deduction",
        "80ccd_2",  # Employer NPS contribution (up to 14% of basic salary)
    ]
)

FY_2024_25_OLD_REGIME = RegimeRules(
    regime_name="Old Regime",
    description="Traditional regime retaining all Chapter VI-A deductions and exemptions.",
    standard_deduction_salary=50000.0,
    sec_87a_rebate_limit=12500.0,
    sec_87a_max_taxable_income=500000.0,
    has_marginal_relief_87a=False,
    cess_rate=0.04,
    slabs=[
        TaxSlab(min_income=0.0, max_income=250000.0, rate=0.0),
        TaxSlab(min_income=250000.0, max_income=500000.0, rate=0.05),
        TaxSlab(min_income=500000.0, max_income=1000000.0, rate=0.20),
        TaxSlab(min_income=1000000.0, max_income=None, rate=0.30),
    ],
    senior_slabs=[  # Age 60 to 79
        TaxSlab(min_income=0.0, max_income=300000.0, rate=0.0),
        TaxSlab(min_income=300000.0, max_income=500000.0, rate=0.05),
        TaxSlab(min_income=500000.0, max_income=1000000.0, rate=0.20),
        TaxSlab(min_income=1000000.0, max_income=None, rate=0.30),
    ],
    super_senior_slabs=[  # Age 80+
        TaxSlab(min_income=0.0, max_income=500000.0, rate=0.0),
        TaxSlab(min_income=500000.0, max_income=1000000.0, rate=0.20),
        TaxSlab(min_income=1000000.0, max_income=None, rate=0.30),
    ],
    surcharge_slabs=[
        SurchargeSlab(min_income=5000000.0, max_income=10000000.0, rate=0.10),
        SurchargeSlab(min_income=10000000.0, max_income=20000000.0, rate=0.15),
        SurchargeSlab(min_income=20000000.0, max_income=50000000.0, rate=0.25),
        SurchargeSlab(min_income=50000000.0, max_income=None, rate=0.37),
    ],
    allowed_deductions=[
        "standard_deduction",
        "80c",
        "80d",
        "80ccd_1b",
        "80ccd_2",
        "24b",
        "80tta",
        "80ttb",
        "80e",
        "80g",
        "hra_exemption",
    ]
)

FY_2024_25_CAPITAL_GAINS = CapitalGainsRules(
    equity_stcg_rate=0.20,             # Revised from 15% to 20% w.e.f. 23 July 2024
    equity_stcg_holding_months=12,
    equity_ltcg_rate=0.125,            # Revised from 10% to 12.5% w.e.f. 23 July 2024
    equity_ltcg_exemption=125000.0,    # Increased from ₹1,00,000 to ₹1,25,000
    debt_fund_tax_mode="SLAB",
    other_funds_stcg_holding_months=24,
    other_funds_ltcg_rate=0.125,
    cess_rate=0.04,
    effective_from_note="Finance (No. 2) Act, 2024 rules effective from 23 July 2024."
)


# ==============================================================================
# FINANCIAL YEAR 2025-26 (Assessment Year 2026-27)
# Same baseline structure as Finance Act 2024 ongoing provisions
# ==============================================================================

FY_2025_26_NEW_REGIME = RegimeRules(
    regime_name="New Regime (Section 115BAC)",
    description="Default regime under Section 115BAC(1A) for FY 2025-26.",
    standard_deduction_salary=75000.0,
    sec_87a_rebate_limit=25000.0,
    sec_87a_max_taxable_income=700000.0,
    has_marginal_relief_87a=True,
    cess_rate=0.04,
    slabs=[
        TaxSlab(min_income=0.0, max_income=300000.0, rate=0.0),
        TaxSlab(min_income=300000.0, max_income=700000.0, rate=0.05),
        TaxSlab(min_income=700000.0, max_income=1000000.0, rate=0.10),
        TaxSlab(min_income=1000000.0, max_income=1200000.0, rate=0.15),
        TaxSlab(min_income=1200000.0, max_income=1500000.0, rate=0.20),
        TaxSlab(min_income=1500000.0, max_income=None, rate=0.30),
    ],
    surcharge_slabs=[
        SurchargeSlab(min_income=5000000.0, max_income=10000000.0, rate=0.10),
        SurchargeSlab(min_income=10000000.0, max_income=20000000.0, rate=0.15),
        SurchargeSlab(min_income=20000000.0, max_income=None, rate=0.25),
    ],
    allowed_deductions=[
        "standard_deduction",
        "80ccd_2",
    ]
)

FY_2025_26_OLD_REGIME = RegimeRules(
    regime_name="Old Regime",
    description="Traditional regime for FY 2025-26 with Chapter VI-A deductions.",
    standard_deduction_salary=50000.0,
    sec_87a_rebate_limit=12500.0,
    sec_87a_max_taxable_income=500000.0,
    has_marginal_relief_87a=False,
    cess_rate=0.04,
    slabs=[
        TaxSlab(min_income=0.0, max_income=250000.0, rate=0.0),
        TaxSlab(min_income=250000.0, max_income=500000.0, rate=0.05),
        TaxSlab(min_income=500000.0, max_income=1000000.0, rate=0.20),
        TaxSlab(min_income=1000000.0, max_income=None, rate=0.30),
    ],
    senior_slabs=[
        TaxSlab(min_income=0.0, max_income=300000.0, rate=0.0),
        TaxSlab(min_income=300000.0, max_income=500000.0, rate=0.05),
        TaxSlab(min_income=500000.0, max_income=1000000.0, rate=0.20),
        TaxSlab(min_income=1000000.0, max_income=None, rate=0.30),
    ],
    super_senior_slabs=[
        TaxSlab(min_income=0.0, max_income=500000.0, rate=0.0),
        TaxSlab(min_income=500000.0, max_income=1000000.0, rate=0.20),
        TaxSlab(min_income=1000000.0, max_income=None, rate=0.30),
    ],
    surcharge_slabs=[
        SurchargeSlab(min_income=5000000.0, max_income=10000000.0, rate=0.10),
        SurchargeSlab(min_income=10000000.0, max_income=20000000.0, rate=0.15),
        SurchargeSlab(min_income=20000000.0, max_income=50000000.0, rate=0.25),
        SurchargeSlab(min_income=50000000.0, max_income=None, rate=0.37),
    ],
    allowed_deductions=[
        "standard_deduction",
        "80c",
        "80d",
        "80ccd_1b",
        "80ccd_2",
        "24b",
        "80tta",
        "80ttb",
        "80e",
        "80g",
        "hra_exemption",
    ]
)

FY_2025_26_CAPITAL_GAINS = CapitalGainsRules(
    equity_stcg_rate=0.20,
    equity_stcg_holding_months=12,
    equity_ltcg_rate=0.125,
    equity_ltcg_exemption=125000.0,
    debt_fund_tax_mode="SLAB",
    other_funds_stcg_holding_months=24,
    other_funds_ltcg_rate=0.125,
    cess_rate=0.04,
    effective_from_note="Presumed continuation of Finance (No. 2) Act, 2024 provisions."
)


# Statutory Deduction Limits
DEDUCTION_LIMITS: Dict[str, Dict[str, Any]] = {
    "80c": {
        "name": "Section 80C (PPF, EPF, ELSS, Life Insurance, Home Loan Principal)",
        "max_limit": 150000.0,
        "eligible_regimes": ["old"],
        "description": "Aggregate cap of ₹1,50,000 across EPF, PPF, ELSS, NPS (1), SSY, NSC, life insurance premiums, and home loan principal.",
        "section_ref": "Section 80C / 80CCE, Income-tax Act, 1961"
    },
    "80d": {
        "name": "Section 80D (Health Insurance Premium & Health Check-up)",
        "self_family_max": 25000.0,
        "self_family_senior_max": 50000.0,
        "parents_max": 25000.0,
        "parents_senior_max": 50000.0,
        "preventive_checkup_sublimit": 5000.0,
        "eligible_regimes": ["old"],
        "description": "Deduction for medical insurance premium paid for self, spouse, children, and parents. Maximum up to ₹1,00,000 if both are senior citizens.",
        "section_ref": "Section 80D, Income-tax Act, 1961"
    },
    "80ccd_1b": {
        "name": "Section 80CCD(1B) (Additional NPS Contribution)",
        "max_limit": 50000.0,
        "eligible_regimes": ["old"],
        "description": "Exclusive deduction for voluntary contributions to National Pension System (NPS Tier 1), over and above the 80C limit.",
        "section_ref": "Section 80CCD(1B), Income-tax Act, 1961"
    },
    "80ccd_2": {
        "name": "Section 80CCD(2) (Employer NPS Contribution)",
        "max_limit_pct_govt": 0.14,
        "max_limit_pct_private": 0.14,  # Budget 2024 harmonized private employer deduction to 14% under new regime
        "eligible_regimes": ["old", "new"],
        "description": "Employer contribution to employee's NPS Tier 1. Permitted under BOTH Old and New regimes.",
        "section_ref": "Section 80CCD(2), Income-tax Act, 1961"
    },
    "24b": {
        "name": "Section 24(b) (Home Loan Interest - Self Occupied)",
        "max_limit": 200000.0,
        "eligible_regimes": ["old"],
        "description": "Deduction for interest paid on housing loan for self-occupied house property up to ₹2,00,000.",
        "section_ref": "Section 24(b), Income-tax Act, 1961"
    },
    "80tta": {
        "name": "Section 80TTA (Savings Account Interest - Non Seniors)",
        "max_limit": 10000.0,
        "eligible_regimes": ["old"],
        "description": "Interest earned on savings bank accounts up to ₹10,000 for individuals below 60 years.",
        "section_ref": "Section 80TTA, Income-tax Act, 1961"
    },
    "80ttb": {
        "name": "Section 80TTB (Deposits Interest - Senior Citizens)",
        "max_limit": 50000.0,
        "eligible_regimes": ["old"],
        "description": "Interest on all deposits (savings, FD, RD) up to ₹50,000 for senior citizens (age 60+).",
        "section_ref": "Section 80TTB, Income-tax Act, 1961"
    },
    "80e": {
        "name": "Section 80E (Higher Education Loan Interest)",
        "max_limit": float("inf"),
        "eligible_regimes": ["old"],
        "description": "Full interest paid on loan taken for higher education of self, spouse, or children (no upper ceiling, max 8 years).",
        "section_ref": "Section 80E, Income-tax Act, 1961"
    },
    "80g": {
        "name": "Section 80G (Charitable Donations)",
        "max_limit": float("inf"),
        "eligible_regimes": ["old"],
        "description": "Donations to eligible relief funds and registered charitable institutions (50% or 100% deduction subject to qualifying limits).",
        "section_ref": "Section 80G, Income-tax Act, 1961"
    },
}

SUPPORTED_FINANCIAL_YEARS: Dict[str, Dict[str, Any]] = {
    "2024-25": {
        "label": "FY 2024–25 (AY 2025–26)",
        "old_regime": FY_2024_25_OLD_REGIME,
        "new_regime": FY_2024_25_NEW_REGIME,
        "capital_gains": FY_2024_25_CAPITAL_GAINS,
        "version": "1.0-FA2024",
        "is_default": True,
    },
    "2025-26": {
        "label": "FY 2025–26 (AY 2026–27)",
        "old_regime": FY_2025_26_OLD_REGIME,
        "new_regime": FY_2025_26_NEW_REGIME,
        "capital_gains": FY_2025_26_CAPITAL_GAINS,
        "version": "1.0-FA2025-BASE",
        "is_default": False,
    },
}


def get_tax_rules(financial_year: str = "2024-25") -> Dict[str, Any]:
    """
    Retrieve official tax rules for a specified financial year.
    Raises ValueError if financial_year is unsupported.
    """
    if financial_year not in SUPPORTED_FINANCIAL_YEARS:
        supported = ", ".join(SUPPORTED_FINANCIAL_YEARS.keys())
        raise ValueError(
            f"Unsupported financial year '{financial_year}'. Supported years: {supported}"
        )
    return SUPPORTED_FINANCIAL_YEARS[financial_year]
