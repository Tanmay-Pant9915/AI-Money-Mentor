"""
views/chat_mentor_view.py
Streamlit view for Task 8: AI Chat Financial Mentor.
Provides an interactive, conversational personal finance assistant grounded in
Tasks 1-7 (Profile, Health Score, Budget, Goals, FIRE, Emergency/Insurance, Tax, Portfolio).
Features session conversation memory, starter question pills, deterministic what-if simulations,
live data source indicators, and regulatory disclaimers.
"""
from typing import Any, Dict, List, Optional
import streamlit as st

from services.financial_mentor_context import get_focused_context
from services.financial_mentor_service import _groq_client, ask_financial_mentor
from services.profile_service import get_profile


STARTER_QUESTIONS = [
    "🩺 How healthy is my current financial situation?",
    "💸 Where is most of my monthly income going?",
    "🛡️ How long will it take to reach my emergency fund target?",
    "🏖️ Am I on track to reach my retirement & FIRE goals?",
    "🏷️ Which tax regime has a lower estimated liability?",
    "📈 Analyze my mutual fund portfolio and XIRR",
    "💡 What if I save ₹5,000 more every month?",
    "📚 What is XIRR and why does it matter?",
]


def render_chat_mentor_view(
    user_id: str = "default_user",
    portfolio_data: Optional[Any] = None,
    db_path: Optional[str] = None,
) -> None:
    """Render the AI Financial Mentor conversational interface."""
    st.header("🤖 AI Financial Mentor")
    st.markdown(
        """
        Your personalized, conversational personal finance mentor. Ask questions about your
        **financial health**, **spending & budget**, **emergency runway**, **retirement & FIRE**,
        **tax optimization**, or **mutual fund portfolio**.
        """
    )

    # 1. Connected Context Status Bar
    _render_context_status_bar(user_id=user_id, portfolio_data=portfolio_data, db_path=db_path)

    # 2. Top Action Controls (Clear Chat & AI Status)
    col_ctrl, col_status = st.columns([3, 1])
    with col_ctrl:
        if st.button("🧹 Clear Conversation", help="Reset conversation history and start fresh"):
            st.session_state["mentor_chat_messages"] = []
            st.rerun()

    with col_status:
        if _groq_client is not None:
            st.caption("🟢 **Groq AI Active** (Llama-3.3-70B)")
        else:
            st.caption("🟡 **Deterministic Offline Mode** (Deterministic summaries)")

    # 3. Initialize Conversation State
    if "mentor_chat_messages" not in st.session_state:
        st.session_state["mentor_chat_messages"] = [
            {
                "role": "assistant",
                "content": (
                    "👋 **Hello! I'm your AI Money Mentor.**\n\n"
                    "I am connected to your financial profile, budget, emergency runway, retirement projections, "
                    "tax regimes, and mutual fund portfolio. How can I help you today?\n\n"
                    "Feel free to click any of the suggested questions below or type your own question."
                ),
                "is_initial": True,
            }
        ]

    # 4. Suggested Starter Questions Expander
    with st.expander("💡 **Suggested Questions to Ask**", expanded=len(st.session_state["mentor_chat_messages"]) <= 1):
        st.markdown("*Click any question below to immediately ask your mentor:*")
        c1, c2 = st.columns(2)
        for idx, prompt_text in enumerate(STARTER_QUESTIONS):
            col = c1 if idx % 2 == 0 else c2
            clean_prompt = prompt_text.split(" ", 1)[1] if " " in prompt_text else prompt_text
            if col.button(prompt_text, key=f"starter_btn_{idx}", use_container_width=True):
                st.session_state["mentor_pending_query"] = clean_prompt
                st.rerun()

    st.divider()

    # 5. Display Conversation History
    for msg in st.session_state["mentor_chat_messages"]:
        role = msg.get("role", "assistant")
        with st.chat_message(role):
            st.markdown(msg.get("content", ""))
            if msg.get("simulation_result"):
                sim = msg["simulation_result"]
                st.info(f"🔄 **Simulated Impact:** {sim.get('impact_summary', '')}")
            if msg.get("category_name") and role == "assistant" and not msg.get("is_initial"):
                st.caption(f"📁 *Category: {msg.get('category_name')}*")

    # 6. Capture Pending Query or Chat Input
    user_query = None
    if "mentor_pending_query" in st.session_state and st.session_state["mentor_pending_query"]:
        user_query = st.session_state.pop("mentor_pending_query")

    typed_input = st.chat_input("Ask your Financial Mentor a question (e.g., 'How healthy is my financial situation?')...")
    if typed_input:
        user_query = typed_input

    # 7. Process User Query
    if user_query:
        # Append User Message
        st.session_state["mentor_chat_messages"].append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # Generate Assistant Response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your financial context and preparing grounded response..."):
                resp = ask_financial_mentor(
                    user_query=user_query,
                    user_id=user_id,
                    conversation_history=st.session_state["mentor_chat_messages"][:-1],
                    portfolio_data=portfolio_data,
                    financial_year="2024-25",
                    db_path=db_path,
                )

                st.markdown(resp.content)
                if resp.simulation_result:
                    sim = resp.simulation_result
                    st.info(f"🔄 **Simulated Impact:** {sim.get('impact_summary', '')}")
                if resp.category_name:
                    st.caption(f"📁 *Category: {resp.category_name}*")

                # Record in state
                st.session_state["mentor_chat_messages"].append(
                    {
                        "role": "assistant",
                        "content": resp.content,
                        "intent": resp.intent,
                        "category_name": resp.category_name,
                        "is_ai_generated": resp.is_ai_generated,
                        "simulation_result": resp.simulation_result,
                    }
                )

    # 8. Regulatory Disclaimer
    st.markdown("---")
    st.caption(
        "⚖️ **Regulatory & Educational Disclaimer**: AI Money Mentor is an educational tool designed to help you analyze "
        "and explore personal financial planning scenarios. It is not a SEBI-registered Investment Adviser, IRDAI insurance broker, "
        "or Chartered Accountant. Projections and calculations are educational estimates based on user-supplied information and "
        "historical figures. Please consult a qualified SEBI RIA or certified financial planner before executing major financial decisions."
    )


