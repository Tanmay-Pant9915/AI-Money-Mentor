from groq import Groq
from dotenv import load_dotenv

import streamlit as st
import os
import json

load_dotenv()

api_key = st.secrets.get(
    "GROQ_API_KEY",
    os.getenv("GROQ_API_KEY")
)

client = Groq(
    api_key=api_key
)

# ---------------------------------------------------------------------------
# SYSTEM PROMPT
# Defines the AI persona, strict grounding rules, and output contract.
# Kept separate so it is never overwritten by user-supplied data.
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """
You are a SEBI-registered investment advisor specializing in Indian mutual funds.
You are given a JSON snapshot of a retail investor's mutual fund portfolio.

STRICT RULES — follow every rule without exception:
1. Base every statement ONLY on the numbers present in the portfolio JSON.
   Do NOT reference market conditions, index levels, or any data not in the JSON.
2. If a field is null or missing for a fund, explicitly say "data unavailable"
   for that fund instead of guessing.
3. Never recommend specific third-party funds, stocks, or products by name.
4. Keep all currency values in Indian Rupees (₹). Use Lakh/Crore notation for
   large numbers (e.g., ₹1.5 Lakh, ₹2.3 Crore).
5. Use plain English. Avoid jargon. A first-time investor must understand it.
6. Never exceed 350 words in total.
7. Always produce EXACTLY the five sections listed below — even for a
   single-fund portfolio — using the exact headings shown.

OUTPUT FORMAT (use these exact markdown headings, keep each section concise):

### 🏥 Portfolio Health
[2-3 sentences: overall verdict, diversification, and fund count context]

### 📈 Returns Analysis
[bullet per fund: "• <Scheme Name>: XIRR X.XX% — <Good/Average/Poor> vs typical equity MF benchmark of 10-12%"]
[If XIRR is null for a fund, say "data unavailable"]

### 💸 Expense Analysis
[bullet per fund: "• <Scheme Name>: Expense Ratio X.XX% — costs ₹X,XXX/year"]
[Flag any fund with expense ratio > 1.5% as HIGH COST]
[End with: Total annual fee drag across portfolio: ₹X,XXX]

### ⚠️ Key Risks
[2-4 bullet points identifying specific risks visible in this portfolio's data,
 e.g., concentration in one fund, high expense ratios, low/negative XIRR, etc.]

### ✅ Actionable Recommendations
[3-5 numbered, specific, data-driven suggestions based only on the portfolio JSON]
""".strip()


# ---------------------------------------------------------------------------
# USER PROMPT TEMPLATE
# Only carries the portfolio data — no instructions that could conflict with
# the system prompt or be confused with data.
# ---------------------------------------------------------------------------
_USER_PROMPT_TEMPLATE = """
Here is the portfolio data to analyze:

```json
{portfolio_json}
```

Portfolio summary:
- Total funds: {num_funds}
- Total current value: ₹{total_value:,.2f}
- Total annual expense drag: ₹{total_expense:,.2f}

Now produce the five-section analysis exactly as instructed.
""".strip()


def generate_portfolio_summary(portfolio_data: list) -> str:
    """
    Generate a structured, hallucination-resistant AI portfolio analysis.

    Args:
        portfolio_data: List of fund dicts with keys:
            scheme, current_value, xirr, expense_ratio, annual_expense_cost

    Returns:
        Markdown string with five labelled sections.
    """
    # Normalise: accept a single fund dict or a list of fund dicts.
    if isinstance(portfolio_data, dict):
        portfolio_data = [portfolio_data]

    # Pre-compute aggregates so the model doesn't have to — reduces errors.
    num_funds = len(portfolio_data)
    total_value = sum(
        f.get("current_value") or 0
        for f in portfolio_data
    )
    total_expense = sum(
        f.get("annual_expense_cost") or 0
        for f in portfolio_data
    )

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        portfolio_json=json.dumps(portfolio_data, indent=2, default=str),
        num_funds=num_funds,
        total_value=total_value,
        total_expense=total_expense,
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.2,   # Lower = more deterministic, fewer hallucinations.
            max_tokens=700,    # Enough for ~350 words + markdown formatting overhead.
        )
        return response.choices[0].message.content

    except Exception as exc:
        # Import inside except so the module still loads without groq installed.
        error_type = type(exc).__name__

        if "AuthenticationError" in error_type or "401" in str(exc):
            return (
                "⚠️ **AI Analysis unavailable** — GROQ_API_KEY is missing or invalid. "
                "Please set a valid key in your `.env` file and restart the app."
            )
        if "RateLimitError" in error_type or "429" in str(exc):
            return (
                "⚠️ **AI Analysis unavailable** — Groq API rate limit reached. "
                "Please wait a moment and re-run the analysis."
            )
        if "APIConnectionError" in error_type or "Connection" in error_type:
            return (
                "⚠️ **AI Analysis unavailable** — Could not reach the Groq API. "
                "Please check your internet connection and try again."
            )
        # Fallback for any other unexpected error.
        return (
            f"⚠️ **AI Analysis unavailable** — An unexpected error occurred "
            f"while contacting the AI service ({error_type}). "
            "The portfolio data table and charts above are still accurate."
        )