"""
services/financial_mentor_service.py
Core conversational orchestration service for AI Financial Mentor.
Coordinates question classification, context extraction, deterministic scenario execution,
Groq LLM generation, conversation memory, and robust offline fallbacks.
"""
from dataclasses import dataclass, field
import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from groq import Groq
import streamlit as st

from services.financial_mentor_context import get_focused_context
from services.financial_mentor_router import classify_user_intent
from utils.financial_mentor_prompt import (
    FINANCIAL_MENTOR_SYSTEM_PROMPT,
    build_mentor_user_prompt,
)
from utils.financial_mentor_scenarios import detect_and_simulate_scenario

load_dotenv()

# Initialize Groq client
_api_key = os.getenv("GROQ_API_KEY")
if not _api_key:
    try:
        _api_key = st.secrets.get("GROQ_API_KEY")
    except Exception:
        _api_key = None

_groq_client = Groq(api_key=_api_key) if _api_key else None
_DEFAULT_CLIENT = object()


@dataclass
class MentorResponse:
    """Standardized response from the AI Financial Mentor."""
    content: str
    intent: str
    category_name: str
    is_ai_generated: bool
    context_used: Dict[str, Any] = field(default_factory=dict)
    simulation_result: Optional[Dict[str, Any]] = None
    error_note: Optional[str] = None


