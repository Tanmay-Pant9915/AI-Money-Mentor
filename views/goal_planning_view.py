"""
views/goal_planning_view.py
Streamlit UI view for Goal-Based Investment Planning & Investment Suggestions.
Visualizes goal feasibility, portfolio-level surplus allocation, deterministic
compound growth projections, risk-aware asset class allocations, and interactive
what-if scenario analysis without modifying saved data until explicitly confirmed.
"""
from datetime import date, datetime
import math
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.financial_planning_service import generate_active_plan
from services.goal_planning_service import (
    create_goal,
    delete_goal,
    evaluate_goal_planning_overview,
    get_goal_by_id,
    get_user_goals,
    mark_goal_completed,
    update_goal,
)
from services.profile_service import format_inr, get_profile
from utils.goal_allocation import ASSET_CLASSES
from utils.goal_calculator import GOAL_CATEGORIES, GOAL_PRIORITIES
from utils.investment_projection import (
    calculate_required_contribution_for_target,
    project_investment_growth,
)


CATEGORY_ICONS = {
    "Education": "🎓",
    "Vehicle": "🚗",
    "Home purchase": "🏠",
    "Wedding": "💍",
    "Emergency savings": "🛡️",
    "Retirement": "🏖️",
    "Other": "🎯",
}

PRIORITY_COLORS = {
    "High": "🔴",
    "Medium": "🟡",
    "Low": "🟢",
}


def render_goal_planning_view(
    user_id: str = "default_user",
    db_path: Optional[str] = None,
):
    """Render the primary Goal-Based Investment Planning dashboard."""
    st.header("🎯 Goal-Based Investment Planning & Investment Suggestions")
    st.caption(
        "Plan your financial milestones with deterministic math, evaluate monthly budget affordability, "
        "and receive educational category-level asset allocations aligned with your time horizon and risk profile."
    )

    # Educational Disclaimer Banner
    st.info(
        "ℹ️ **Educational Financial Planning Prototype:** All calculations, required contributions, "
        "and compound projections are deterministic mathematical evaluations. Category allocations are illustrative "
        "and based on standard financial planning frameworks. This is not a regulated SEBI investment advisory service."
    )
    st.divider()

    # Session state initialization for what-if scenarios and editing
    if "goal_scenario_goal_id" not in st.session_state:
        st.session_state.goal_scenario_goal_id = None
    if "goal_editing_id" not in st.session_state:
        st.session_state.goal_editing_id = None
    if "delete_confirm_id" not in st.session_state:
        st.session_state.delete_confirm_id = None

    # Load evaluated overview
    overview = evaluate_goal_planning_overview(user_id=user_id, db_path=db_path)
    goals = overview["goals"]
    summary = overview["portfolio_summary"]
    alerts = overview["portfolio_alerts"]
    surplus = overview["available_monthly_surplus"]
    has_surplus = overview["has_surplus_data"]

    # 1. TOP-LEVEL METRICS CARDS
    _render_portfolio_summary_cards(summary, surplus, has_surplus)

    # 2. PORTFOLIO ALERTS
    if alerts:
        _render_portfolio_alerts(alerts)

    st.markdown("---")

    # 3. MAIN TABS
    tab_dashboard, tab_scenario, tab_add_goal, tab_portfolio_view = st.tabs(
        [
            "🎯 Active Goals & Allocations",
            "🔬 What-If Scenario Simulator",
            "➕ Add New Goal",
            "📊 Portfolio Overview & Cash Flow",
        ]
    )

    with tab_dashboard:
        _render_goals_dashboard(goals, user_id=user_id, db_path=db_path)

    with tab_scenario:
        _render_scenario_simulator(goals, user_id=user_id, db_path=db_path)

    with tab_add_goal:
        _render_add_goal_form(user_id=user_id, db_path=db_path)

    with tab_portfolio_view:
        _render_portfolio_analytics(goals, summary, surplus)


