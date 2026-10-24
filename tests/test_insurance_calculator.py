"""
tests/test_insurance_calculator.py
Unit tests for deterministic insurance calculations:
- Health coverage gap calculation
- Existing coverage meeting or exceeding target
- Missing / zero health coverage data
- Employer coverage kept distinct from personal coverage
- Life insurance needs calculation (needs-based / human life value)
- Existing insurance reducing additional need
- Existing eligible assets reducing additional need
- No dependents and no stated obligations edge case
- Negative calculated coverage gap clamped to 0
- Missing financial obligations handling
- Avoiding double-counting of resources and obligations
- Accident / disability assessment with incomplete or zero data
"""
import pytest

from utils.insurance_calculator import (
    calculate_health_insurance_gap,
    calculate_life_insurance_needs,
    evaluate_personal_accident_coverage,
)


def test_health_coverage_gap():
    # Target 10 Lakhs, personal 3 Lakhs, employer 2 Lakhs
    # Total = 5 Lakhs -> Gap = 5 Lakhs
    res = calculate_health_insurance_gap(
        personal_coverage=300000.0,
        employer_coverage=200000.0,
        target_coverage=1000000.0,
    )
    assert res["total_current_coverage"] == 500000.0
    assert res["total_coverage_gap"] == 500000.0
    assert res["personal_coverage_gap"] == 700000.0
    assert res["is_adequate_total"] is False
    assert res["status"] == "Under-Insured"


def test_health_coverage_meeting_or_exceeding_target():
    # Target 10 Lakhs, personal 15 Lakhs
    res = calculate_health_insurance_gap(
        personal_coverage=1500000.0,
        employer_coverage=0.0,
        target_coverage=1000000.0,
    )
    assert res["total_coverage_gap"] == 0.0
    assert res["is_adequate_total"] is True
    assert res["is_adequate_personal"] is True
    assert res["status"] == "Adequately Covered"


def test_health_missing_or_zero_coverage():
    res = calculate_health_insurance_gap(
        personal_coverage=0.0,
        employer_coverage=0.0,
        target_coverage=500000.0,
    )
    assert res["total_current_coverage"] == 0.0
    assert res["total_coverage_gap"] == 500000.0
    assert res["status"] == "No Coverage"


def test_health_employer_coverage_distinct_from_personal():
    # Target 10 Lakhs, 0 personal, 10 Lakhs employer
    res = calculate_health_insurance_gap(
        personal_coverage=0.0,
        employer_coverage=1000000.0,
        target_coverage=1000000.0,
    )
    # Total meets target, but personal cover is 0
    assert res["total_coverage_gap"] == 0.0
    assert res["personal_coverage_gap"] == 1000000.0
    assert res["is_adequate_total"] is True
    assert res["is_adequate_personal"] is False
    assert res["status"] == "Employer Only"
    assert "contingent on employment" in res["summary"]


def test_life_insurance_needs_calculation():
    # Annual income 12,00,000, 2 dependents, 10x multiplier = 1,20,00,000 (1.2 Crore)
    # Liabilities 30,00,000, Goals 20,00,000 -> Gross Need = 1,70,00,000
    # Assets 20,00,000, Existing cover 50,00,000 -> Resources = 70,00,000
    # Additional Need = 1,70,00,000 - 70,00,000 = 1,00,00,000 (1 Crore)
    res = calculate_life_insurance_needs(
        annual_income=1200000.0,
        number_of_dependents=2,
        income_replacement_years=10.0,
        outstanding_liabilities=3000000.0,
        future_family_obligations=0.0,
        specified_goals=2000000.0,
        existing_eligible_assets=2000000.0,
        existing_life_insurance=5000000.0,
    )
    assert res["gross_protection_need"] == 17000000.0
    assert res["total_existing_resources"] == 7000000.0
    assert res["net_additional_need"] == 10000000.0
    assert res["is_adequately_covered"] is False


def test_life_insurance_resources_reducing_need():
    # Need before resources: 1 Crore
    # With 0 existing resources -> Gap = 1 Crore
    res1 = calculate_life_insurance_needs(
        annual_income=1000000.0,
        number_of_dependents=1,
        income_replacement_years=10.0,
        existing_eligible_assets=0.0,
        existing_life_insurance=0.0,
    )
    assert res1["net_additional_need"] == 10000000.0

    # With 40 Lakhs life cover and 30 Lakhs assets -> Gap = 30 Lakhs
    res2 = calculate_life_insurance_needs(
        annual_income=1000000.0,
        number_of_dependents=1,
        income_replacement_years=10.0,
        existing_eligible_assets=3000000.0,
        existing_life_insurance=4000000.0,
    )
    assert res2["net_additional_need"] == 3000000.0


def test_life_insurance_no_dependents_and_no_obligations():
    # Single person, 0 dependents, 0 debts, 0 obligations
    # Must NOT recommend a massive policy!
    res = calculate_life_insurance_needs(
        annual_income=1500000.0,
        number_of_dependents=0,
        outstanding_liabilities=0.0,
        future_family_obligations=0.0,
        specified_goals=0.0,
    )
    assert res["has_dependents"] is False
    assert res["gross_protection_need"] == 0.0
    assert res["net_additional_need"] == 0.0
    assert res["is_adequately_covered"] is True
    assert res["status"] == "No Life Cover Needed"


def test_life_insurance_negative_calculated_gap():
    # Resources (2 Crore) exceed Gross Need (1 Crore)
    # Gap must strictly be 0.0 (never negative)
    res = calculate_life_insurance_needs(
        annual_income=1000000.0,
        number_of_dependents=1,
        income_replacement_years=10.0,
        existing_eligible_assets=10000000.0,
        existing_life_insurance=10000000.0,
    )
    assert res["net_additional_need"] == 0.0
    assert res["is_adequately_covered"] is True
    assert res["status"] == "Adequately Protected"


def test_life_insurance_missing_obligations():
    # Handles 0 or None for optional inputs without failure
    res = calculate_life_insurance_needs(
        annual_income=800000.0,
        number_of_dependents=1,
        income_replacement_years=5.0,
        outstanding_liabilities=None,
        future_family_obligations=None,
        specified_goals=None,
    )
    assert res["gross_protection_need"] == 4000000.0  # 800k * 5
    assert res["net_additional_need"] == 4000000.0


def test_accident_disability_assessment():
    # User without accident insurance
    res_no = evaluate_personal_accident_coverage(annual_income=1000000.0, has_accident_cover=False)
    assert res_no["has_accident_cover"] is False
    assert res_no["status"] == "No Accident/Disability Cover"
    assert len(res_no["checklist"]) >= 4

    # User with accident insurance
    res_yes = evaluate_personal_accident_coverage(
        annual_income=1000000.0,
        has_accident_cover=True,
        current_sum_insured=5000000.0,
    )
    assert res_yes["has_accident_cover"] is True
    assert res_yes["current_sum_insured"] == 5000000.0
    assert res_yes["status"] == "Protected"
