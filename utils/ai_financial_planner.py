"""
utils/ai_financial_planner.py
AI-generated financial plan explanations and educational narrative.
Grounds all narrative strictly on deterministic calculation outputs from Python.
Falls back gracefully if the Groq API key is missing or encounters network errors.
"""
import json
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from groq import Groq
import streamlit as st

load_dotenv()

try:
    from utils.ai_summary import client as _shared_client
except Exception:
    _shared_client = None

_api_key = os.getenv("GROQ_API_KEY")
if not _api_key:
    try:
        _api_key = st.secrets.get("GROQ_API_KEY")
    except Exception:
        _api_key = None

_client = _shared_client if _shared_client is not None else (Groq(api_key=_api_key) if _api_key else None)


_SYSTEM_PROMPT = """
You are an expert, empathetic fee-only financial planner specializing in Indian personal finance and budgeting.
You are provided with a verified JSON snapshot containing the user's deterministic financial summary, recommended budget allocations, goal progress, and prioritized actions.

STRICT GROUNDING & COMPLIANCE RULES:
1. Base every statement and figure SOLELY on the numbers provided in the plan JSON.
2. NEVER invent or recalculate income, expenses, debts, emergency funds, or goal amounts.
3. NEVER recommend specific stock tickers, individual mutual fund schemes, crypto, or third-party products.
4. Keep all currency in Indian Rupees (₹) using standard Indian notation (₹X,XXX or ₹X.X Lakh).
5. Do NOT promise guaranteed returns or guarantee financial success.
6. Acknowledge essential living expenses and debt repayments as non-negotiable obligations.
7. Total word count must not exceed 400 words.
8. Follow EXACTLY the four markdown headings below:

### 📌 Executive Financial Summary
[2-3 sentences summarizing current cash flow sustainability, savings rate, and overall financial balance]

### 💡 Budget Adjustments & Rationale
[Explain why discretionary spending or surplus was adjusted, highlighting specific categories and monthly differences]

### 🛡️ Debt & Emergency Reserves Roadmap
[Explain the recommended runway target and debt strategy based on the DTI and emergency fund coverage in the JSON]

### 🎯 Goal Strategy & Next Steps
[Explain how surplus is allocated across goals or trade-offs needed, concluding with 2-3 immediate practical habits]
""".strip()


_USER_PROMPT_TEMPLATE = """
Here is the validated financial plan and budget dataset:

```json
{plan_json}
```

Please generate the four-section educational financial plan explanation exactly as instructed.
""".strip()


def generate_plan_explanation(
    summary: Dict[str, Any],
    budget: Dict[str, Any],
    goals_data: Optional[Dict[str, Any]] = None,
    actions: Optional[list] = None,
) -> str:
    """
    Generate an AI-powered explanation of the deterministic financial plan.
    Returns markdown text or a structured educational fallback if the AI API is unavailable.
    """
    if _client is None:
        return _generate_deterministic_fallback(summary, budget, goals_data, actions)

    # Build clean serializable payload
    payload = {
        "monthly_income": summary.get("monthly_income"),
        "total_monthly_outflows": summary.get("total_monthly_outflows"),
        "monthly_surplus": summary.get("monthly_surplus"),
        "is_deficit": summary.get("is_deficit"),
        "savings_rate_pct": summary.get("savings_rate"),
        "debt_to_income_pct": summary.get("debt_to_income"),
        "recommended_categories": budget.get("recommended_categories"),
        "emergency_allocation": budget.get("emergency_allocation"),
        "goals_allocation": {
            "total_required": (goals_data or {}).get("total_required_monthly"),
            "total_allocated": (goals_data or {}).get("total_allocated_monthly"),
            "shortfall": (goals_data or {}).get("surplus_shortfall"),
            "is_fully_funded": (goals_data or {}).get("is_fully_funded"),
        },
        "budget_notes": budget.get("notes"),
        "top_priorities": [
            {"category": a.get("category"), "title": a.get("title"), "priority": a.get("priority")}
            for a in (actions or [])[:3]
        ],
    }

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        plan_json=json.dumps(payload, indent=2, default=str)
    )

    try:
        response = _client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=800,
        )
        return response.choices[0].message.content

    except Exception as exc:
        err_msg = str(exc)
        fallback = _generate_deterministic_fallback(summary, budget, goals_data, actions)
        return (
            f"ℹ️ *Note: AI service is currently unavailable ({type(exc).__name__}). "
            f"Displaying verified deterministic plan explanation below.*\n\n{fallback}"
        )


