"""
tests/test_tax_rules.py
Unit tests for tax rules configuration and financial year loader.
"""
import pytest
from data.tax_rules import (
    SUPPORTED_FINANCIAL_YEARS,
    DEDUCTION_LIMITS,
    get_tax_rules,
    TaxSlab,
)


def test_supported_financial_years_exist():
    assert "2024-25" in SUPPORTED_FINANCIAL_YEARS
    assert "2025-26" in SUPPORTED_FINANCIAL_YEARS


def test_get_tax_rules_valid():
    rules_24 = get_tax_rules("2024-25")
    assert rules_24["label"] == "FY 2024–25 (AY 2025–26)"
    assert rules_24["old_regime"].standard_deduction_salary == 50000.0
    assert rules_24["new_regime"].standard_deduction_salary == 75000.0
    assert rules_24["new_regime"].sec_87a_max_taxable_income == 700000.0
    assert rules_24["new_regime"].has_marginal_relief_87a is True


def test_get_tax_rules_invalid():
    with pytest.raises(ValueError, match="Unsupported financial year"):
        get_tax_rules("1999-00")


def test_slabs_monotonic_and_continuous():
    for fy, config in SUPPORTED_FINANCIAL_YEARS.items():
        for regime in [config["old_regime"], config["new_regime"]]:
            slabs = regime.slabs
            assert len(slabs) > 0
            prev_max = 0.0
            for i, slab in enumerate(slabs):
                assert slab.min_income == prev_max
                if slab.max_income is not None:
                    assert slab.max_income > slab.min_income
                    prev_max = slab.max_income
                else:
                    # Last slab must have max_income None
                    assert i == len(slabs) - 1


def test_deduction_limits_integrity():
    assert "80c" in DEDUCTION_LIMITS
    assert DEDUCTION_LIMITS["80c"]["max_limit"] == 150000.0
    assert "80ccd_1b" in DEDUCTION_LIMITS
    assert DEDUCTION_LIMITS["80ccd_1b"]["max_limit"] == 50000.0
    assert "24b" in DEDUCTION_LIMITS
    assert DEDUCTION_LIMITS["24b"]["max_limit"] == 200000.0