def _render_portfolio_summary_cards(
    summary: Dict[str, Any], surplus: Optional[float], has_surplus: bool
):
    """Render top-level executive metrics cards."""
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Active Goals</div>
                <div class="metric-value">{summary.get('active_goals_count', 0)}</div>
                <div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">{summary.get('completed_goals_count', 0)} completed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Total Remaining Target</div>
                <div class="metric-value">{format_inr(summary.get('total_remaining_amount', 0.0))}</div>
                <div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">Target: {format_inr(summary.get('total_target_amount', 0.0))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Required Monthly (0% Return)</div>
                <div class="metric-value">{format_inr(summary.get('total_required_monthly', 0.0))}</div>
                <div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">Combined baseline need</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        surplus_val_str = format_inr(surplus) if has_surplus and surplus is not None else "Not Set"
        surplus_color = "#10b981" if (surplus or 0) >= 0 else "#ef4444"
        surplus_sub = "Monthly cash flow surplus" if has_surplus else "Complete profile / budget"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Available Surplus</div>
                <div class="metric-value" style="color:{surplus_color};">{surplus_val_str}</div>
                <div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">{surplus_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col5:
        afford_status = summary.get("affordability_status", "Unknown")
        afford_count = summary.get("affordable_goals_count", 0)
        active_count = summary.get("active_goals_count", 0)
        afford_color = "#10b981" if afford_status == "Fully Affordable" else ("#f59e0b" if afford_status == "Partially Affordable" else "#ef4444")
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Affordability</div>
                <div class="metric-value" style="color:{afford_color}; font-size:1.35rem;">{afford_status}</div>
                <div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">{afford_count} of {active_count} goals funded</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_portfolio_alerts(alerts: List[Dict[str, str]]):
    """Display prioritized warnings and alerts generated deterministically."""
    for alert in alerts:
        severity = alert.get("severity") or alert.get("level") or "info"
        title = alert.get("title")
        msg = alert.get("message", "")
        display = f"**{title}:** {msg}" if title else msg
        if severity in ["critical", "error"]:
            st.error(f"🚨 {display}")
        elif severity == "warning":
            st.warning(f"⚠️ {display}")
        elif severity == "success":
            st.success(f"✅ {display}")
        else:
            st.info(f"💡 {display}")



def _render_goals_dashboard(
    goals: List[Dict[str, Any]], user_id: str = "default_user", db_path: Optional[str] = None
):
    """Render list of goals with detailed feasibility, projection, and allocation cards."""
    if not goals:
        st.info("👋 You don't have any financial goals saved yet. Click the **➕ Add New Goal** tab above to create your first goal!")
        return

    # Filter toggles
    col_f1, col_f2 = st.columns([3, 1])
    with col_f1:
        st.subheader("Your Financial Goals")
    with col_f2:
        show_completed = st.checkbox("Show Completed Goals", value=True)

    filtered_goals = [g for g in goals if show_completed or not g.get("is_completed")]

    for g in filtered_goals:
        _render_individual_goal_card(g, user_id=user_id, db_path=db_path)


