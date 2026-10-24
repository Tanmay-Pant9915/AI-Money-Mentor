"""
views/financial_planning_view.py
Streamlit UI view for the AI Financial Planning & Budgeting module.
Visualizes cash flow breakdowns, recommended budgets, interactive custom scenarios,
goal funding allocations, prioritized action checklists, and AI plan explanations.
"""
from datetime import datetime
from typing import Any, Dict, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.financial_planning_service import (
    generate_active_plan,
    get_latest_saved_plan,
    get_saved_plan_history,
    save_financial_plan,
)
from services.profile_service import format_inr, get_profile
from utils.ai_financial_planner import generate_plan_explanation


def render_financial_planning_view(
    user_id: str = "default_user",
    db_path: Optional[str] = None,
):
    """Render the primary Financial Planning & Budgeting dashboard."""
    st.header("📋 AI Financial Planning & Budgeting")
    st.caption(
        "Analyze where your money goes, establish sustainable budget allocations, "
        "and prioritize debt, emergency cushion, and milestone goals."
    )
    st.divider()

    # Verify existing profile
    profile = get_profile(user_id=user_id, db_path=db_path)
    if not profile or not profile.get("monthly_income"):
        _render_no_profile_state()
        return

    # Session state for interactive budget customization and AI explanation
    if "budget_custom_overrides" not in st.session_state:
        st.session_state.budget_custom_overrides = {}
    if "ai_plan_explanation" not in st.session_state:
        # Load from latest saved plan if available
        latest_saved = get_latest_saved_plan(user_id=user_id, db_path=db_path)
        st.session_state.ai_plan_explanation = latest_saved.get("ai_explanation") if latest_saved else None

    # Generate plan with any active overrides
    plan = generate_active_plan(
        user_id=user_id,
        custom_overrides=st.session_state.budget_custom_overrides,
        db_path=db_path,
    )

    summary = plan["summary"]
    budget = plan["budget"]
    adjusted_cats = plan["adjusted_categories"]
    actions = plan["actions"]
    goals_data = budget.get("goals_allocation", {})

    # Incomplete profile banner
    if summary.get("is_data_incomplete") and summary.get("missing_fields"):
        missing_str = ", ".join(summary["missing_fields"])
        col_w, col_b = st.columns([5, 1])
        with col_w:
            st.warning(
                f"⚠️ **Incomplete Profile Data:** The following fields are not recorded: **{missing_str}**. "
                "Current calculations and recommendations use provisional baselines. "
                "Complete your profile for precise financial figures."
            )
        with col_b:
            if st.button("✏️ Complete Profile", key="btn_complete_profile"):
                st.session_state["nav_override"] = "👤 Financial Profile"
                st.rerun()

    # Top action bar
    top_col1, top_col2, top_col3 = st.columns([5, 2, 2])
    with top_col2:
        if st.button("💾 Save Plan", type="primary", use_container_width=True):
            save_financial_plan(
                plan_data=plan,
                user_id=user_id,
                plan_name="Monthly Financial Plan",
                ai_explanation=st.session_state.ai_plan_explanation,
                db_path=db_path,
            )
            st.toast("✅ Financial Plan successfully saved!", icon="💾")
    with top_col3:
        if st.session_state.budget_custom_overrides:
            if st.button("🔄 Reset Custom", use_container_width=True):
                st.session_state.budget_custom_overrides = {}
                st.rerun()

    # 1. Financial Position Summary Cards
    _render_summary_metrics(summary)

    st.markdown("---")

    # 2. Expense Outflows Breakdown Chart & Table
    _render_outflows_breakdown(summary)

    st.markdown("---")

    # 3. Budget Scenarios: Current vs Recommended vs Custom Scenario
    _render_budget_comparison(budget, adjusted_cats, summary)

    st.markdown("---")

    # 4. Interactive Budget Simulator / Customizer
    _render_budget_customizer(summary, budget, adjusted_cats)

    st.markdown("---")

    # 5. Financial Goals Contribution Schedule
    _render_goals_allocation(goals_data)

    st.markdown("---")

    # 6. Emergency Fund Resilience
    _render_emergency_section(budget.get("emergency_allocation", {}), summary)

    st.markdown("---")

    # 7. Prioritized Financial Action Plan
    _render_action_plan(actions)

    st.markdown("---")

    # 8. AI-Powered Plan Explanation
    _render_ai_explanation_section(summary, budget, goals_data, actions)

    st.markdown("---")

    # 9. Saved Plans Audit History
    _render_plan_history(user_id=user_id, db_path=db_path)

    st.markdown("---")

    # 10. Educational Disclaimer
    st.info(
        "⚖️ **Educational Financial Notice:** This financial plan is an educational decision-support tool "
        "calculated using deterministic mathematical models. It does not constitute formal SEBI-regulated "
        "investment advice, legal counsel, or credit underwriting."
    )


