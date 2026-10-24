"""
views/risk_view.py
Streamlit UI view for Risk Assessment Questionnaire, Deterministic Scoring,
Educational Insights, and Retake Flow.
"""
import streamlit as st

from services.profile_service import get_profile
from services.risk_profile_service import (
    get_latest_risk_assessment,
    get_risk_assessment_history,
    submit_risk_assessment,
)
from utils.risk_scoring import RISK_QUESTIONS


def render_risk_view():
    st.header("🎯 Investment Risk Profile & Tolerance Assessment")
    st.caption(
        "Evaluate your psychological risk tolerance alongside your objective financial capacity. "
        "Calculated deterministically without third-party LLMs."
    )
    st.divider()

    latest = get_latest_risk_assessment(user_id="default_user")

    if "retake_mode" not in st.session_state:
        st.session_state.retake_mode = False

    if latest is not None and not st.session_state.retake_mode:
        _render_assessment_results(latest)
    else:
        _render_questionnaire_form(latest)


def _render_assessment_results(assessment: dict):
    score = assessment.get("score", 0.0)
    classification = assessment.get("classification", "Moderate")

    # Classification Badge Color
    color_map = {
        "Conservative": "#3b82f6",  # Blue
        "Moderate": "#f59e0b",      # Amber
        "Aggressive": "#ef4444",    # Red
    }
    badge_color = color_map.get(classification, "#10b981")

    # Score Banner
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.9)); 
                    border: 2px solid {badge_color}; border-radius: 16px; padding: 24px; margin-bottom: 25px; text-align: center;">
            <div style="font-size: 1rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600;">
                Assessed Risk Classification
            </div>
            <div style="font-size: 3rem; font-weight: 800; color: {badge_color}; margin: 8px 0;">
                {classification}
            </div>
            <div style="font-size: 1.25rem; color: #e2e8f0;">
                Risk Score: <strong>{score} / 100</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sub-scores: Capacity vs Tolerance
    st.markdown("### ⚖️ The Two Pillars of Investment Risk")
    st.caption(
        "**Financial Capacity** is your objective financial ability to withstand losses (runway, debt, horizon). "
        "**Risk Tolerance** is your emotional comfort with market swings."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Financial Capacity</div>
                <div class="metric-value">{assessment.get('capacity_score')}/100</div>
                <p style="font-size: 0.85rem; color: var(--text-color); opacity: 0.8; margin-top: 8px;">
                    Objective ability to bear losses without lifestyle distress.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Psychological Tolerance</div>
                <div class="metric-value">{assessment.get('tolerance_score')}/100</div>
                <p style="font-size: 0.85rem; color: var(--text-color); opacity: 0.8; margin-top: 8px;">
                    Emotional appetite and comfort during sharp market downturns.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Guardrail notice if applied
    if assessment.get("guardrail_applied"):
        for reason in assessment.get("guardrail_reasons", []):
            st.warning(f"🛡️ **Risk Guardrail Triggered:** {reason}")

    # Financial Constraints
    constraints = assessment.get("constraints", [])
    if constraints:
        st.markdown("### ⚠️ Key Constraints Identified")
        for c in constraints:
            st.markdown(f"- 🔴 {c}")

    # Detailed Guidance & Explanation
    st.markdown("### 📖 Educational Guidance & Strategy")
    st.info(assessment.get("explanation", ""))
    st.markdown(f"**Recommended Asset Allocation Framework:**\n\n{assessment.get('guidance', '')}")

    # Regulatory Educational Disclaimer
    st.caption(f"ℹ️ {assessment.get('disclaimer', '')}")

    # Action buttons: Retake Assessment
    st.divider()
    col_retake, col_hist = st.columns([2, 3])
    with col_retake:
        if st.button("🔄 Retake Risk Questionnaire", use_container_width=True, type="secondary"):
            st.session_state.confirm_retake = True
            st.rerun()

    # Confirmation Modal/Banner
    if st.session_state.get("confirm_retake", False):
        st.warning(
            "⚠️ **Retaking the questionnaire will update your active risk score and classification.** "
            "Future asset allocation suggestions will adapt to your updated profile. "
            "Your previous assessment will be saved in your assessment history. Do you wish to proceed?"
        )
        conf_col1, conf_col2 = st.columns(2)
        with conf_col1:
            if st.button("✅ Yes, Retake Questionnaire", type="primary", use_container_width=True):
                st.session_state.retake_mode = True
                st.session_state.confirm_retake = False
                st.rerun()
        with conf_col2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.confirm_retake = False
                st.rerun()

    # Assessment History
    with st.expander("📜 View Assessment History"):
        history = get_risk_assessment_history(user_id="default_user")
        if history:
            for h in history:
                status_tag = " [Current Active]" if h["is_latest"] == 1 else ""
                st.write(
                    f"- **{h['created_at'][:19]}**: Score **{h['score']}/100** ({h['classification']}) "
                    f"| Capacity: {h['capacity_score']} | Tolerance: {h['tolerance_score']}{status_tag}"
                )
        else:
            st.write("No prior assessments recorded.")


def _render_questionnaire_form(existing_assessment: dict = None):
    st.subheader("Risk Profiling Questionnaire")
    st.write(
        "Answer the 12 questions below to determine your risk profile. "
        "Take your time to select the option that best matches your financial situation and mindset."
    )

    # Initialize answers in session state
    if "risk_answers" not in st.session_state:
        st.session_state.risk_answers = (
            dict(existing_assessment.get("answers", {}))
            if existing_assessment and "answers" in existing_assessment
            else {}
        )

    # Calculate completion progress
    total_q = len(RISK_QUESTIONS)
    answered_count = sum(1 for q in RISK_QUESTIONS if q["id"] in st.session_state.risk_answers)
    progress_pct = answered_count / total_q
    st.progress(progress_pct, text=f"Questionnaire Progress: {answered_count}/{total_q} Answered ({int(progress_pct*100)}%)")

    # Group questions into 4 logical sections
    sections = [
        ("Section 1: Life Stage & Financial Stability", RISK_QUESTIONS[0:3]),
        ("Section 2: Investment Horizon & Experience", [RISK_QUESTIONS[3], RISK_QUESTIONS[4], RISK_QUESTIONS[9]]),
        ("Section 3: Market Volatility & Drawdown Reactions", RISK_QUESTIONS[5:8]),
        ("Section 4: Patience & Growth Priorities", [RISK_QUESTIONS[8], RISK_QUESTIONS[10], RISK_QUESTIONS[11]]),
    ]

    for sec_title, q_list in sections:
        with st.expander(sec_title, expanded=True):
            for q in q_list:
                qid = q["id"]
                st.markdown(f"**{q['factor']}**")
                st.write(q["question"])

                # Find current selected index
                opt_labels = [f"{opt['label']} — {opt['description']}" for opt in q["options"]]
                curr_score = st.session_state.risk_answers.get(qid)
                default_idx = None
                if curr_score is not None:
                    # scores are 1-based (1, 2, 3, 4) -> idx 0, 1, 2, 3
                    default_idx = max(0, min(len(opt_labels) - 1, curr_score - 1))

                selected_label = st.radio(
                    f"Select your answer for {q['factor']}:",
                    options=opt_labels,
                    index=default_idx,
                    key=f"radio_{qid}",
                    label_visibility="collapsed",
                )

                if selected_label:
                    # Map back to score
                    chosen_idx = opt_labels.index(selected_label)
                    st.session_state.risk_answers[qid] = q["options"][chosen_idx]["score"]

                st.markdown("---")

    # Submission section
    st.markdown("### Review & Submit")
    if answered_count < total_q:
        st.warning(f"Please answer all {total_q} questions to calculate your risk profile ({total_q - answered_count} remaining).")
        submit_disabled = True
    else:
        st.success("All questions answered! You are ready to calculate your risk profile.")
        submit_disabled = False

    sub_col1, sub_col2 = st.columns([3, 1])
    with sub_col1:
        if st.button("📊 Calculate & Save Risk Profile", type="primary", use_container_width=True, disabled=submit_disabled):
            # Fetch user financial profile if available to enrich constraints
            fin_profile = get_profile(user_id="default_user")

            # Submit and score
            result = submit_risk_assessment(
                answers=st.session_state.risk_answers,
                user_id="default_user",
                financial_profile=fin_profile,
            )
            st.success(f"✅ Risk Profile Calculated: **{result['classification']}** ({result['score']}/100)!")
            st.session_state.retake_mode = False
            st.rerun()

    with sub_col2:
        if existing_assessment is not None:
            if st.button("Cancel", use_container_width=True):
                st.session_state.retake_mode = False
                st.rerun()