def _render_individual_goal_card(
    g: Dict[str, Any], user_id: str = "default_user", db_path: Optional[str] = None
):
    """Render an individual interactive card for a single goal."""
    g_id = g.get("id")
    name = g.get("name", "Unnamed Goal")
    category = g.get("category", "Other")
    cat_icon = CATEGORY_ICONS.get(category, "🎯")
    priority = g.get("priority", "Medium")
    p_icon = PRIORITY_COLORS.get(priority, "🟡")
    is_completed = bool(g.get("is_completed"))

    target_amt = float(g.get("target_amount", 0.0))
    current_amt = float(g.get("current_amount", 0.0))
    rem_amt = float(g.get("remaining_amount", 0.0))
    rem_months = int(g.get("remaining_months", 0))
    target_date_str = str(g.get("target_date", ""))
    pct_saved = min(100.0, (current_amt / target_amt * 100)) if target_amt > 0 else 0.0

    status = g.get("status", "In Progress")
    req_monthly = float(g.get("required_monthly", 0.0))
    planned_monthly = float(g.get("monthly_planned", 0.0))
    allocated_surplus = float(g.get("allocated_from_surplus", 0.0))
    assumed_r = float(g.get("assumed_annual_return", 8.0))
    proj_fv = float(g.get("projected_future_value", 0.0))
    proj = g.get("projection", {})
    alloc = g.get("asset_allocation", {})

    status_tag = "✅ Completed" if is_completed else (f"⚠️ {status}" if status != "In Progress" else "Active")

    with st.expander(f"{cat_icon} **{name}** — {format_inr(target_amt)} by {target_date_str} [{p_icon} {priority} Priority] ({status_tag})", expanded=(not is_completed)):
        # Edit Form if this goal is being edited
        if st.session_state.goal_editing_id == g_id:
            _render_edit_goal_inline(g, user_id=user_id, db_path=db_path)
            return

        # Main Info Columns
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Target Amount", format_inr(target_amt))
        c2.metric("Saved So Far", format_inr(current_amt), delta=f"{pct_saved:.1f}% reached")
        c3.metric("Remaining Needed", format_inr(rem_amt))
        c4.metric(
            "Time Remaining",
            f"{rem_months} Months" if rem_months > 0 else "Due / Expired",
            delta=f"{rem_months/12:.1f} Yrs" if rem_months > 0 else None,
        )

        st.progress(pct_saved / 100.0)

        # Contribution Feasibility & Affordability Breakdown
        st.markdown("##### 💵 Monthly Contribution & Budget Affordability")
        cf1, cf2, cf3, cf4 = st.columns(4)
        cf1.metric("Required Monthly (0% Return)", format_inr(req_monthly), help="Baseline required monthly savings assuming zero investment returns.")
        cf2.metric("Your Planned Monthly SIP", format_inr(planned_monthly), help="Amount you planned to invest monthly for this goal.")
        cf3.metric("Allocated from Surplus", format_inr(allocated_surplus), help="Surplus allocated to this goal based on priority order.")
        
        afford_badge = g.get("affordability", "Unknown")
        cf4.metric("Goal Affordability", afford_badge)

        # Investment Growth Projection Section
        st.markdown("---")
        st.markdown(f"##### 📈 Deterministic Investment Growth Projection (Assumed Return: **{assumed_r:.1f}% p.a.**)")
        
        pj1, pj2, pj3, pj4 = st.columns(4)
        pj1.metric("Projected Corpus (FV)", format_inr(proj_fv))
        pj2.metric("Principal Invested", format_inr(proj.get("total_principal_invested", 0.0)))
        pj3.metric("Projected Compound Growth", format_inr(proj.get("projected_growth", 0.0)))
        pj4.metric("0% Return Baseline", format_inr(proj.get("baseline_no_return_fv", 0.0)), help="Corpus if savings earn no return.")

        # Comparison Chart: Current vs Principal vs Growth vs Target
        fig_proj = _create_projection_chart(target_amt, current_amt, proj)
        st.plotly_chart(fig_proj, use_container_width=True)

        # Asset Allocation Section
        st.markdown("---")
        st.markdown(f"##### 🛡️ Educational Category-Level Asset Allocation ({alloc.get('horizon_category', '')})")
        if alloc.get("guardrails_applied"):
            for g_note in alloc["guardrails_applied"]:
                st.caption(f"🛡️ **Protective Guardrail Applied:** {g_note}")

        col_pie, col_tbl = st.columns([1, 1])
        with col_pie:
            fig_alloc = _create_allocation_donut(alloc.get("allocations", {}))
            st.plotly_chart(fig_alloc, use_container_width=True)
        with col_tbl:
            _render_allocation_table(alloc.get("allocations", {}))

        # Alerts & Assumptions
        if g.get("alerts"):
            for alt in g["alerts"]:
                sev = alt.get("severity") or alt.get("level") or "info"
                m = alt.get("message", "")
                t = alt.get("title")
                disp = f"**{t}:** {m}" if t else m
                if sev in ["critical", "error"]:
                    st.error(f"🚨 {disp}")
                elif sev == "warning":
                    st.warning(f"⚠️ {disp}")
                elif sev == "success":
                    st.success(f"✅ {disp}")
                else:
                    st.info(f"💡 {disp}")

        if g.get("assumptions"):
            with st.expander("ℹ️ Calculation Assumptions & Disclaimers", expanded=False):
                for asmp in g["assumptions"]:
                    st.markdown(f"- {asmp}")
                if proj.get("assumptions_disclaimer"):
                    st.caption(f"**Disclaimer:** {proj['assumptions_disclaimer']}")

        # Action Buttons
        st.markdown("---")
        act_col1, act_col2, act_col3, act_col4 = st.columns([2, 2, 2, 2])
        with act_col1:
            toggle_label = "↩️ Re-open Goal" if is_completed else "✅ Mark Completed"
            if st.button(toggle_label, key=f"btn_complete_{g_id}"):
                mark_goal_completed(g_id, not is_completed, user_id=user_id, db_path=db_path)
                st.rerun()

        with act_col2:
            if st.button("✏️ Edit Goal", key=f"btn_edit_{g_id}"):
                st.session_state.goal_editing_id = g_id
                st.rerun()

        with act_col3:
            if st.button("🔬 What-If Scenario", key=f"btn_whatif_{g_id}"):
                st.session_state.goal_scenario_goal_id = g_id
                st.session_state["nav_scenario_tab"] = True
                st.rerun()

        with act_col4:
            if st.session_state.delete_confirm_id == g_id:
                c_del1, c_del2 = st.columns(2)
                with c_del1:
                    if st.button("⚠️ Confirm Delete", key=f"btn_confirm_del_{g_id}"):
                        delete_goal(g_id, user_id=user_id, db_path=db_path)
                        st.session_state.delete_confirm_id = None
                        st.success("Goal deleted.")
                        st.rerun()
                with c_del2:
                    if st.button("Cancel", key=f"btn_cancel_del_{g_id}"):
                        st.session_state.delete_confirm_id = None
                        st.rerun()
            else:
                if st.button("🗑️ Delete Goal", key=f"btn_del_{g_id}"):
                    st.session_state.delete_confirm_id = g_id
                    st.rerun()