def _render_summary_metrics(summary: Dict[str, Any]):
    """Render high-level cash flow summary metric cards."""
    st.subheader("💵 Monthly Cash Flow Snapshot")

    col1, col2, col3, col4, col5 = st.columns(5)
    surplus = summary["monthly_surplus"]
    is_deficit = summary["is_deficit"]

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Take-Home Income</div>
                <div class="metric-value">{format_inr(summary['monthly_income'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Total Outflows</div>
                <div class="metric-value" style="color: #f59e0b;">{format_inr(summary['total_monthly_outflows'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        surplus_color = "#ef4444" if is_deficit else "#10b981"
        surplus_label = "Monthly Deficit" if is_deficit else "Monthly Surplus"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{surplus_label}</div>
                <div class="metric-value" style="color: {surplus_color};">{format_inr(surplus)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        sr_val = summary.get("savings_rate", 0.0)
        sr_color = "#ef4444" if sr_val < 0 else "#f59e0b" if sr_val < 15 else "#10b981"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Savings Rate</div>
                <div class="metric-value" style="color: {sr_color};">{sr_val:.1f}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col5:
        dti_val = summary.get("debt_to_income", 0.0)
        dti_color = "#ef4444" if dti_val > 40 else "#f59e0b" if dti_val > 20 else "#10b981"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Debt-to-Income</div>
                <div class="metric-value" style="color: {dti_color};">{dti_val:.1f}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Clearly distinguish total debt vs monthly repayments
    out_debt = summary.get("outstanding_debt", 0.0)
    mo_debt = summary.get("monthly_debt_repayment", 0.0)
    if out_debt > 0 or mo_debt > 0:
        st.caption(
            f"💳 **Debt Obligations:** Total Outstanding Debt: **{format_inr(out_debt)}** | "
            f"Monthly Debt Servicing: **{format_inr(mo_debt)}/mo** (DTI: {dti_val:.1f}%)"
        )


def _render_outflows_breakdown(summary: Dict[str, Any]):
    """Render donut chart and table of current outflow allocations."""
    st.subheader("📊 Current Expense & Debt Breakdown")
    st.caption("All categories are non-overlapping. Contractual debt service is tracked distinctly from day-to-day living.")

    chart_col, table_col = st.columns([1, 1])

    breakdown = summary.get("breakdown", {})
    chart_data = [
        {"Category": name, "Amount": data["amount"], "Color": data["color"]}
        for name, data in breakdown.items()
        if data["amount"] > 0
    ]

    with chart_col:
        if chart_data and summary["total_monthly_outflows"] > 0:
            df_chart = pd.DataFrame(chart_data)
            fig = px.pie(
                df_chart,
                names="Category",
                values="Amount",
                hole=0.45,
                color="Category",
                color_discrete_map={row["Category"]: row["Color"] for row in chart_data},
            )
            fig.update_layout(
                margin=dict(t=20, b=20, l=10, r=10),
                height=280,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
                legend=dict(orientation="h", y=-0.1),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No recorded monthly outflows to display.")

    with table_col:
        table_rows = []
        for name, data in breakdown.items():
            table_rows.append({
                "Outflow Category": name,
                "Monthly Amount": format_inr(data["amount"]),
                "% of Total Outflows": f"{data['pct_of_outflows']:.1f}%",
                "% of Take-Home Pay": f"{data['pct_of_income']:.1f}%",
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)


def _render_budget_comparison(
    budget: Dict[str, Any],
    adjusted_cats: Dict[str, Dict[str, Any]],
    summary: Dict[str, Any],
):
    """Render Current vs Recommended budget scenario comparison table."""
    st.subheader("⚖️ Current vs Recommended Budget")
    st.caption(
        "Recommended budget preserves essential obligations and contractual debt service, "
        "while creating structured allocations for emergency liquidity and financial goals."
    )

    savings_imp = budget.get("potential_savings_improvement", 0.0)
    if savings_imp > 0:
        st.success(
            f"💡 **Potential Monthly Savings Improvement:** By following the recommended allocation, "
            f"you can unlock an additional **{format_inr(savings_imp)}/month** toward your wealth milestones."
        )

    rows = []
    for cat_name, data in adjusted_cats.items():
        curr = data.get("current", 0.0)
        rec = data.get("recommended", 0.0)
        adj = data.get("adjusted", rec)
        diff = adj - curr

        diff_str = f"+{format_inr(diff)}" if diff > 0 else f"-{format_inr(abs(diff))}" if diff < 0 else "₹0"
        rows.append({
            "Budget Category": cat_name,
            "Classification": data.get("type", "Allocation"),
            "Current Outflow": format_inr(curr),
            "Recommended": format_inr(rec),
            "Your Scenario": format_inr(adj),
            "Monthly Delta": diff_str,
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Budget notes
    notes = budget.get("notes", [])
    if notes:
        with st.expander("📝 Budget Algorithm Observations & Adjustments", expanded=False):
            for n in notes:
                st.markdown(f"- {n}")


def _render_budget_customizer(
    summary: Dict[str, Any],
    budget: Dict[str, Any],
    adjusted_cats: Dict[str, Any],
):
    """Interactive slider controls allowing users to simulate budget scenarios."""
    with st.expander("🛠️ Interactive Budget Simulator (Customize Your Scenario)", expanded=False):
        st.caption(
            "Experiment with your discretionary spending or goal contributions to see how your "
            "monthly surplus changes. Your adjustments remain in session state until you click **Save Plan**."
        )

        income = summary["monthly_income"]
        rec_disc = budget.get("recommended_categories", {}).get("Discretionary Living", {}).get("recommended", 0.0)
        curr_disc = adjusted_cats.get("Discretionary Living", {}).get("adjusted", rec_disc)

        max_disc_slider = max(50000.0, income * 0.70)
        new_disc = st.slider(
            "Discretionary Living Spending Target (₹/month):",
            min_value=0.0,
            max_value=float(max_disc_slider),
            value=float(curr_disc),
            step=1000.0,
            format="₹%d",
        )

        rec_emg = budget.get("emergency_allocation", {}).get("recommended_monthly", 0.0)
        curr_emg = adjusted_cats.get("Emergency Savings", {}).get("adjusted", rec_emg)
        new_emg = st.slider(
            "Emergency Savings Allocation (₹/month):",
            min_value=0.0,
            max_value=float(income * 0.50),
            value=float(curr_emg),
            step=1000.0,
            format="₹%d",
        )

        rec_goals = budget.get("recommended_categories", {}).get("Financial Goals", {}).get("recommended", 0.0)
        curr_goals = adjusted_cats.get("Financial Goals", {}).get("adjusted", rec_goals)
        max_goals_slider = max(50000.0, income * 0.50)
        new_goals = st.slider(
            "Milestone Financial Goals Allocation (₹/month):",
            min_value=0.0,
            max_value=float(max_goals_slider),
            value=float(curr_goals),
            step=1000.0,
            format="₹%d",
        )

        if (
            new_disc != curr_disc
            or new_emg != curr_emg
            or new_goals != curr_goals
            or "Discretionary Living" not in st.session_state.budget_custom_overrides
        ):
            if st.button("Apply Custom Scenario", type="secondary"):
                st.session_state.budget_custom_overrides = {
                    "Discretionary Living": new_disc,
                    "Emergency Savings": new_emg,
                    "Financial Goals": new_goals,
                }
                st.rerun()


def _render_goals_allocation(goals_data: Dict[str, Any]):
    """Render financial goals contribution plan."""
    st.subheader("🎯 Milestone Financial Goals Allocation")
    st.caption("Required monthly contributions calculated deterministically to meet your target date without relying on speculative returns.")

    if not goals_data.get("has_goals"):
        st.info("ℹ️ No financial goals configured. Add goals in your **Financial Profile** to track funding progress.")
        return

    goals_detail = goals_data.get("goals_detail", [])
    table_rows = []
    for g in goals_detail:
        table_rows.append({
            "Goal Name": g["name"],
            "Target Amount": format_inr(g["target_amount"]),
            "Current Saved": format_inr(g["current_amount"]),
            "Remaining Amount": format_inr(g["remaining_amount"]),
            "Months Left": f"{g['remaining_months']} mo" if g["remaining_months"] > 0 else "Due / Expired",
            "Required / Month": format_inr(g["required_monthly"]),
            "Allocated / Month": format_inr(g["allocated_monthly"]),
            "Status": g["status"],
        })

    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    if not goals_data.get("is_fully_funded"):
        st.warning(
            f"⚠️ **Goal Shortfall:** Total requested goal contributions exceed your affordable surplus by "
            f"**{format_inr(goals_data.get('surplus_shortfall', 0))}/month**. Available funds have been pro-rated."
        )
    else:
        st.success("✅ **All Milestone Goals Fully Funded:** Your monthly surplus comfortably covers required goal contributions.")


def _render_emergency_section(emergency_data: Dict[str, Any], summary: Dict[str, Any]):
    """Render emergency fund status and savings recommendation."""
    st.subheader("🛡️ Emergency Fund Cushion & Runway")

    if emergency_data.get("is_provisional"):
        st.info(
            "ℹ️ **Provisional Recommendation:** Liquid savings data is unrecorded in your profile. "
            "The runway coverage and allocation figures below assume a provisional starting point."
        )

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Liquid Savings", format_inr(emergency_data.get("current_liquid", 0.0)))
    with col2:
        st.metric("Essential Needs", f"{format_inr(summary.get('essential_expenses', 0.0))}/mo")
    with col3:
        cov = emergency_data.get("coverage_months", 0.0)
        cov_color = "🔴" if cov < 1 else "🟡" if cov < 3 else "🟢"
        st.metric("Runway Coverage", f"{cov:.1f} Months", delta=f"{cov_color} Target: 3-6 Mo")
    with col4:
        st.metric("Shortfall to Target", format_inr(emergency_data.get("shortfall", 0.0)))
    with col5:
        st.metric("Recommended Allocation", f"{format_inr(emergency_data.get('recommended_monthly', 0.0))}/mo")


def _render_action_plan(actions: list):
    """Render prioritized financial action plan."""
    st.subheader("🚀 Prioritized Financial Action Plan")
    st.caption("Ordered strictly by financial urgency: Solvency → Obligations → Emergency Liquidity → Debt Freedom → Goals.")

    if not actions:
        st.success("🎉 All financial pillars in top tier! Maintain your current automated plan.")
        return

    for item in actions:
        prio = item.get("priority", "Medium")
        prio_color = "#ef4444" if prio == "High" else "#f59e0b" if prio == "Medium" else "#3b82f6"

        with st.container(border=True):
            head_col, badge_col = st.columns([5, 1])
            with head_col:
                st.markdown(f"**{item.get('title')}** `({item.get('category')})`")
            with badge_col:
                st.markdown(
                    f"<span style='color: {prio_color}; font-weight: 700; border: 1px solid {prio_color}; "
                    f"padding: 2px 8px; border-radius: 4px; font-size: 0.8rem;'>{prio} Priority</span>",
                    unsafe_allow_html=True,
                )
            st.write(item.get("action"))
            st.caption(f"**Why this matters:** {item.get('rationale')}")


def _render_ai_explanation_section(
    summary: Dict[str, Any],
    budget: Dict[str, Any],
    goals_data: Dict[str, Any],
    actions: list,
):
    """Render optional AI plan explanation."""
    st.subheader("🤖 AI Financial Mentor Explanation")
    st.caption("Plain-English narrative analyzing your cash flow and explaining the rationale behind your budget plan.")

    btn_col, _ = st.columns([2, 5])
    with btn_col:
        gen_clicked = st.button("✨ Generate AI Explanation", use_container_width=True)

    if gen_clicked:
        with st.spinner("Consulting AI Financial Mentor..."):
            explanation = generate_plan_explanation(summary, budget, goals_data, actions)
            st.session_state.ai_plan_explanation = explanation

    if st.session_state.ai_plan_explanation:
        with st.container(border=True):
            st.markdown(st.session_state.ai_plan_explanation)
    else:
        st.info("Click **Generate AI Explanation** above to receive a structured plain-English briefing from your AI Money Mentor.")


def _render_plan_history(user_id: str, db_path: Optional[str] = None):
    """Render historical saved financial plans."""
    with st.expander("📜 Saved Financial Plans History", expanded=False):
        history = get_saved_plan_history(user_id=user_id, db_path=db_path)
        if not history:
            st.info("No saved financial plans recorded yet. Click **Save Plan** to preserve your current plan snapshot.")
            return

        rows = []
        for h in history:
            date_raw = h.get("created_at", "")
            try:
                date_str = datetime.fromisoformat(date_raw).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                date_str = date_raw

            rows.append({
                "Plan ID": h["id"],
                "Plan Name": h.get("plan_name", "Monthly Financial Plan"),
                "Saved On": date_str,
                "Is Latest": "✅ Yes" if h.get("is_latest") == 1 else "No",
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_no_profile_state():
    """State displayed when no financial profile is found in database."""
    st.warning("⚠️ **Financial Profile Required**")
    st.write(
        "To build your personalized financial plan and budget, you first need to record your "
        "monthly income, essential living expenses, and debt details in your Financial Profile."
    )
    if st.button("🚀 Set Up Financial Profile Now", type="primary"):
        st.session_state["nav_override"] = "👤 Financial Profile"
        st.rerun()
