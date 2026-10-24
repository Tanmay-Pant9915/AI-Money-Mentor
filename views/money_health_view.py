"""
views/money_health_view.py
Streamlit UI view for the deterministic Money Health Score dashboard.
Displays overall score, rating badge, data completeness, component breakdown,
actionable rule-based insights, prioritized recommendations, and score history.
"""
from datetime import datetime
from typing import Any, Dict, Optional
import pandas as pd
import streamlit as st

from services.money_health_service import (
    get_health_score_history,
    get_latest_health_score,
    get_or_calculate_health_score,
)
from services.profile_service import format_inr, get_profile


def render_money_health_view(
    cas_portfolio: Optional[Dict[str, Any]] = None,
    user_id: str = "default_user",
    db_path: Optional[str] = None,
):
    """Render the primary Money Health Score dashboard view."""
    st.header("🩺 Money Health Score")
    st.caption(
        "A comprehensive, explainable evaluation of your overall financial health across "
        "5 core pillars: Savings, Debt, Emergency Cushion, Investments, and Goals."
    )
    st.divider()

    # Load existing profile to verify presence
    profile = get_profile(user_id=user_id, db_path=db_path)

    # Action buttons row
    top_col1, top_col2, top_col3 = st.columns([5, 2, 2])
    with top_col2:
        recalc_clicked = st.button("🔄 Recalculate Score", use_container_width=True, type="secondary")
    with top_col3:
        if st.button("👤 View Profile", use_container_width=True):
            st.session_state["nav_override"] = "👤 Financial Profile"
            st.rerun()

    # Calculate or retrieve score
    health_result = get_or_calculate_health_score(
        user_id=user_id,
        cas_portfolio=cas_portfolio,
        force_recalculate=recalc_clicked,
        db_path=db_path,
    )

    if recalc_clicked:
        st.toast("✅ Money Health Score successfully recalculated!", icon="🩺")

    # If profile does not exist or has insufficient data
    if not profile:
        _render_no_profile_state()
        return

    if not health_result.get("is_sufficient_data"):
        _render_incomplete_data_state(health_result, profile)
        return

    # 1. Hero Score Banner
    _render_hero_score_card(health_result)

    st.markdown("---")

    # 2. Five Component Cards
    st.subheader("📊 The 5 Core Financial Pillars")
    st.caption(
        "Each pillar contributes to your overall score based on its assigned weight. "
        "Missing pillars have their weights proportionally normalized."
    )
    _render_component_cards(health_result.get("components", {}))

    st.markdown("---")

    # 3. Component Summary Comparison Table
    _render_component_table(health_result.get("components", {}))

    st.markdown("---")

    # 4. Financial Insights & Prioritized Recommendations
    col_insights, col_recs = st.columns(2)
    with col_insights:
        _render_insights_section(health_result.get("insights", []))
    with col_recs:
        _render_recommendations_section(health_result.get("recommendations", []))

    st.markdown("---")

    # 5. Historical Trends & Auditing
    _render_history_section(user_id=user_id, db_path=db_path)

    st.markdown("---")

    # 6. Educational Disclaimer
    _render_disclaimer(health_result.get("disclaimer"))