def generate_deterministic_fallback(
    intent: str,
    category_name: str,
    context: Dict[str, Any],
    simulation: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Produce a clean, explainable, deterministic markdown response when Groq API is unavailable.
    """
    lines = [
        f"### 📊 Financial Overview: {category_name}",
        "*Note: AI service is offline. Here is a verified deterministic summary of your data.*",
        "",
    ]

    # If simulation was performed
    if simulation:
        lines.append("#### 🧪 What-If Scenario Calculation Results:")
        for k, v in simulation.items():
            if k not in ("scenario_type", "note"):
                clean_key = k.replace("_", " ").title()
                lines.append(f"- **{clean_key}:** {v}")
        if simulation.get("note"):
            lines.append(f"*{simulation['note']}*")
        lines.append("")
        return "\n".join(lines)

    # Health score
    if "money_health" in context and context["money_health"].get("status") == "available":
        mh = context["money_health"]
        lines.append(f"- **Overall Money Health Score:** {mh.get('overall_score')} ({mh.get('rating')})")
        lines.append("- **Component Scores:**")
        for sub_k, sub_v in mh.get("sub_scores", {}).items():
            lines.append(f"  • {sub_k.replace('_', ' ').title()}: {sub_v}")

    # Emergency fund
    if "emergency_fund" in context and context["emergency_fund"].get("status") == "available":
        ef = context["emergency_fund"]
        lines.append(f"- **Emergency Fund Coverage:** {ef.get('actual_coverage_months')} (Target: {ef.get('target_coverage_months')})")
        lines.append(f"- **Current Savings:** {ef.get('current_savings')} | **Remaining Gap:** {ef.get('fund_gap')}")

    # Budget
    if "budget" in context and context["budget"].get("status") == "available":
        bg = context["budget"]
        lines.append(f"- **Monthly Income:** {bg.get('monthly_income')} | **Current Surplus:** {bg.get('current_savings_surplus')}")
        rec = bg.get("recommended_50_30_20", {})
        lines.append(f"- **50/30/20 Targets:** Needs: {rec.get('needs_target')} | Wants: {rec.get('wants_target')} | Savings: {rec.get('savings_target')}")

    # Retirement
    if "retirement" in context and context["retirement"].get("status") == "available":
        rt = context["retirement"]
        lines.append(f"- **Retirement Target Age:** {rt.get('target_retirement_age')} | **Target Corpus:** {rt.get('target_retirement_corpus')}")
        lines.append(f"- **Projected Corpus:** {rt.get('projected_corpus_at_retirement')} | **Required Monthly:** {rt.get('required_monthly_investment')}")

    # Tax
    if "tax" in context and context["tax"].get("status") == "available":
        tx = context["tax"]
        lines.append(f"- **Recommended Regime (FY {tx.get('financial_year')}):** {tx.get('recommended_regime')}")
        lines.append(f"- **Tax Savings Difference:** {tx.get('tax_savings_difference')}")

    # Portfolio
    if "portfolio" in context and context["portfolio"].get("status") == "available":
        pf = context["portfolio"]
        lines.append(f"- **Portfolio Valuation:** {pf.get('total_valuation')} ({pf.get('fund_count')} funds)")
        lines.append(f"- **Average XIRR:** {pf.get('average_xirr')} | **Average Expense Ratio:** {pf.get('average_expense_ratio')}")

    # Profile fallback
    prof = context.get("profile", {})
    if prof.get("status") == "available":
        lines.append("")
        lines.append(f"**Monthly Income:** {prof.get('monthly_income')} | **Total Expenses:** {prof.get('total_monthly_expenses')} | **Surplus:** {prof.get('monthly_surplus')}")
    else:
        lines.append("\n*No active financial profile found. You can set up your profile in the 'Financial Profile' section.*")

    lines.append("\n👉 *Next Step: Review the corresponding module in the sidebar navigation for detailed interactive planning.*")
    return "\n".join(lines)


def ask_financial_mentor(
    user_query: str,
    user_id: str = "default_user",
    conversation_history: Optional[List[Dict[str, str]]] = None,
    portfolio_data: Optional[Any] = None,
    financial_year: str = "2024-25",
    db_path: Optional[str] = None,
    groq_client: Any = _DEFAULT_CLIENT,
) -> MentorResponse:
    """
    Main entrypoint for interacting with the AI Financial Mentor.
    Retrieves grounded context, executes what-if calculations, queries LLM, and falls back gracefully.
    """
    client_to_use = _groq_client if groq_client is _DEFAULT_CLIENT else groq_client

    # 1. Classify Intent
    intent, category_name = classify_user_intent(user_query)

    # 2. Check for deterministic What-If simulation
    simulation_result = detect_and_simulate_scenario(user_query, user_id=user_id, db_path=db_path)
    if simulation_result:
        intent = "WHAT_IF_SCENARIO"
        category_name = "What-If Scenario Simulation"

    # 3. Retrieve Focused Context
    context_data = get_focused_context(
        intent=intent,
        user_id=user_id,
        portfolio_data=portfolio_data,
        financial_year=financial_year,
        db_path=db_path,
    )

    if simulation_result:
        context_data["simulation_result"] = simulation_result

    # 4. If AI Client is missing, return deterministic fallback immediately
    if client_to_use is None:
        fallback_text = generate_deterministic_fallback(
            intent=intent,
            category_name=category_name,
            context=context_data,
            simulation=simulation_result,
        )
        return MentorResponse(
            content=fallback_text,
            intent=intent,
            category_name=category_name,
            is_ai_generated=False,
            context_used=context_data,
            simulation_result=simulation_result,
            error_note="GROQ_API_KEY is not configured. Displaying deterministic profile summary.",
        )

    # 5. Build Grounded Prompts with Conversation Memory
    user_prompt = build_mentor_user_prompt(
        user_query=user_query,
        context_data=context_data,
        category_name=category_name,
    )

    messages = [{"role": "system", "content": FINANCIAL_MENTOR_SYSTEM_PROMPT}]

    # Include up to last 4 conversation turns for conversational continuity
    if conversation_history:
        recent_history = conversation_history[-4:]
        for msg in recent_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    # Append current grounded user turn
    messages.append({"role": "user", "content": user_prompt})

    # 6. Query Groq LLM
    try:
        response = client_to_use.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.2,   # Grounded and deterministic
            max_tokens=900,
        )
        ai_reply = response.choices[0].message.content

        return MentorResponse(
            content=ai_reply,
            intent=intent,
            category_name=category_name,
            is_ai_generated=True,
            context_used=context_data,
            simulation_result=simulation_result,
        )

    except Exception as exc:
        err_msg = str(exc)
        fallback_text = generate_deterministic_fallback(
            intent=intent,
            category_name=category_name,
            context=context_data,
            simulation=simulation_result,
        )
        return MentorResponse(
            content=fallback_text,
            intent=intent,
            category_name=category_name,
            is_ai_generated=False,
            context_used=context_data,
            simulation_result=simulation_result,
            error_note=f"AI service connection notice ({type(exc).__name__}). Displaying deterministic profile data.",
        )
