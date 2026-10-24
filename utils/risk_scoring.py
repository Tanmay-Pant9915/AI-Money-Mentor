"""
utils/risk_scoring.py
Deterministic Risk Scoring Engine for AI Money Mentor.
Assesses user risk tolerance and financial risk capacity across 12 standardized questions.
"""
from typing import Any, Dict, List, Optional, Tuple

RISK_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "q1_life_stage",
        "factor": "Age & Investment Life Stage",
        "category": "capacity",
        "question": "Which best describes your current life and career stage?",
        "options": [
            {
                "label": "Retirement / Near-retirement",
                "description": "Relying on or soon relying on savings for living expenses",
                "score": 1,
            },
            {
                "label": "Late Career (45–55+)",
                "description": "Peak earning years with established commitments and college/wedding goals ahead",
                "score": 2,
            },
            {
                "label": "Mid Career (32–45)",
                "description": "Stable career, growing income, mortgage/family commitments",
                "score": 3,
            },
            {
                "label": "Early Career (under 32)",
                "description": "Starting out with long compounding runway ahead and minimal dependents",
                "score": 4,
            },
        ],
    },
    {
        "id": "q2_income_stability",
        "factor": "Income Stability",
        "category": "capacity",
        "question": "How steady and predictable is your primary source of monthly income?",
        "options": [
            {
                "label": "Highly unpredictable or irregular",
                "description": "Freelancing, commission-heavy, or seasonal earnings",
                "score": 1,
            },
            {
                "label": "Somewhat variable",
                "description": "Business revenue or performance bonus dependent",
                "score": 2,
            },
            {
                "label": "Mostly stable",
                "description": "Salaried employment with standard annual revisions",
                "score": 3,
            },
            {
                "label": "Very stable & secure",
                "description": "Established corporate, public sector, or resilient profession",
                "score": 4,
            },
        ],
    },
    {
        "id": "q3_emergency_fund",
        "factor": "Emergency Savings",
        "category": "capacity",
        "question": "How many months of mandatory living expenses do you currently hold in liquid cash/FDs?",
        "options": [
            {
                "label": "Less than 1 month",
                "description": "Vulnerable to immediate unexpected expenses or emergencies",
                "score": 1,
            },
            {
                "label": "1 to 3 months",
                "description": "Modest emergency buffer, still building core security",
                "score": 2,
            },
            {
                "label": "3 to 6 months",
                "description": "Adequate safety cushion meeting standard financial planning guidelines",
                "score": 3,
            },
            {
                "label": "More than 6 months",
                "description": "Robust emergency reserve providing total short-term peace of mind",
                "score": 4,
            },
        ],
    },
    {
        "id": "q4_time_horizon",
        "factor": "Investment Time Horizon",
        "category": "capacity",
        "question": "When do you expect to withdraw or use the majority of your invested capital?",
        "options": [
            {
                "label": "Within 1 to 2 years",
                "description": "Short-term need; capital cannot afford a market downturn",
                "score": 1,
            },
            {
                "label": "In 3 to 5 years",
                "description": "Medium term; moderate room to recover from volatility",
                "score": 2,
            },
            {
                "label": "In 5 to 10 years",
                "description": "Long term; ample time to ride out several market cycles",
                "score": 3,
            },
            {
                "label": "More than 10 years",
                "description": "Very long horizon; can maximize equity compounding",
                "score": 4,
            },
        ],
    },
    {
        "id": "q5_experience",
        "factor": "Investment Experience",
        "category": "tolerance",
        "question": "What is your previous experience with equity mutual funds and stock markets?",
        "options": [
            {
                "label": "Complete beginner",
                "description": "Only used savings accounts, fixed deposits, or recurring deposits",
                "score": 1,
            },
            {
                "label": "Basic familiarity",
                "description": "Invested in a few mutual funds or tax-saving ELSS schemes",
                "score": 2,
            },
            {
                "label": "Moderate experience",
                "description": "Active mutual fund investor through SIPs for over 3 years",
                "score": 3,
            },
            {
                "label": "Extensive experience",
                "description": "Familiar with market cycles, direct equities, asset allocation, and market corrections",
                "score": 4,
            },
        ],
    },
    {
        "id": "q6_market_dip_10",
        "factor": "Reaction to a 10% Market Decline",
        "category": "tolerance",
        "question": "If your portfolio dropped by 10% in a month due to market correction, how would you react?",
        "options": [
            {
                "label": "Panic and redeem everything to cash",
                "description": "Deep anxiety; unable to tolerate any visible principal decline",
                "score": 1,
            },
            {
                "label": "Stop ongoing SIPs and wait anxiously",
                "description": "Uncomfortable watching value dip, prefer halting contributions",
                "score": 2,
            },
            {
                "label": "Do nothing and let SIPs continue",
                "description": "Accept minor volatility as a normal part of equity investing",
                "score": 3,
            },
            {
                "label": "Invest extra funds to buy the dip",
                "description": "View short-term declines as attractive buying opportunities",
                "score": 4,
            },
        ],
    },
    {
        "id": "q7_market_dip_30",
        "factor": "Reaction to a 20–30% Market Crash",
        "category": "tolerance",
        "question": "During a prolonged bear market (like 2008 or March 2020) where your portfolio falls 25–30%:",
        "options": [
            {
                "label": "Liquidate remaining funds to prevent further losses",
                "description": "Cannot endure deep drawdown or uncertainty",
                "score": 1,
            },
            {
                "label": "Cut back exposure and shift into safe debt instruments",
                "description": "High stress; desire to preserve remaining capital",
                "score": 2,
            },
            {
                "label": "Hold tight without selling, waiting patiently for recovery",
                "description": "Trust the long-term historical recovery of Indian markets",
                "score": 3,
            },
            {
                "label": "Aggressively accumulate equity units at discount valuations",
                "description": "High emotional discipline and long-term focus",
                "score": 4,
            },
        ],
    },
    {
        "id": "q8_volatility_attitude",
        "factor": "Willingness to Accept Volatility",
        "category": "tolerance",
        "question": "Which return vs. volatility profile appeals to you the most?",
        "options": [
            {
                "label": "Steady 6–7% returns with zero chance of capital loss",
                "description": "Guaranteed principal preservation, like Fixed Deposits",
                "score": 1,
            },
            {
                "label": "Modest 8–10% returns with small, infrequent fluctuations",
                "description": "Conservative hybrid approach with mild equity exposure",
                "score": 2,
            },
            {
                "label": "Healthy 11–13% returns with moderate periodic ups and downs",
                "description": "Balanced asset allocation, multi-asset or flexicap funds",
                "score": 3,
            },
            {
                "label": "High 14–16%+ returns with frequent sharp swings and drawdowns",
                "description": "Pure equity growth, mid & small-cap aggressive orientation",
                "score": 4,
            },
        ],
    },
    {
        "id": "q9_loss_capacity",
        "factor": "Capacity to Tolerate Losses",
        "category": "capacity",
        "question": "If your portfolio lost 15% of its value this year, how would it impact your everyday lifestyle?",
        "options": [
            {
                "label": "Severe crisis; I might struggle to meet monthly bills or debt obligations",
                "description": "High debt or low liquidity makes any loss critical",
                "score": 1,
            },
            {
                "label": "Noticeable disruption; I would have to cut back essential or discretionary spending",
                "description": "Tight budget with minimal wiggle room",
                "score": 2,
            },
            {
                "label": "Minor inconvenience; requires postponing a luxury or vacation, but daily life unchanged",
                "description": "Adequate financial buffer",
                "score": 3,
            },
            {
                "label": "Zero impact; my daily lifestyle and emergency needs are completely insulated",
                "description": "Invested capital is truly surplus and isolated from living needs",
                "score": 4,
            },
        ],
    },
    {
        "id": "q10_liquidity_need",
        "factor": "Investment Objective & Liquidity Need",
        "category": "capacity",
        "question": "What is the primary objective of this money and how easily might you need to access it?",
        "options": [
            {
                "label": "Immediate capital preservation; money must be accessible at short notice",
                "description": "Cannot be locked up or subjected to exit loads/losses",
                "score": 1,
            },
            {
                "label": "Planned milestone in 2–3 years (e.g. house down-payment, wedding)",
                "description": "Predictable medium-term capital requirement",
                "score": 2,
            },
            {
                "label": "Long-term goal (child education, future wealth creation) over 5–10 years",
                "description": "No interim liquidity required",
                "score": 3,
            },
            {
                "label": "Ultra long-term wealth compounding / retirement (10+ years)",
                "description": "Untouchable capital dedicated purely to maximizing terminal net worth",
                "score": 4,
            },
        ],
    },
    {
        "id": "q11_loss_patience",
        "factor": "Reaction to Temporary Paper Losses",
        "category": "tolerance",
        "question": "How long are you willing to wait for a portfolio in a temporary paper loss to break even?",
        "options": [
            {
                "label": "Less than 3 months; I get restless if returns turn negative",
                "description": "High sensitivity to seeing red numbers",
                "score": 1,
            },
            {
                "label": "Up to 6–12 months",
                "description": "Tolerates short slumps but expects recovery within a year",
                "score": 2,
            },
            {
                "label": "1 to 3 years",
                "description": "Understands typical economic and equity drawdown cycles",
                "score": 3,
            },
            {
                "label": "3+ years without concern",
                "description": "Unfazed by multi-year market consolidation phases",
                "score": 4,
            },
        ],
    },
    {
        "id": "q12_preservation_vs_growth",
        "factor": "Capital Preservation vs. Growth",
        "category": "tolerance",
        "question": "When choosing between safety and growth, which statement best reflects your priority?",
        "options": [
            {
                "label": "Protecting my initial money is far more important than high returns",
                "description": "Loss aversion is paramount",
                "score": 1,
            },
            {
                "label": "I prefer safety, but want just enough growth to beat inflation (7–8%)",
                "description": "Defensive with inflation-hedging focus",
                "score": 2,
            },
            {
                "label": "I want solid growth and am willing to accept commensurate market risks",
                "description": "Balanced growth seeker",
                "score": 3,
            },
            {
                "label": "Maximizing long-term wealth is my priority; I embrace risk for outsized returns",
                "description": "Aggressive wealth compounding mindset",
                "score": 4,
            },
        ],
    },
]