def _render_context_status_bar(
    user_id: str = "default_user",
    portfolio_data: Optional[Any] = None,
    db_path: Optional[str] = None,
) -> None:
    """Render compact pill badges displaying available financial data modules."""
    summary_ctx = get_focused_context(
        intent="GENERAL_SUMMARY",
        user_id=user_id,
        portfolio_data=portfolio_data,
        db_path=db_path,
    )

    prof = summary_ctx.get("financial_profile")
    health = summary_ctx.get("money_health_score")
    budget = summary_ctx.get("budget_plan")
    goals = summary_ctx.get("goals")
    fire = summary_ctx.get("retirement_fire_plan")
    efund = summary_ctx.get("emergency_fund_plan")
    ins = summary_ctx.get("insurance_assessment")
    tax = summary_ctx.get("tax_plan")
    port = summary_ctx.get("portfolio")

    with st.expander("📊 **Connected Financial Modules & Data Sources**", expanded=False):
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            if prof and prof.get("monthly_income", 0) > 0:
                st.success(f"👤 Profile: ₹{prof['monthly_income']:,.0f}/mo")
            else:
                st.warning("👤 Profile: Incomplete")

            if health and health.get("score") is not None:
                st.success(f"🩺 Health Score: {health['score']}/100")
            else:
                st.info("🩺 Health Score: Not calculated")

        with c2:
            if budget and budget.get("monthly_income", 0) > 0:
                st.success(f"📋 Budget: {budget.get('savings_rate_pct', 0):.1f}% savings")
            else:
                st.info("📋 Budget: Not saved")

            if goals and len(goals) > 0:
                st.success(f"🎯 Goals: {len(goals)} active")
            else:
                st.info("🎯 Goals: None recorded")

        with c3:
            if fire and fire.get("projected_corpus", 0) > 0:
                st.success(f"🏖️ FIRE: ₹{fire['projected_corpus']/1e7:.2f} Cr target")
            else:
                st.info("🏖️ FIRE: Not projected")

            if efund and efund.get("current_liquid_savings", 0) > 0:
                st.success(f"🛡️ E-Fund: {efund.get('runway_months', 0):.1f} mo runway")
            else:
                st.info("🛡️ E-Fund: Not planned")

        with c4:
            if tax and tax.get("recommended_regime"):
                st.success(f"🏷️ Tax: {tax['recommended_regime']}")
            else:
                st.info("🏷️ Tax: Not assessed")

            if port and port.get("total_value", 0) > 0:
                st.success(f"📈 Portfolio: ₹{port['total_value']:,.0f}")
            else:
                st.info("📈 Portfolio: CAS not uploaded")