def _render_edit_goal_inline(
    g: Dict[str, Any], user_id: str = "default_user", db_path: Optional[str] = None
):
    """Render inline editing form for an existing goal."""
    g_id = g.get("id")
    st.markdown("#### ✏️ Edit Goal Details")
    with st.form(key=f"form_edit_goal_{g_id}"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Goal Name", value=g.get("name", ""))
            category = st.selectbox(
                "Category",
                GOAL_CATEGORIES,
                index=GOAL_CATEGORIES.index(g.get("category", "Other")) if g.get("category") in GOAL_CATEGORIES else 0,
            )
            priority = st.selectbox(
                "Priority Level",
                GOAL_PRIORITIES,
                index=GOAL_PRIORITIES.index(g.get("priority", "Medium")) if g.get("priority") in GOAL_PRIORITIES else 1,
            )
        with col2:
            target_amt = st.number_input(
                "Target Amount (₹)", min_value=1000.0, value=float(g.get("target_amount", 100000.0)), step=10000.0
            )
            cur_date_val = date.today()
            try:
                cur_date_val = datetime.strptime(str(g.get("target_date", "")), "%Y-%m-%d").date()
            except Exception:
                pass
            target_date = st.date_input("Target Date", value=cur_date_val)
            current_amt = st.number_input(
                "Current Amount Saved (₹)", min_value=0.0, value=float(g.get("current_amount", 0.0)), step=5000.0
            )
            monthly_contrib = st.number_input(
                "Monthly Planned SIP (₹)", min_value=0.0, value=float(g.get("monthly_contribution", 0.0)), step=1000.0
            )

        col_save, col_cancel = st.columns([1, 1])
        with col_save:
            submit = st.form_submit_button("💾 Save Changes")
        with col_cancel:
            cancel = st.form_submit_button("❌ Cancel")

    if cancel:
        st.session_state.goal_editing_id = None
        st.rerun()

    if submit:
        update_data = {
            "name": name,
            "category": category,
            "target_amount": target_amt,
            "target_date": target_date.strftime("%Y-%m-%d"),
            "current_amount": current_amt,
            "monthly_contribution": monthly_contrib,
            "priority": priority,
            "is_completed": g.get("is_completed", False),
        }
        success, _, errors = update_goal(g_id, update_data, user_id=user_id, db_path=db_path)
        if success:
            st.success("Goal successfully updated!")
            st.session_state.goal_editing_id = None
            st.rerun()
        else:
            for err in errors:
                st.error(f"⚠️ {err}")


def _render_add_goal_form(user_id: str = "default_user", db_path: Optional[str] = None):
    """Form to create a new financial goal."""
    st.subheader("➕ Create a New Financial Goal")
    st.caption("Define your target amount, date, and savings to track feasibility and calculate SIP requirements.")

    with st.form(key="form_add_new_goal"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Goal Name (e.g. Dream House Down Payment, MBA Fund)", placeholder="e.g. New Car Purchase")
            category = st.selectbox("Category", GOAL_CATEGORIES, index=1)
            priority = st.selectbox("Priority Level", GOAL_PRIORITIES, index=1, help="High priority goals get funding precedence from monthly surplus.")
        with col2:
            target_amount = st.number_input("Target Amount (INR)", min_value=1000.0, value=200000.0, step=10000.0)
            default_target_date = date.today().replace(year=date.today().year + 3)
            target_date = st.date_input("Target Date", value=default_target_date)
            current_amount = st.number_input("Current Amount Saved (INR)", min_value=0.0, value=25000.0, step=5000.0)
            monthly_contrib = st.number_input("Planned Monthly SIP (INR)", min_value=0.0, value=5000.0, step=1000.0)

        submit = st.form_submit_button("🚀 Add Financial Goal")

    if submit:
        goal_payload = {
            "name": name,
            "category": category,
            "target_amount": target_amount,
            "target_date": target_date.strftime("%Y-%m-%d"),
            "current_amount": current_amount,
            "monthly_contribution": monthly_contrib,
            "priority": priority,
        }
        success, _, errors = create_goal(goal_payload, user_id=user_id, db_path=db_path)
        if success:
            st.success(f"🎉 Goal '{name}' created successfully! View it in the Active Goals tab.")
            st.rerun()
        else:
            for err in errors:
                st.error(f"⚠️ {err}")


def _render_scenario_simulator(
    goals: List[Dict[str, Any]], user_id: str = "default_user", db_path: Optional[str] = None
):
    """Interactive What-If Scenario Simulator."""
    st.subheader("🔬 Interactive What-If Scenario Analysis")
    st.caption(
        "Simulate changes to your monthly SIP, target date, or expected market returns in real-time. "
        "Test feasibility without altering your saved profile until you explicitly choose to save."
    )

    if not goals:
        st.info("No active goals available for simulation. Please create a goal first.")
        return

    # Select goal
    goal_names = {g["id"]: f"{g.get('name', 'Goal')} ({format_inr(g.get('target_amount', 0))})" for g in goals}
    default_id = st.session_state.goal_scenario_goal_id or goals[0]["id"]
    if default_id not in goal_names:
        default_id = goals[0]["id"]

    selected_id = st.selectbox(
        "Select Goal to Simulate",
        options=list(goal_names.keys()),
        format_func=lambda x: goal_names[x],
        index=list(goal_names.keys()).index(default_id),
    )

    # Get baseline saved goal data
    base_goal = next((g for g in goals if g["id"] == selected_id), None)
    if not base_goal:
        return

    st.markdown("---")

    # Scenario Controls
    c_ctrl1, c_ctrl2 = st.columns(2)
    with c_ctrl1:
        st.markdown("##### 🎛️ Scenario Adjustments")
        sc_target_amt = st.number_input(
            "Target Amount (₹)",
            min_value=1000.0,
            value=float(base_goal.get("target_amount", 100000.0)),
            step=10000.0,
            key=f"sc_target_{selected_id}",
        )
        sc_cur_amt = st.number_input(
            "Current Savings (₹)",
            min_value=0.0,
            value=float(base_goal.get("current_amount", 0.0)),
            step=5000.0,
            key=f"sc_cur_{selected_id}",
        )
        sc_contrib = st.slider(
            "Monthly Contribution / SIP (₹)",
            min_value=0,
            max_value=int(max(50000, base_goal.get("monthly_planned", 0) * 3)),
            value=int(base_goal.get("monthly_planned", 0) or base_goal.get("required_monthly", 5000)),
            step=500,
            key=f"sc_contrib_{selected_id}",
        )
        sc_months = st.slider(
            "Investment Horizon (Months)",
            min_value=1,
            max_value=360,
            value=max(1, int(base_goal.get("remaining_months", 36))),
            step=1,
            key=f"sc_months_{selected_id}",
        )
        sc_priority = st.selectbox(
            "Goal Priority Level",
            GOAL_PRIORITIES,
            index=GOAL_PRIORITIES.index(base_goal.get("priority", "Medium")) if base_goal.get("priority") in GOAL_PRIORITIES else 1,
            key=f"sc_priority_{selected_id}",
        )

    with c_ctrl2:
        st.markdown("##### 📈 Return & Inflation Assumptions")
        sc_return = st.slider(
            "Assumed Annual Rate of Return (%)",
            min_value=-5.0,
            max_value=20.0,
            value=float(base_goal.get("assumed_annual_return", 8.0)),
            step=0.5,
            key=f"sc_return_{selected_id}",
        )
        sc_timing = st.selectbox(
            "Contribution Timing",
            ["End of Month (Standard SIP)", "Beginning of Month (Advance SIP)"],
            index=0,
            key=f"sc_timing_{selected_id}",
        )
        timing_key = "beginning_of_period" if "Beginning" in sc_timing else "end_of_period"
        sc_inflation = st.slider(
            "Expected Annual Inflation (%)",
            min_value=0.0,
            max_value=12.0,
            value=0.0,
            step=0.5,
            help="Deflates the projected future value to show real purchasing power in today's rupees.",
            key=f"sc_inf_{selected_id}",
        )

    # Calculate deterministic scenario projection
    sc_proj = project_investment_growth(
        current_savings=sc_cur_amt,
        monthly_contribution=sc_contrib,
        remaining_months=sc_months,
        assumed_annual_return=sc_return,
        contribution_timing=timing_key,
        annual_inflation_rate=sc_inflation,
    )

    sc_growth_calc = calculate_required_contribution_for_target(
        target_amount=sc_target_amt,
        current_savings=sc_cur_amt,
        remaining_months=sc_months,
        assumed_annual_return=sc_return,
        contribution_timing=timing_key,
    )
    sc_growth_req = sc_growth_calc["required_monthly_contribution"]
    sc_baseline_req = round(max(0.0, (sc_target_amt - sc_cur_amt) / max(1, sc_months)), 2)

    sc_fv = sc_proj["future_value"]
    sc_baseline_fv = sc_proj["baseline_no_return_fv"]
    sc_diff_vs_target = sc_fv - sc_target_amt
    sc_is_achieved = sc_diff_vs_target >= 0

    st.markdown("---")
    st.markdown("##### ⚖️ Side-by-Side Comparison: Saved Plan vs What-If Scenario")

    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric(
            "Projected Corpus (FV)",
            format_inr(sc_fv),
            delta=f"{format_inr(sc_fv - base_goal.get('projected_future_value', 0))} vs saved",
        )
    with m_col2:
        delta_str = f"+{format_inr(sc_diff_vs_target)} Surplus" if sc_is_achieved else f"-{format_inr(abs(sc_diff_vs_target))} Shortfall"
        st.metric(
            "Corpus vs Target",
            "✅ Target Reached" if sc_is_achieved else "⚠️ Shortfall",
            delta=delta_str,
            delta_color="normal" if sc_is_achieved else "inverse",
        )
    with m_col3:
        st.metric("Total Principal Paid", format_inr(sc_proj["total_principal_invested"]))

    m_col4, m_col5, m_col6 = st.columns(3)
    with m_col4:
        st.metric("Compound Growth Generated", format_inr(sc_proj["projected_growth"]))
    with m_col5:
        st.metric(
            "Req. Monthly (0% Baseline)",
            format_inr(sc_baseline_req),
            help="Monthly savings required with zero investment returns.",
        )
    with m_col6:
        st.metric(
            f"Req. Monthly ({sc_return:.1f}% Return)",
            format_inr(sc_growth_req),
            help=f"Monthly SIP required assuming {sc_return:.1f}% annual return.",
        )

    # Scenario Comparison Chart
    fig_sc = go.Figure()
    fig_sc.add_trace(go.Bar(
        name="Target Amount",
        x=["Saved Goal", "What-If Scenario"],
        y=[base_goal.get("target_amount", 0), sc_target_amt],
        marker_color="#94a3b8",
    ))
    fig_sc.add_trace(go.Bar(
        name="Principal Invested",
        x=["Saved Goal", "What-If Scenario"],
        y=[base_goal.get("projection", {}).get("total_principal_invested", 0), sc_proj["total_principal_invested"]],
        marker_color="#3b82f6",
    ))
    fig_sc.add_trace(go.Bar(
        name="Projected Future Value",
        x=["Saved Goal", "What-If Scenario"],
        y=[base_goal.get("projected_future_value", 0), sc_fv],
        marker_color="#10b981",
    ))
    fig_sc.update_layout(
        barmode="group",
        title="Saved Plan vs What-If Scenario Comparison (INR)",
        yaxis_title="Amount (₹)",
        template="plotly_white",
        height=380,
    )
    st.plotly_chart(fig_sc, use_container_width=True)

    # Action controls: Reset vs Save
    col_sc_act1, col_sc_act2, _ = st.columns([2, 2, 4])
    with col_sc_act1:
        if st.button("🔄 Reset to Saved Profile", key="btn_reset_scenario"):
            for k in [
                f"sc_target_{selected_id}",
                f"sc_cur_{selected_id}",
                f"sc_contrib_{selected_id}",
                f"sc_months_{selected_id}",
                f"sc_priority_{selected_id}",
                f"sc_return_{selected_id}",
                f"sc_timing_{selected_id}",
                f"sc_inf_{selected_id}",
            ]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    with col_sc_act2:
        if st.button("💾 Save Scenario to Goal", key="btn_apply_scenario"):
            # Update target date based on months
            new_target_year = date.today().year + (date.today().month + sc_months - 1) // 12
            new_target_month = (date.today().month + sc_months - 1) % 12 + 1
            new_date = date(new_target_year, new_target_month, min(28, date.today().day)).strftime("%Y-%m-%d")

            update_data = {
                "name": base_goal.get("name", "Goal"),
                "category": base_goal.get("category", "Other"),
                "target_amount": sc_target_amt,
                "target_date": new_date,
                "current_amount": sc_cur_amt,
                "monthly_contribution": sc_contrib,
                "priority": sc_priority,
                "is_completed": base_goal.get("is_completed", False),
            }
            succ, _, errs = update_goal(selected_id, update_data, user_id=user_id, db_path=db_path)
            if succ:
                st.success("🎉 Scenario successfully saved to your financial goal!")
                st.rerun()
            else:
                for e in errs:
                    st.error(e)


def _render_portfolio_analytics(
    goals: List[Dict[str, Any]], summary: Dict[str, Any], surplus: Optional[float]
):
    """Render cross-goal portfolio charts and cash-flow impact."""
    st.subheader("📊 Portfolio Overview & Cash Flow Impact")

    if not goals:
        st.info("No goals available for portfolio analytics.")
        return

    # Chart 1: Target vs Saved vs Projected across all goals
    df_goals = pd.DataFrame(
        [
            {
                "Goal": g.get("name", "Goal"),
                "Target": g.get("target_amount", 0.0),
                "Saved": g.get("current_amount", 0.0),
                "Projected FV": g.get("projected_future_value", 0.0),
                "Required Monthly": g.get("required_monthly", 0.0),
            }
            for g in goals
        ]
    )

    fig_overview = px.bar(
        df_goals,
        x="Goal",
        y=["Saved", "Projected FV", "Target"],
        barmode="group",
        title="Goal Target vs Saved vs Projected Future Value",
        color_discrete_map={"Saved": "#3b82f6", "Projected FV": "#10b981", "Target": "#94a3b8"},
        height=400,
    )
    st.plotly_chart(fig_overview, use_container_width=True)

    # Monthly Cash Flow Comparison: Surplus vs Total Required Monthly
    st.markdown("##### 💵 Monthly Cash-Flow Surplus vs Total Goal Contributions")
    total_req = summary.get("total_required_monthly", 0.0)
    surplus_val = surplus if surplus is not None else 0.0

    fig_cf = go.Figure()
    fig_cf.add_trace(go.Bar(
        name="Available Monthly Surplus",
        x=["Monthly Cash Flow"],
        y=[surplus_val],
        marker_color="#10b981" if surplus_val >= total_req else "#ef4444",
    ))
    fig_cf.add_trace(go.Bar(
        name="Combined Required Monthly Contribution",
        x=["Monthly Cash Flow"],
        y=[total_req],
        marker_color="#6366f1",
    ))
    fig_cf.update_layout(
        barmode="group",
        title="Available Monthly Surplus vs Required Contributions (0% Baseline)",
        yaxis_title="Amount (₹)",
        height=350,
    )
    st.plotly_chart(fig_cf, use_container_width=True)


def _create_projection_chart(target_amt: float, current_amt: float, proj: Dict[str, Any]) -> go.Figure:
    """Create a breakdown bar chart of Current + New Contributions + Growth vs Target."""
    pv = float(proj.get("fv_current_savings", current_amt))
    contrib_prin = float(proj.get("total_contributions_paid", 0.0))
    growth = float(proj.get("projected_growth", 0.0))
    fv = float(proj.get("future_value", current_amt))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Current Savings",
        x=["Projected Corpus"],
        y=[pv],
        marker_color="#3b82f6",
    ))
    fig.add_trace(go.Bar(
        name="New Monthly SIPs",
        x=["Projected Corpus"],
        y=[contrib_prin],
        marker_color="#60a5fa",
    ))
    fig.add_trace(go.Bar(
        name="Compound Growth",
        x=["Projected Corpus"],
        y=[growth],
        marker_color="#10b981",
    ))
    fig.add_trace(go.Bar(
        name="Target Amount",
        x=["Target Benchmark"],
        y=[target_amt],
        marker_color="#94a3b8",
    ))

    fig.update_layout(
        barmode="stack",
        title="Projected Value Breakdown vs Goal Target",
        yaxis_title="Amount in INR (₹)",
        height=320,
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def _create_allocation_donut(alloc_dict: Dict[str, Any]) -> go.Figure:
    """Create a donut chart for educational category asset allocation."""
    labels = []
    values = []
    colors = ["#10b981", "#3b82f6", "#6366f1", "#f59e0b", "#ec4899"]

    for item in ASSET_CLASSES:
        k = item["key"]
        pct = alloc_dict.get(k, {}).get("percentage", 0.0)
        if pct > 0:
            labels.append(item["name"])
            values.append(pct)

    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.55, marker_colors=colors)])
    fig.update_layout(
        title="Asset Allocation (100%)",
        height=280,
        margin=dict(l=10, r=10, t=35, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    )
    return fig


def _render_allocation_table(alloc_dict: Dict[str, Any]):
    """Render table of educational category allocations and rationale."""
    rows = []
    for item in ASSET_CLASSES:
        k = item["key"]
        info = alloc_dict.get(k, {})
        pct = info.get("percentage", 0.0)
        if pct > 0:
            rows.append(
                {
                    "Asset Class": item["name"],
                    "Share": f"{pct:.0f}%",
                    "Role": item["role"],
                    "Typical Instruments": item["instruments"],
                }
            )
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