def _render_hero_score_card(result: Dict[str, Any]):
    """Render the top visual hero banner with the overall score and rating badge."""
    score = result.get("overall_score")
    rating = result.get("rating", "Needs Attention")
    completeness = result.get("data_completeness", 0.0)
    calculated_at = result.get("calculated_at", "")
    excluded = result.get("excluded_components", [])

    # Format calculation timestamp
    calc_time_str = "Recently"
    if calculated_at:
        try:
            dt = datetime.fromisoformat(calculated_at)
            calc_time_str = dt.strftime("%b %d, %Y at %I:%M %p")
        except Exception:
            calc_time_str = calculated_at[:19]

    # Color tokens based on rating
    rating_colors = {
        "Needs Attention": ("#ef4444", "rgba(239, 68, 68, 0.15)"),
        "Fair": ("#f59e0b", "rgba(245, 158, 11, 0.15)"),
        "Good": ("#3b82f6", "rgba(59, 130, 246, 0.15)"),
        "Excellent": ("#10b981", "rgba(16, 185, 129, 0.15)"),
    }
    badge_color, badge_bg = rating_colors.get(rating, ("#3b82f6", "rgba(59, 130, 246, 0.15)"))

    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.75), rgba(15, 23, 42, 0.95));
                    border: 2px solid {badge_color}; border-radius: 20px; padding: 28px; margin-bottom: 20px;
                    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2); text-align: center;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap;">
                <span style="font-size: 0.85rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600;">
                    Overall Financial Health
                </span>
                <span style="font-size: 0.85rem; color: #94a3b8;">
                    🕒 Last Calculated: <strong style="color: #f1f5f9;">{calc_time_str}</strong>
                </span>
            </div>
            <div style="display: flex; justify-content: center; align-items: baseline; gap: 12px; margin: 12px 0;">
                <span style="font-size: 4.5rem; font-weight: 800; color: {badge_color}; line-height: 1;">
                    {score}
                </span>
                <span style="font-size: 1.75rem; font-weight: 600; color: #64748b;">
                    / 100
                </span>
            </div>
            <div style="display: inline-block; background: {badge_bg}; border: 1px solid {badge_color};
                        color: {badge_color}; padding: 6px 20px; border-radius: 9999px; font-weight: 700;
                        font-size: 1.1rem; letter-spacing: 0.5px; margin-bottom: 16px;">
                {rating}
            </div>
            <div style="max-width: 650px; margin: 0 auto; color: #cbd5e1; font-size: 0.95rem; line-height: 1.5;">
                {_get_rating_description(rating, score)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Data Completeness Progress Bar
    comp_col1, comp_col2 = st.columns([3, 1])
    with comp_col1:
        st.write(f"**Data Completeness:** {completeness:.0f}%")
        st.progress(min(1.0, completeness / 100.0))
    with comp_col2:
        if excluded:
            st.caption(f"Excluded: *{', '.join(excluded)}* (weights normalized)")
        else:
            st.caption("✅ All 5 financial pillars evaluated.")


def _get_rating_description(rating: str, score: Optional[int]) -> str:
    """Return an educational explanation corresponding to the score band."""
    if rating == "Excellent":
        return (
            "Outstanding financial health! You demonstrate high savings discipline, "
            "minimal debt obligations, a solid emergency cushion, and active investments."
        )
    elif rating == "Good":
        return (
            "Solid financial foundation. Most key areas are in good standing. "
            "Focusing on the minor shortfalls highlighted below can elevate you into the Excellent tier."
        )
    elif rating == "Fair":
        return (
            "Moderate financial health. While certain components are functional, key vulnerabilities "
            "in cash flow, debt burden, or liquidity reserves require proactive adjustments."
        )
    else:
        return (
            "Financial health requires prompt attention. Essential living expenses, debt repayments, "
            "or lack of liquid reserves place stress on your cash flow. Follow the prioritized actions below."
        )


def _render_component_cards(components: Dict[str, Dict[str, Any]]):
    """Render the 5 component cards with metrics, scores, weights, and progress bars."""
    pillar_configs = [
        ("savings_rate", "💰 Savings Rate", "25%"),
        ("debt_burden", "💳 Debt Burden", "25%"),
        ("emergency_fund", "🛡️ Emergency Cushion", "20%"),
        ("investment_health", "📈 Investment Health", "20%"),
        ("goal_progress", "🎯 Goal Progress", "10%"),
    ]

    col1, col2 = st.columns(2)
    col_list = [col1, col2]

    for idx, (key, title, weight_label) in enumerate(pillar_configs):
        target_col = col_list[idx % 2]
        comp = components.get(key, {})
        is_avail = comp.get("is_available", False)
        score = comp.get("score")
        metric_disp = comp.get("display_metric", "Unavailable")
        contrib = comp.get("weighted_contribution", 0.0)
        status = comp.get("status", "Unavailable")
        explanation = comp.get("explanation", "Data unavailable.")

        with target_col:
            with st.container(border=True):
                # Header row
                h_col1, h_col2 = st.columns([3, 1])
                with h_col1:
                    st.markdown(f"#### {title}")
                with h_col2:
                    st.caption(f"Weight: **{weight_label}**")

                if is_avail and score is not None:
                    # Metric and Score display
                    m_col1, m_col2, m_col3 = st.columns(3)
                    with m_col1:
                        st.metric("Metric", metric_disp)
                    with m_col2:
                        st.metric("Score", f"{score:.0f}/100")
                    with m_col3:
                        st.metric("Contribution", f"{contrib:.1f} pts")

                    # Visual Progress Bar
                    score_ratio = max(0.0, min(1.0, score / 100.0))
                    st.progress(score_ratio)

                    # Status badge and explanation
                    st.markdown(f"**Status:** `{status}`")
                    st.write(explanation)

                    # Extra details if available
                    if key == "emergency_fund" and comp.get("shortfall") is not None:
                        sf = comp.get("shortfall", 0.0)
                        if sf > 0:
                            st.caption(f"Estimated shortfall to 6-month buffer: **{format_inr(sf)}**")
                    elif key == "debt_burden" and comp.get("actual_value") is not None:
                        st.caption(f"Monthly Debt-to-Income: **{comp.get('actual_value'):.1f}%**")
                else:
                    st.warning(f"⚠️ **{title} is Excluded**")
                    st.write(explanation)
                    st.caption("Weight is normalized across available components so your score is not penalized.")


def _render_component_table(components: Dict[str, Dict[str, Any]]):
    """Render a clean comparison table summarizing all 5 components."""
    st.subheader("📋 Pillar Breakdown Summary")

    table_data = []
    for key, comp in components.items():
        name = comp.get("name", key.replace("_", " ").title())
        is_avail = comp.get("is_available", False)
        metric = comp.get("display_metric", "—")
        score = f"{comp.get('score', 0):.0f} / 100" if is_avail else "Excluded"
        weight = f"{int(comp.get('weight', 0.2) * 100)}%"
        contrib = f"{comp.get('weighted_contribution', 0):.1f} pts" if is_avail else "0.0 pts"
        status = comp.get("status", "Unavailable") if is_avail else "Excluded"

        table_data.append({
            "Pillar": name,
            "Actual Value": metric,
            "Score": score,
            "Configured Weight": weight,
            "Weighted Contribution": contrib,
            "Status": status,
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_insights_section(insights: list):
    """Render rule-based deterministic financial observations."""
    st.subheader("💡 Key Financial Observations")
    if not insights:
        st.info("No specific alerts triggered. Your financial metrics are within normal parameters.")
        return

    for item in insights:
        if item.startswith("🔴"):
            st.error(item)
        elif item.startswith("🟡") or item.startswith("⚠️"):
            st.warning(item)
        elif item.startswith("🟢"):
            st.success(item)
        else:
            st.info(item)


def _render_recommendations_section(recommendations: list):
    """Render prioritized actionable recommendations based on weakest components."""
    st.subheader("🚀 Prioritized Action Plan")
    if not recommendations:
        st.success("🎉 Excellent! All key financial components are in top tier. Maintain your current plan.")
        return

    for rec in recommendations:
        prio = rec.get("priority", "Medium")
        area = rec.get("area", "Finance")
        action = rec.get("action", "")

        prio_color = "#ef4444" if prio == "High" else "#f59e0b" if prio == "Medium" else "#3b82f6"
        with st.container(border=True):
            r_col1, r_col2 = st.columns([4, 1])
            with r_col1:
                st.markdown(f"**{area}**")
                st.write(action)
            with r_col2:
                st.markdown(
                    f"<span style='color: {prio_color}; font-weight: 700; border: 1px solid {prio_color}; "
                    f"padding: 2px 8px; border-radius: 4px; font-size: 0.8rem;'>{prio} Priority</span>",
                    unsafe_allow_html=True,
                )


def _render_history_section(user_id: str, db_path: Optional[str] = None):
    """Render an expandable audit history of previously calculated scores."""
    with st.expander("📜 Score Calculation History & Audit Log", expanded=False):
        history = get_health_score_history(user_id=user_id, db_path=db_path)
        if not history:
            st.info("No historical score records found yet.")
            return

        hist_rows = []
        for h in history:
            score_val = f"{h['overall_score']} / 100" if h.get("overall_score") is not None else "Incomplete"
            rating_val = h.get("rating") or "Incomplete"
            comp_val = f"{h.get('data_completeness', 0):.0f}%"
            date_raw = h.get("calculated_at", "")
            try:
                date_str = datetime.fromisoformat(date_raw).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                date_str = date_raw

            hist_rows.append({
                "Calculation Date": date_str,
                "Score": score_val,
                "Rating": rating_val,
                "Completeness": comp_val,
                "Is Latest": "✅ Yes" if h.get("is_latest") == 1 else "No",
            })

        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)


def _render_disclaimer(disclaimer_text: Optional[str]):
    """Render mandatory educational notice."""
    st.info(
        f"⚖️ **Educational Financial Notice:** {disclaimer_text or 'The Money Health Score is an educational indicator...'}"
    )


def _render_no_profile_state():
    """State displayed when no financial profile is found in database."""
    st.warning("⚠️ **No Financial Profile Found**")
    st.write(
        "To calculate your Money Health Score, you first need to set up your Financial Profile "
        "with your income, expenses, and savings details."
    )
    if st.button("🚀 Create Your Financial Profile", type="primary"):
        st.session_state["nav_override"] = "👤 Financial Profile"
        st.rerun()


def _render_incomplete_data_state(result: Dict[str, Any], profile: Dict[str, Any]):
    """State displayed when profile exists but has insufficient data for a valid score."""
    completeness = result.get("data_completeness", 0.0)
    excluded = result.get("excluded_components", [])

    st.warning("⚠️ **Insufficient Financial Data for Score Calculation**")
    st.write(
        f"Your profile data completeness is currently at **{completeness:.0f}%**. "
        "At least **40%** data completeness with verified take-home income is required "
        "to generate a reliable, unbiased Money Health Score."
    )

    st.markdown(
        f"""
        <div style="background: rgba(245, 158, 11, 0.1); border-left: 4px solid #f59e0b;
                    padding: 16px; border-radius: 8px; margin: 15px 0;">
            <strong>Missing or Incomplete Components:</strong>
            <ul>
                {''.join(f'<li>{comp}</li>' for comp in excluded)}
            </ul>
            Please update your <strong>Financial Profile</strong> to include monthly income, 
            essential living costs, and debt or savings details.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("✏️ Complete Financial Profile Now", type="primary"):
        st.session_state["nav_override"] = "👤 Financial Profile"
        st.rerun()