# Quick lookup dictionaries
QUESTION_MAP = {q["id"]: q for q in RISK_QUESTIONS}
TOTAL_QUESTIONS = len(RISK_QUESTIONS)
MIN_RAW_SCORE = TOTAL_QUESTIONS * 1  # 12
MAX_RAW_SCORE = TOTAL_QUESTIONS * 4  # 48

# Category sub-groups
CAPACITY_Q_IDS = [q["id"] for q in RISK_QUESTIONS if q["category"] == "capacity"]
TOLERANCE_Q_IDS = [q["id"] for q in RISK_QUESTIONS if q["category"] == "tolerance"]


def normalize_score(raw_score: float, min_val: float, max_val: float) -> float:
    """Normalize a raw score into a 0.0 to 100.0 scale."""
    if max_val <= min_val:
        return 0.0
    clamped = max(min_val, min(max_val, raw_score))
    return round(((clamped - min_val) / (max_val - min_val)) * 100.0, 1)


def classify_score(score_100: float) -> str:
    """
    Standard project classification thresholds:
    0 - 33: Conservative
    34 - 66: Moderate
    67 - 100: Aggressive
    """
    rounded = round(score_100)
    if rounded <= 33:
        return "Conservative"
    elif rounded <= 66:
        return "Moderate"
    else:
        return "Aggressive"


