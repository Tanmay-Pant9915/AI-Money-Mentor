"""
tests/test_financial_mentor_router.py
Unit tests for question classification and intent routing in AI Financial Mentor.
"""
from services.financial_mentor_router import classify_user_intent


def test_classify_health_score_queries():
    assert classify_user_intent("How healthy is my financial situation?")[0] == "HEALTH_SCORE"
    assert classify_user_intent("What is affecting my Money Health Score?")[0] == "HEALTH_SCORE"
    assert classify_user_intent("Give me my health rating breakdown")[0] == "HEALTH_SCORE"


def test_classify_budget_and_savings_queries():
    assert classify_user_intent("Where is most of my monthly income going?")[0] == "BUDGET_SAVINGS"
    assert classify_user_intent("How much should I save each month?")[0] == "BUDGET_SAVINGS"
    assert classify_user_intent("Review my 50/30/20 spending budget")[0] == "BUDGET_SAVINGS"


def test_classify_emergency_fund_queries():
    assert classify_user_intent("How long will it take to reach my emergency fund target?")[0] == "EMERGENCY_FUND"
    assert classify_user_intent("Is my liquid savings runway sufficient?")[0] == "EMERGENCY_FUND"


def test_classify_tax_queries():
    assert classify_user_intent("Which tax regime has lower tax liability?")[0] == "TAX_PLANNING"
    assert classify_user_intent("How can I save tax under Section 80C and 80D?")[0] == "TAX_PLANNING"


def test_classify_retirement_queries():
    assert classify_user_intent("What is my estimated FIRE corpus?")[0] == "RETIREMENT_FIRE"
    assert classify_user_intent("How much do I need to invest monthly for retirement?")[0] == "RETIREMENT_FIRE"


def test_classify_portfolio_queries():
    assert classify_user_intent("Why does my portfolio have overlapping mutual funds?")[0] == "PORTFOLIO_CAS"
    assert classify_user_intent("What does my portfolio's XIRR mean?")[0] == "PORTFOLIO_CAS"


def test_classify_what_if_queries():
    assert classify_user_intent("What if I save ₹5,000 more each month?")[0] == "WHAT_IF_SCENARIO"
    assert classify_user_intent("What if I retire at age 52?")[0] == "WHAT_IF_SCENARIO"
    assert classify_user_intent("Suppose I increase my emergency target to 9 months")[0] == "WHAT_IF_SCENARIO"


def test_classify_general_education_queries():
    assert classify_user_intent("What is XIRR?")[0] == "GENERAL_EDUCATION"
    assert classify_user_intent("Explain how inflation affects savings")[0] == "GENERAL_EDUCATION"
    assert classify_user_intent("Define compound interest")[0] == "GENERAL_EDUCATION"