def _generate_deterministic_fallback(
    summary: Dict[str, Any],
    budget: Dict[str, Any],
    goals_data: Optional[Dict[str, Any]] = None,
    actions: Optional[list] = None,
) -> str:
    """
    High-quality deterministic fallback narrative generated entirely without LLM APIs.
    Ensures 100% utility when offline or when GROQ_API_KEY is not configured.
    """
    income = summary.get("monthly_income", 0.0)
    surplus = summary.get("monthly_surplus", 0.0)
    is_deficit = summary.get("is_deficit", False)
    savings_rate = summary.get("savings_rate", 0.0)
    dti = summary.get("debt_to_income", 0.0)

    emg = budget.get("emergency_allocation", {})
    coverage = emg.get("coverage_months", 0.0)
    emg_monthly = emg.get("recommended_monthly", 0.0)

    # Section 1
    if is_deficit:
        exec_summary = (
            f"Your current cash flow is in a monthly deficit of ₹{abs(surplus):,.0f} "
            f"on a monthly take-home income of ₹{income:,.0f}. Immediate adjustments are required "
            "to bring monthly living expenses within available income."
        )
    else:
        exec_summary = (
            f"You are operating with a positive monthly cash flow surplus of ₹{surplus:,.0f} "
            f"({savings_rate:.1f}% savings rate) from ₹{income:,.0f} take-home income. "
            "Your baseline cash flow is solvent and capable of funding structured savings."
        )

    # Section 2
    rec_disc = budget.get("recommended_categories", {}).get("Discretionary Living", {})
    disc_diff = rec_disc.get("diff", 0.0)
    if disc_diff < 0:
        budget_text = (
            f"To optimize your cash flow, discretionary spending is recommended to be trimmed by "
            f"₹{abs(disc_diff):,.0f}/mo (to ₹{rec_disc.get('recommended', 0):,.0f}/mo). "
            "Essential living expenses and contractual debt repayments are fully protected."
        )
    else:
        budget_text = (
            "Your current discretionary spending is already sustainable. The recommended plan "
            "preserves your day-to-day lifestyle while funneling existing surplus into structured targets."
        )

    # Section 3
    if coverage < 3.0:
        debt_emg_text = (
            f"Your emergency cushion covers {coverage:.1f} months of essential expenses. "
            f"Allocating ₹{emg_monthly:,.0f}/mo toward liquid reserves is prioritized to build your "
            f"safety cushion toward the 3–6 month baseline. Your Debt-to-Income ratio is {dti:.1f}%."
        )
    else:
        debt_emg_text = (
            f"Your emergency reserves cover a healthy {coverage:.1f} months of expenses. "
            f"With debt repayments consuming {dti:.1f}% of income, excess surplus can safely "
            "be directed toward financial goals and long-term investments."
        )

    # Section 4
    goals_detail = (goals_data or {}).get("goals_detail", [])
    if goals_detail:
        if (goals_data or {}).get("is_fully_funded"):
            goal_text = (
                f"All {len(goals_detail)} active milestone goals are fully funded with a combined allocation of "
                f"₹{(goals_data or {}).get('total_allocated_monthly', 0):,.0f}/mo. Automate these transfers on salary day."
            )
        else:
            goal_text = (
                f"You have a goal funding shortfall of ₹{(goals_data or {}).get('surplus_shortfall', 0):,.0f}/mo. "
                "Available surplus has been pro-rated. Consider extending timelines on lower-urgency goals."
            )
    else:
        goal_text = "No financial goals are currently configured. Setting specific milestone targets will help channel your monthly savings."

    return f"""### 📌 Executive Financial Summary
{exec_summary}

### 💡 Budget Adjustments & Rationale
{budget_text}

### 🛡️ Debt & Emergency Reserves Roadmap
{debt_emg_text}

### 🎯 Goal Strategy & Next Steps
{goal_text}
"""