def calculate_risk_profile(
    answers: Dict[str, int],
    financial_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Calculate deterministic risk score, capacity vs tolerance subscores,
    apply guardrails for low financial capacity, and generate educational feedback.

    Args:
        answers: Dict mapping question id -> integer score (1 to 4)
        financial_profile: Optional user financial profile dict for enriched constraints

    Returns:
        Structured result dict.
    """
    # 1. Validate answers
    valid_answers: Dict[str, int] = {}
    missing_questions: List[str] = []

    for q in RISK_QUESTIONS:
        qid = q["id"]
        val = answers.get(qid)
        if val is None or not isinstance(val, (int, float)) or int(val) not in (1, 2, 3, 4):
            missing_questions.append(qid)
        else:
            valid_answers[qid] = int(val)

    if missing_questions:
        raise ValueError(
            f"Missing or invalid answers for {len(missing_questions)} questions: "
            f"{', '.join(missing_questions)}"
        )

    # 2. Raw and category scores
    raw_total = sum(valid_answers.values())
    overall_normalized = normalize_score(raw_total, MIN_RAW_SCORE, MAX_RAW_SCORE)

    raw_capacity = sum(valid_answers[qid] for qid in CAPACITY_Q_IDS)
    min_cap = len(CAPACITY_Q_IDS) * 1
    max_cap = len(CAPACITY_Q_IDS) * 4
    capacity_normalized = normalize_score(raw_capacity, min_cap, max_cap)

    raw_tolerance = sum(valid_answers[qid] for qid in TOLERANCE_Q_IDS)
    min_tol = len(TOLERANCE_Q_IDS) * 1
    max_tol = len(TOLERANCE_Q_IDS) * 4
    tolerance_normalized = normalize_score(raw_tolerance, min_tol, max_tol)

    # Initial classification
    preliminary_classification = classify_score(overall_normalized)
    final_classification = preliminary_classification
    guardrail_applied = False
    guardrail_reasons: List[str] = []
    constraints: List[str] = []

    # 3. Guardrails for Low Financial Capacity
    # If the user has low capacity (<= 33), they cannot sustain aggressive drawdowns
    if round(capacity_normalized) <= 33 and preliminary_classification == "Aggressive":
        final_classification = "Moderate"
        guardrail_applied = True
        guardrail_reasons.append(
            "Low Financial Capacity Cap: While your psychological risk tolerance is high, "
            "your financial capacity (short investment horizon, emergency fund gap, or income constraints) "
            "cannot absorb high drawdowns. Your risk tier is prudently capped at Moderate."
        )

    # If capacity is severely constrained (<= 20) and tolerance is Moderate or higher:
    if round(capacity_normalized) <= 20 and final_classification in ("Moderate", "Aggressive"):
        final_classification = "Conservative"
        guardrail_applied = True
        guardrail_reasons.append(
            "Critical Capacity Protection: Your financial buffer and liquidity runway are very low. "
            "Protecting your base capital is essential, capping your classification at Conservative."
        )

    # 4. Identify Financial Constraints (from answers + optional linked profile)
    if valid_answers.get("q3_emergency_fund") in (1, 2):
        constraints.append("Emergency cash reserve covers less than 3 months of expenses.")
    if valid_answers.get("q4_time_horizon") == 1:
        constraints.append("Capital is needed within 1–2 years; short horizon restricts high equity exposure.")
    if valid_answers.get("q2_income_stability") == 1:
        constraints.append("Income volatility requires maintaining higher liquidity and conservative buffers.")
    if valid_answers.get("q9_loss_capacity") in (1, 2):
        constraints.append("A 15% drop would directly impact daily lifestyle or loan commitments.")

    # Check linked financial profile metrics if provided
    if financial_profile:
        metrics = financial_profile.get("metrics") or {}
        if metrics.get("is_deficit"):
            constraints.append("Current monthly expenses exceed income (running a monthly deficit).")
        if metrics.get("outstanding_debt", 0) > 0 and metrics.get("savings_liquid", 0) == 0:
            constraints.append("Outstanding debt present with zero liquid savings buffer.")

    # 5. Key Factors Summary
    factors = [
        {
            "name": "Financial Capacity",
            "score": f"{capacity_normalized}/100",
            "level": classify_score(capacity_normalized),
            "description": "Your objective ability to endure financial losses based on time horizon, income stability, and liquid buffers.",
        },
        {
            "name": "Psychological Risk Tolerance",
            "score": f"{tolerance_normalized}/100",
            "level": classify_score(tolerance_normalized),
            "description": "Your mental and emotional willingness to stay invested through sharp market downturns.",
        },
    ]

    # 6. Educational Guidance & Explanations
    guidance_map = {
        "Conservative": (
            "Your priority is capital preservation and liquidity. You should lean heavily toward fixed-income "
            "instruments (Liquid funds, Short Duration Debt, Fixed Deposits) with minimal to low equity exposure (0–20%). "
            "This shields you from market volatility while keeping your money readily accessible."
        ),
        "Moderate": (
            "You are well-suited for a balanced hybrid approach. A multi-asset or balanced advantage allocation "
            "(typically 40–60% equity, 40–60% debt & gold) lets you beat inflation over 3–5 years without suffering "
            "intolerable drawdowns during sudden market corrections."
        ),
        "Aggressive": (
            "With high financial resilience and long investment horizons (7–10+ years), you can comfortably embrace "
            "equity-oriented portfolios (70–90% equity across Large, Mid, and Flexicap funds). Short-term market swings "
            "and paper drawdowns are viewed as buying opportunities to compound wealth over decades."
        ),
    }

    explanation_map = {
        "Conservative": (
            f"You scored {overall_normalized}/100, placing you in the **Conservative** risk category. "
            "Your responses indicate that capital security, low drawdown anxiety, and predictable liquidity "
            "are more critical than aggressive capital growth."
        ),
        "Moderate": (
            f"You scored {overall_normalized}/100, placing you in the **Moderate** risk category. "
            "You have a balanced appetite: willing to endure reasonable market swings for decent long-term returns, "
            "while demanding a safety net against severe crashes."
        ),
        "Aggressive": (
            f"You scored {overall_normalized}/100, placing you in the **Aggressive** risk category. "
            "You possess both the psychological grit to ride out bear markets and the long time horizon required "
            "for equity compounding."
        ),
    }

    disclaimer = (
        "Educational Assessment Notice: This risk assessment is generated deterministically for financial educational "
        "and guidance purposes only. It does not constitute official SEBI investment advice, a portfolio recommendation, "
        "or a guarantee of returns. Actual investment allocations should be aligned with your specific tax status and goals."
    )

    return {
        "score": overall_normalized,
        "classification": final_classification,
        "preliminary_classification": preliminary_classification,
        "capacity_score": capacity_normalized,
        "tolerance_score": tolerance_normalized,
        "guardrail_applied": guardrail_applied,
        "guardrail_reasons": guardrail_reasons,
        "factors": factors,
        "constraints": constraints,
        "explanation": explanation_map[final_classification],
        "guidance": guidance_map[final_classification],
        "disclaimer": disclaimer,
    }
