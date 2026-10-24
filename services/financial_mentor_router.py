"""
services/financial_mentor_router.py
Lightweight deterministic intent router for AI Financial Mentor.
Classifies user queries into specific financial domains to select minimal, relevant context.
"""
import re
from typing import Dict, Tuple


INTENT_PATTERNS = [
    (
        "WHAT_IF_SCENARIO",
        r"\b(what\s+if|suppose\s+i|if\s+i\s+(save|invest|spend|retire|cut)|simulate|scenario)\b",
    ),
    (
        "HEALTH_SCORE",
        r"\b(healthy|health\s+score|money\s+health|financial\s+health|health\s+rating|score\s+breakdown)\b",
    ),
    (
        "EMERGENCY_FUND",
        r"\b(emergency\s+(fund|savings|reserve|runway|buffer)|safety\s+net|liquid\s+(savings\s+)?runway|liquid\s+savings|rainy\s+day)\b",
    ),
    (
        "TAX_PLANNING",
        r"\b(tax|income\s+tax|regime|old\s+vs\s+new|80c|80d|nps\s+tax|hra|tds|capital\s+gain|advance\s+tax)\b",
    ),
    (
        "RETIREMENT_FIRE",
        r"\b(retire|retirement|fire\s+(age|corpus|number)|pension|early\s+retirement|years\s+to\s+fire)\b",
    ),
    (
        "INSURANCE_PROTECTION",
        r"\b(insurance|health\s+(cover|insurance|policy)|life\s+(cover|insurance)|term\s+insurance|disability|accident\s+cover)\b",
    ),
    (
        "GOALS_INVESTMENT",
        r"\b(goal|goals|target\s+date|sip\s+for|house\s+goal|child\s+education|wedding\s+goal)\b",
    ),
    (
        "PORTFOLIO_CAS",
        r"\b(xirr|portfolio|mutual\s+fund|overlap|expense\s+ratio|cams|fund\s+performance|holdings)\b",
    ),
    (
        "BUDGET_SAVINGS",
        r"\b(budget|expenses|spending|where\s+.*(money|income)\s+(go|going)|surplus|deficit|50/30/20|save\s+each\s+month|savings\s+rate|monthly\s+savings)\b",
    ),
]


def classify_user_intent(query: str) -> Tuple[str, str]:
    """
    Classify user query into a primary intent and return (intent_code, friendly_category_name).
    """
    if not query or not query.strip():
        return ("GENERAL_SUMMARY", "General Financial Overview")

    q_lower = query.lower().strip()

    # If it's a general definition question without personal pronouns (e.g., "What is XIRR?"), prioritize education
    if re.search(r"^(what\s+is|what\s+does|define|explain|meaning\s+of)\b", q_lower) and not re.search(r"\b(my|i|me|we|our)\b", q_lower):
        return ("GENERAL_EDUCATION", "Financial Education & Concepts")

    # Match against prioritized patterns
    for intent_code, pattern in INTENT_PATTERNS:
        if re.search(pattern, q_lower):
            category_names = {
                "WHAT_IF_SCENARIO": "What-If Scenario Simulation",
                "HEALTH_SCORE": "Money Health Score Analysis",
                "EMERGENCY_FUND": "Emergency Fund & Liquid Runway",
                "TAX_PLANNING": "Tax Optimization & Regimes",
                "RETIREMENT_FIRE": "Retirement & FIRE Planning",
                "INSURANCE_PROTECTION": "Insurance & Risk Protection",
                "GOALS_INVESTMENT": "Goal-Based Investment Planning",
                "PORTFOLIO_CAS": "Mutual Fund Portfolio & CAS",
                "BUDGET_SAVINGS": "Budgeting, Spending & Cash Flow",
            }
            return (intent_code, category_names.get(intent_code, "Financial Planning"))

    # Fallback to general educational/summary
    if any(k in q_lower for k in ("what is", "how does", "explain", "define", "meaning of")):
        return ("GENERAL_EDUCATION", "Financial Education & Concepts")

    return ("GENERAL_SUMMARY", "Holistic Financial Overview")
