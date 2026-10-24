"""
views/retirement_view.py
Streamlit UI dashboard for FIRE & Retirement Planning in AI Money Mentor.
Includes interactive Retirement Planner, FIRE Planner, What-If Scenario Simulator,
and Saved Plans History with rich Plotly charts and deterministic financial math.
"""
from datetime import datetime
import json
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.profile_service import format_inr
from services.retirement_planning_service import (
    delete_saved_plan,
    evaluate_retirement_and_fire_plan,
    get_latest_saved_plan,
    get_saved_plans_history,
    get_user_retirement_context,
    save_retirement_plan,
)
from utils.fire_calculator import (
    calculate_fire_corpus,
    calculate_fire_timeline,
    calculate_savings_rate_table,
)
from utils.retirement_calculator import (
    calculate_inflation_adjusted_expenses,
    calculate_required_monthly_contribution,
    calculate_retirement_accumulation,
    calculate_retirement_corpus,
)


def render_retirement_view(
    user_id: str = "default_user", db_path: Optional[str] = None
):
    """Primary render function for FIRE & Retirement Planning view."""
    st.header("🏖️ FIRE & Retirement Planning")
    st.caption(
        "Estimate your retirement corpus, determine your FIRE (Financial Independence, Retire Early) timeline, "
        "and simulate the impact of inflation, savings rate, and compounding returns."
    )

    # Educational Disclaimer Banner
    st.info(
        "ℹ️ **Educational Financial Planning Prototype:** All projections and corpus requirements are deterministic "
        "mathematical models. Real-world market returns fluctuate unpredictably, inflation varies over time, and taxes "
        "materially impact net cash flows. This prototype is not a regulated SEBI investment advisory service."
    )
    st.divider()

    # Load baseline context from user's saved financial profile, budget, and goals
    ctx = get_user_retirement_context(user_id=user_id, db_path=db_path)

    # Initialize session state for interactive inputs
    if "ret_inputs" not in st.session_state:
        st.session_state.ret_inputs = {
            "current_age": ctx["current_age"],
            "target_retirement_age": ctx["target_retirement_age"],
            "planning_age": ctx["planning_age"],
            "current_corpus": ctx["current_corpus"],
            "monthly_expenses_today": ctx["monthly_expenses_today"],
            "monthly_contribution": ctx["monthly_contribution"],
            "available_monthly_surplus": ctx["available_monthly_surplus"],
            "annual_inflation_rate": ctx["annual_inflation_rate"],
            "pre_retirement_return": ctx["pre_retirement_return"],
            "post_retirement_return": ctx["post_retirement_return"],
            "safe_withdrawal_rate": ctx["safe_withdrawal_rate"],
            "fire_safe_withdrawal_rate": ctx["fire_safe_withdrawal_rate"],
            "monthly_pension": ctx["monthly_pension"],
            "is_pension_inflation_indexed": ctx["is_pension_inflation_indexed"],
            "monthly_income": ctx["monthly_income"],
        }

    # Evaluate current plan
    plan = evaluate_retirement_and_fire_plan(
        st.session_state.ret_inputs, user_id=user_id, db_path=db_path
    )

    if not plan["is_valid"]:
        for err in plan.get("errors", []):
            st.error(f"⚠️ {err}")
        return

    # 1. TOP-LEVEL METRICS CARDS
    _render_executive_metrics(plan)

    # 2. DETERMINISTIC ALERTS
    if plan.get("alerts"):
        _render_plan_alerts(plan["alerts"])

    st.markdown("---")

    # 3. MAIN DASHBOARD TABS
    tab_retire, tab_fire, tab_scenarios, tab_history = st.tabs(
        [
            "🏖️ Retirement Planner",
            "🔥 FIRE Planner",
            "🔬 What-If Scenario Simulator",
            "📜 Saved Plans & History",
        ]
    )

    with tab_retire:
        _render_retirement_tab(plan, user_id=user_id, db_path=db_path)

    with tab_fire:
        _render_fire_tab(plan, user_id=user_id, db_path=db_path)

    with tab_scenarios:
        _render_scenarios_tab(plan, user_id=user_id, db_path=db_path)

    with tab_history:
        _render_history_tab(user_id=user_id, db_path=db_path)


def _render_executive_metrics(plan: Dict[str, Any]):
    """Render top-level KPI cards for executive overview."""
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Retirement Age</div>
                <div class="metric-value">{plan['target_retirement_age']} Yrs</div>
                <div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">In {plan['years_until_retirement']:.0f} years (Age {plan['current_age']})</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Future Monthly Exp.</div>
                <div class="metric-value">{format_inr(plan['future_monthly_expenses'])}</div>
                <div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">Today: {format_inr(plan['monthly_expenses_today'])}/mo</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Target Corpus</div>
                <div class="metric-value">{format_inr(plan['target_corpus'])}</div>
                <div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">At Age {plan['target_retirement_age']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        is_funded = plan["is_corpus_funded"]
        status_color = "#10b981" if is_funded else "#ef4444"
        gap_str = (
            f"+{format_inr(plan['surplus_or_shortfall'])} Surplus"
            if is_funded
            else f"-{format_inr(abs(plan['corpus_gap']))} Shortfall"
        )
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Projected Corpus</div>
                <div class="metric-value" style="color:{status_color};">{format_inr(plan['projected_corpus'])}</div>
                <div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">{gap_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col5:
        fire_info = plan.get("fire_timeline", {})
        fire_age_str = f"Age {fire_info['fire_age']:.0f}" if fire_info.get("fire_age") else "Extended"
        fire_sub = (
            f"In {fire_info['years_to_fire']:.1f} Yrs"
            if fire_info.get("years_to_fire") is not None
            else "Needs higher savings"
        )
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Projected FIRE</div>
                <div class="metric-value" style="color:#6366f1;">{fire_age_str}</div>
                <div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">{fire_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_plan_alerts(alerts: List[Dict[str, str]]):
    """Render prioritized deterministic warnings and insights."""
    for alert in alerts:
        sev = alert.get("level", "info")
        title = alert.get("title")
        msg = alert.get("message", "")
        disp = f"**{title}:** {msg}" if title else msg
        if sev in ["critical", "error"]:
            st.error(f"🚨 {disp}")
        elif sev == "warning":
            st.warning(f"⚠️ {disp}")
        elif sev == "success":
            st.success(f"🎉 {disp}")
        else:
            st.info(f"💡 {disp}")


def _render_retirement_tab(
    plan: Dict[str, Any], user_id: str = "default_user", db_path: Optional[str] = None
):
    """Render detailed traditional retirement planning interface."""
    st.subheader("🏖️ Traditional Retirement Planning Dashboard")
    st.caption("Plan your financial milestone, adjust assumptions, and visualize retirement cash flows.")

    col_form, col_charts = st.columns([1, 1.2])

    with col_form:
        st.markdown("#### ⚙️ Retirement Planning Assumptions")

        c1, c2 = st.columns(2)
        with c1:
            cur_age = st.number_input(
                "Current Age (Years)",
                min_value=18,
                max_value=100,
                value=int(st.session_state.ret_inputs["current_age"]),
                step=1,
            )
            ret_age = st.number_input(
                "Target Retirement Age",
                min_value=cur_age + 1,
                max_value=110,
                value=max(cur_age + 1, int(st.session_state.ret_inputs["target_retirement_age"])),
                step=1,
            )
            plan_age = st.number_input(
                "Planning Age (Life Expectancy)",
                min_value=ret_age + 1,
                max_value=120,
                value=max(ret_age + 1, int(st.session_state.ret_inputs["planning_age"])),
                step=1,
                help="Duration of retirement to fund.",
            )
        with c2:
            cur_corpus = st.number_input(
                "Current Retirement Corpus (₹)",
                min_value=0.0,
                value=float(st.session_state.ret_inputs["current_corpus"]),
                step=50000.0,
                help="Existing investments designated for retirement.",
            )
            mo_exp_val = max(0.0, float(st.session_state.ret_inputs.get("monthly_expenses_today", 0.0)))
            mo_exp = st.number_input(
                "Monthly Expenses Today (₹)",
                min_value=0.0,
                value=mo_exp_val,
                step=2500.0,
                help="Living expenses needed in retirement in today's purchasing power.",
            )
            mo_contrib = st.number_input(
                "Planned Monthly Contribution (₹)",
                min_value=0.0,
                value=float(st.session_state.ret_inputs["monthly_contribution"]),
                step=2500.0,
                help="Current monthly SIP towards retirement.",
            )

        with st.expander("🛠️ Advanced Return, Inflation & Pension Inputs", expanded=False):
            ar1, ar2 = st.columns(2)
            with ar1:
                inf_v = float(st.session_state.ret_inputs.get("annual_inflation_rate", 6.0))
                inf_rate = st.slider(
                    "Annual Inflation Rate (%)",
                    min_value=0.0,
                    max_value=15.0,
                    value=min(15.0, max(0.0, inf_v)),
                    step=0.5,
                )
                pre_v = float(st.session_state.ret_inputs.get("pre_retirement_return", 10.0))
                pre_ret = st.slider(
                    "Pre-Retirement Annual Return (%)",
                    min_value=2.0,
                    max_value=20.0,
                    value=min(20.0, max(2.0, pre_v)),
                    step=0.5,
                )
                post_v = float(st.session_state.ret_inputs.get("post_retirement_return", 7.0))
                post_ret = st.slider(
                    "Post-Retirement Annual Return (%)",
                    min_value=1.0,
                    max_value=15.0,
                    value=min(15.0, max(1.0, post_v)),
                    step=0.5,
                )
            with ar2:
                swr_v = float(st.session_state.ret_inputs.get("safe_withdrawal_rate", 4.0))
                swr = st.slider(
                    "Safe Withdrawal Rate Baseline (%)",
                    min_value=1.0,
                    max_value=8.0,
                    value=min(8.0, max(1.0, swr_v)),
                    step=0.25,
                    help="Traditional rule-of-thumb baseline (e.g. 4.0%).",
                )
                pension_amt = st.number_input(
                    "Reliable Monthly Pension (₹)",
                    min_value=0.0,
                    value=float(st.session_state.ret_inputs.get("monthly_pension", 0.0)),
                    step=2500.0,
                )
                pension_indexed = st.checkbox(
                    "Pension is Inflation-Indexed",
                    value=bool(st.session_state.ret_inputs["is_pension_inflation_indexed"]),
                )

        # Update session state if inputs change
        updated_inputs = {
            "current_age": cur_age,
            "target_retirement_age": ret_age,
            "planning_age": plan_age,
            "current_corpus": cur_corpus,
            "monthly_expenses_today": mo_exp,
            "monthly_contribution": mo_contrib,
            "available_monthly_surplus": st.session_state.ret_inputs.get("available_monthly_surplus"),
            "annual_inflation_rate": inf_rate,
            "pre_retirement_return": pre_ret,
            "post_retirement_return": post_ret,
            "safe_withdrawal_rate": swr,
            "fire_safe_withdrawal_rate": st.session_state.ret_inputs.get("fire_safe_withdrawal_rate", 3.5),
            "monthly_pension": pension_amt,
            "is_pension_inflation_indexed": pension_indexed,
            "monthly_income": st.session_state.ret_inputs.get("monthly_income", 100000.0),
        }
        st.session_state.ret_inputs = updated_inputs

        # Save Plan Action
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            if st.button("💾 Save Plan to Profile", key="btn_save_ret_plan", type="primary"):
                succ, _, errs = save_retirement_plan(plan, user_id=user_id, db_path=db_path)
                if succ:
                    st.success("🎉 Retirement plan successfully saved to your database!")
                else:
                    for e in errs:
                        st.error(e)

        with col_btn2:
            if st.button("🔄 Reset to Profile Defaults", key="btn_reset_ret_defaults"):
                ctx_reset = get_user_retirement_context(user_id=user_id, db_path=db_path)
                st.session_state.ret_inputs.update(ctx_reset)
                st.rerun()

    with col_charts:
        st.markdown("#### 📊 Target Corpus vs Accumulation Trajectory")
        fig_accum = _create_accumulation_chart(plan)
        st.plotly_chart(fig_accum, use_container_width=True)

        st.markdown("##### 💵 Contribution & Affordability Breakdown")
        req_pmt = plan["required_monthly_contribution"]
        cur_pmt = plan["monthly_contribution"]
        surplus = plan.get("available_monthly_surplus")

        cb1, cb2, cb3 = st.columns(3)
        cb1.metric("Required Monthly SIP", format_inr(req_pmt), help="Monthly contribution needed to reach target.")
        cb2.metric("Your Planned SIP", format_inr(cur_pmt))
        afford_status = plan.get("affordability_status", "Unknown")
        cb3.metric("Budget Affordability", afford_status)

    st.markdown("---")

    # Decumulation Cash Flow Table & Chart
    st.subheader("📉 Retirement Decumulation Cash Flows")
    st.caption(f"Estimated year-by-year portfolio drawdown over {plan['retirement_duration_years']} years of retirement.")
    
    cash_flows = plan.get("corpus_calculation", {}).get("cash_flow_schedule", [])
    if cash_flows:
        df_cf = pd.DataFrame(cash_flows)
        fig_decum = px.line(
            df_cf,
            x="year",
            y=["starting_balance", "ending_balance", "gross_expenses"],
            labels={"year": "Retirement Year", "value": "Amount (₹)", "variable": "Cash Flow Item"},
            title="Portfolio Balance Trajectory in Retirement (INR)",
            color_discrete_map={
                "starting_balance": "#3b82f6",
                "ending_balance": "#10b981",
                "gross_expenses": "#ef4444",
            },
        )
        st.plotly_chart(fig_decum, use_container_width=True)

        with st.expander("📋 View Year-by-Year Cash Flow Schedule Table"):
            st.dataframe(
                df_cf.rename(
                    columns={
                        "year": "Year",
                        "starting_balance": "Start Balance (₹)",
                        "gross_expenses": "Living Expenses (₹)",
                        "pension_income": "Pension (₹)",
                        "net_withdrawal": "Net Withdrawal (₹)",
                        "investment_earnings": "Earnings (₹)",
                        "ending_balance": "Ending Balance (₹)",
                    }
                ),
                hide_index=True,
                use_container_width=True,
            )

    # Detailed Assumptions
    with st.expander("ℹ️ Calculation Formulas & Methodology Documentation", expanded=False):
        for asmp in plan["corpus_calculation"].get("assumptions", []):
            st.markdown(f"- {asmp}")
        st.markdown(
            """
            - **Compounding Convention:** Monthly effective rate $r = (1 + R)^{1/12} - 1$.
            - **Simplified Corpus:** $\\text{Net Annual Expenses at Retirement} / \\text{SWR}$.
            - **Detailed Corpus:** Present value of growing annuity withdrawals over retirement duration net of pension.
            - **Inflation Adjustment:** $E_{\\text{future}} = E_{\\text{today}} \\times (1 + i)^t$.
            """
        )


def _render_fire_tab(
    plan: Dict[str, Any], user_id: str = "default_user", db_path: Optional[str] = None
):
    """Render dedicated FIRE (Financial Independence, Retire Early) planning interface."""
    st.subheader("🔥 Financial Independence, Retire Early (FIRE) Planner")
    st.caption("Calculate the exact corpus and timeline needed to live off your investment portfolio.")

    fire_info = plan.get("fire_timeline", {})
    fire_corpus = plan.get("fire_corpus_info", {})

    col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5, col_kpi6 = st.columns(6)
    with col_kpi1:
        st.metric(
            "Real FIRE Target (Today)",
            format_inr(fire_corpus.get("real_fire_corpus_today", 0)),
            help="Corpus needed in today's purchasing power (Method A: Expenses / SWR).",
        )
    with col_kpi2:
        st.metric(
            "Nominal FIRE Target",
            format_inr(fire_corpus.get("nominal_fire_corpus_at_fire", 0)),
            help="Nominal rupees needed at projected FIRE date adjusted for inflation.",
        )
    with col_kpi3:
        st.metric(
            "Invested Corpus Today",
            format_inr(plan.get("current_corpus", 0)),
            help="Current assets actively compounding towards FIRE.",
        )
    with col_kpi4:
        savings_rate = plan.get("current_savings_rate", 0.0)
        st.metric(
            "Current Savings Rate",
            f"{savings_rate:.1f}%",
            help="Percentage of monthly income currently invested.",
        )
    with col_kpi5:
        years_to_fire = fire_info.get("years_to_fire")
        st.metric(
            "Years to Freedom",
            f"{years_to_fire:.1f} Yrs" if years_to_fire is not None else "Infeasible",
            help="Timeline when investments meet the inflation-adjusted target.",
        )
    with col_kpi6:
        fire_age = fire_info.get("fire_age")
        st.metric(
            "Projected FIRE Age",
            f"Age {fire_age:.0f}" if fire_age is not None else "Needs adjustment",
            help="Age when you achieve financial independence.",
        )

    st.markdown("---")

    # Target FIRE Age Milestone Analysis
    st.markdown("#### 🎯 Target FIRE Age Milestones")
    st.caption("Plan for a specific target FIRE age and calculate the required monthly SIP and corpus shortfall/surplus.")
    
    cur_age = plan["current_age"]
    ret_age = plan["target_retirement_age"]
    default_fire_tgt = plan.get("target_fire_age", min(ret_age, max(cur_age + 5, 50)))

    tf_col1, tf_col2 = st.columns([1, 2])
    with tf_col1:
        min_fire = cur_age + 1
        max_fire = max(min_fire + 1, ret_age)
        sel_fire_age = st.slider(
            "Choose Target FIRE Age",
            min_value=min_fire,
            max_value=max_fire,
            value=max(min_fire, min(max_fire, int(default_fire_tgt))),
            step=1,
            key="fire_target_age_slider",
        )
    
    # Calculate on-the-fly for selected FIRE age
    from utils.fire_calculator import calculate_target_fire_age_analysis
    tf_analysis = calculate_target_fire_age_analysis(
        current_age=cur_age,
        current_invested_assets=plan["current_corpus"],
        monthly_investment_contribution=plan["monthly_contribution"],
        annual_expenses_today=plan["annual_expenses_today"],
        target_fire_age=sel_fire_age,
        assumed_annual_return=plan["pre_retirement_return"],
        annual_inflation_rate=plan["inflation_rate"],
        safe_withdrawal_rate=plan["fire_safe_withdrawal_rate"],
    )

    with tf_col2:
        tc1, tc2, tc3, tc4 = st.columns(4)
        tc1.metric("Target Corpus", format_inr(tf_analysis["nominal_fire_target"]))
        tc2.metric("Projected Corpus", format_inr(tf_analysis["projected_corpus_at_target_age"]))
        tf_gap = tf_analysis["shortfall_or_surplus"]
        tc3.metric(
            "Funding Balance",
            f"+{format_inr(tf_gap)}" if tf_gap >= 0 else f"-{format_inr(abs(tf_gap))}",
            delta="Surplus" if tf_gap >= 0 else "Shortfall",
            delta_color="normal" if tf_gap >= 0 else "inverse",
        )
        tc4.metric(
            "Required Monthly SIP",
            format_inr(tf_analysis["required_monthly_contribution"]),
            help="Monthly investment needed to hit FIRE by selected age.",
        )

    st.markdown("---")

    # Freedom Crossing Chart
    st.markdown("#### 🚀 Wealth Accumulation vs FIRE Target Crossover")
    st.caption("Visualizing the milestone where your accumulated investments surpass the inflation-growing target.")

    trajectory = fire_info.get("trajectory", [])
    if trajectory:
        df_traj = pd.DataFrame(trajectory)
        fig_cross = go.Figure()
        fig_cross.add_trace(go.Scatter(
            x=df_traj["age"],
            y=df_traj["accumulated"],
            mode="lines+markers",
            name="Accumulated Portfolio",
            line=dict(color="#10b981", width=3),
        ))
        fig_cross.add_trace(go.Scatter(
            x=df_traj["age"],
            y=df_traj["target"],
            mode="lines",
            name="Nominal FIRE Target (Growing with Inflation)",
            line=dict(color="#ef4444", dash="dash", width=2),
        ))

        if fire_info.get("fire_age"):
            fig_cross.add_vline(
                x=fire_info["fire_age"],
                line_width=2,
                line_dash="dot",
                line_color="#6366f1",
                annotation_text=f"Freedom Age: {fire_info['fire_age']:.0f}",
                annotation_position="top left",
            )

        fig_cross.update_layout(
            title="FIRE Crossover Trajectory (INR)",
            xaxis_title="Age (Years)",
            yaxis_title="Corpus Amount (₹)",
            template="plotly_white",
            height=380,
        )
        st.plotly_chart(fig_cross, use_container_width=True)

    st.markdown("---")

    # Classic Savings Rate vs Years to Freedom Table
    st.subheader("📈 Savings Rate vs Years to Freedom")
    st.caption("How increasing your savings rate exponentially compresses your working career.")

    savings_table = plan.get("savings_rate_table", [])
    if savings_table:
        df_sr = pd.DataFrame(savings_table)
        df_display = df_sr.copy()
        df_display["monthly_investment"] = df_display["monthly_investment"].apply(format_inr)
        df_display["monthly_expenses"] = df_display["monthly_expenses"].apply(format_inr)
        df_display["fire_corpus_today"] = df_display["fire_corpus_today"].apply(format_inr)
        df_display["years_to_fire"] = df_display["years_to_fire"].apply(
            lambda x: f"{x:.1f} Yrs" if x is not None else "N/A"
        )
        df_display["fire_age"] = df_display["fire_age"].apply(
            lambda x: f"Age {x:.0f}" if x is not None else "N/A"
        )

        col_tbl, col_chart = st.columns([1.2, 1])
        with col_tbl:
            st.dataframe(
                df_display.rename(
                    columns={
                        "savings_rate_pct": "Savings Rate (%)",
                        "monthly_investment": "Monthly SIP",
                        "monthly_expenses": "Living Expenses",
                        "years_to_fire": "Time to FIRE",
                        "fire_age": "FIRE Age",
                        "fire_corpus_today": "Target Corpus",
                    }
                )[["Savings Rate (%)", "Monthly SIP", "Living Expenses", "Time to FIRE", "FIRE Age", "Target Corpus"]],
                hide_index=True,
                use_container_width=True,
            )

        with col_chart:
            df_plot = df_sr.dropna(subset=["years_to_fire"])
            if not df_plot.empty:
                fig_sr = px.bar(
                    df_plot,
                    x="savings_rate_pct",
                    y="years_to_fire",
                    labels={"savings_rate_pct": "Savings Rate (%)", "years_to_fire": "Years to Freedom"},
                    title="Years to Freedom by Savings Rate",
                    color="years_to_fire",
                    color_continuous_scale="Viridis_r",
                    height=300,
                )
                st.plotly_chart(fig_sr, use_container_width=True)


def _render_scenarios_tab(
    base_plan: Dict[str, Any], user_id: str = "default_user", db_path: Optional[str] = None
):
    """Interactive What-If Scenario Simulator."""
    st.subheader("🔬 Interactive What-If Retirement Scenario Simulator")
    st.caption("Simulate changes to your retirement age, SIP amount, or returns without modifying your saved profile.")

    base_inputs = base_plan["inputs"]

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("##### 🎛️ Scenario Timeline & Contribution")
        c_age_base = int(base_inputs["current_age"])
        r_age_base = int(base_inputs["target_retirement_age"])
        min_ret_age = c_age_base + 1
        max_ret_age = max(100, r_age_base + 10)
        sc_ret_age = st.slider(
            "Hypothetical Retirement Age",
            min_value=min_ret_age,
            max_value=max_ret_age,
            value=min(max_ret_age, max(min_ret_age, r_age_base)),
            step=1,
            key="sc_ret_age_slider",
        )
        cur_contrib = max(0, int(base_inputs.get("monthly_contribution", 0.0)))
        max_contrib = max(100000, cur_contrib * 3)
        sc_contrib = st.slider(
            "Hypothetical Monthly Contribution (₹)",
            min_value=0,
            max_value=max_contrib,
            value=min(max_contrib, cur_contrib),
            step=2500 if max_contrib > 10000 else 500,
            key="sc_contrib_slider",
        )
        cur_sc_exp = max(0.0, float(base_inputs.get("monthly_expenses_today", 0.0)))
        sc_expenses = st.number_input(
            "Hypothetical Retirement Monthly Expenses (₹)",
            min_value=0.0,
            value=cur_sc_exp,
            step=2500.0,
            key="sc_exp_input",
        )

    with col_s2:
        st.markdown("##### 📈 Return & Inflation Adjustments")
        pre_val = float(base_inputs.get("pre_retirement_return", 10.0))
        sc_pre_ret = st.slider(
            "Pre-Retirement Annual Return (%)",
            min_value=2.0,
            max_value=20.0,
            value=min(20.0, max(2.0, pre_val)),
            step=0.5,
            key="sc_pre_ret_slider",
        )
        inf_val = float(base_inputs.get("annual_inflation_rate", 6.0))
        sc_inf = st.slider(
            "Expected Annual Inflation (%)",
            min_value=0.0,
            max_value=15.0,
            value=min(15.0, max(0.0, inf_val)),
            step=0.5,
            key="sc_inf_slider",
        )
        swr_val = float(base_inputs.get("safe_withdrawal_rate", 4.0))
        sc_swr = st.slider(
            "Safe Withdrawal Rate (%)",
            min_value=1.0,
            max_value=8.0,
            value=min(8.0, max(1.0, swr_val)),
            step=0.25,
            key="sc_swr_slider",
        )

    # Evaluate hypothetical scenario
    sc_inputs = dict(base_inputs)
    sc_inputs["target_retirement_age"] = sc_ret_age
    sc_inputs["monthly_contribution"] = sc_contrib
    sc_inputs["monthly_expenses_today"] = sc_expenses
    sc_inputs["pre_retirement_return"] = sc_pre_ret
    sc_inputs["annual_inflation_rate"] = sc_inf
    sc_inputs["safe_withdrawal_rate"] = sc_swr

    sc_plan = evaluate_retirement_and_fire_plan(sc_inputs, user_id=user_id, db_path=db_path)

    st.markdown("---")
    st.markdown("##### ⚖️ Side-by-Side Comparison: Saved Baseline vs What-If Scenario")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(
            "Target Corpus",
            format_inr(sc_plan["target_corpus"]),
            delta=f"{format_inr(sc_plan['target_corpus'] - base_plan['target_corpus'])} vs baseline",
            delta_color="inverse",
        )
    with m2:
        st.metric(
            "Projected Corpus",
            format_inr(sc_plan["projected_corpus"]),
            delta=f"{format_inr(sc_plan['projected_corpus'] - base_plan['projected_corpus'])} vs baseline",
        )
    with m3:
        st.metric(
            "Required Monthly SIP",
            format_inr(sc_plan["required_monthly_contribution"]),
            delta=f"{format_inr(sc_plan['required_monthly_contribution'] - base_plan['required_monthly_contribution'])} vs baseline",
            delta_color="inverse",
        )
    with m4:
        sc_fire = sc_plan.get("fire_timeline", {}).get("fire_age")
        base_fire = base_plan.get("fire_timeline", {}).get("fire_age")
        diff_str = (
            f"{sc_fire - base_fire:.0f} Yrs vs baseline"
            if (sc_fire and base_fire)
            else "N/A"
        )
        st.metric(
            "Projected FIRE Age",
            f"Age {sc_fire:.0f}" if sc_fire else "Extended",
            delta=diff_str,
            delta_color="inverse",
        )

    # Scenario Comparison Chart
    fig_cmp = go.Figure()
    fig_cmp.add_trace(go.Bar(
        name="Target Corpus",
        x=["Saved Baseline", "What-If Scenario"],
        y=[base_plan["target_corpus"], sc_plan["target_corpus"]],
        marker_color="#94a3b8",
    ))
    fig_cmp.add_trace(go.Bar(
        name="Projected Corpus",
        x=["Saved Baseline", "What-If Scenario"],
        y=[base_plan["projected_corpus"], sc_plan["projected_corpus"]],
        marker_color="#10b981",
    ))
    fig_cmp.update_layout(
        barmode="group",
        title="Corpus Comparison (INR)",
        yaxis_title="Amount (₹)",
        template="plotly_white",
        height=350,
    )
    st.plotly_chart(fig_cmp, use_container_width=True)

    # Action buttons: Reset vs Save Scenario
    b1, b2, _ = st.columns([1.5, 1.5, 3])
    with b1:
        if st.button("🔄 Reset to Baseline Plan", key="btn_reset_sc_sliders"):
            for k in ["sc_ret_age_slider", "sc_contrib_slider", "sc_exp_input", "sc_pre_ret_slider", "sc_inf_slider", "sc_swr_slider"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    with b2:
        if st.button("💾 Save Scenario as Active Plan", key="btn_save_sc_as_active"):
            succ, _, errs = save_retirement_plan(sc_plan, user_id=user_id, db_path=db_path)
            if succ:
                st.session_state.ret_inputs.update(sc_inputs)
                st.success("🎉 Scenario successfully saved as your primary retirement plan!")
                st.rerun()
            else:
                for e in errs:
                    st.error(e)


def _render_history_tab(user_id: str = "default_user", db_path: Optional[str] = None):
    """Render saved retirement plans and historical snapshots."""
    st.subheader("📜 Saved Retirement Plans & Historical Snapshots")
    st.caption("Review previous retirement projections and track your plan evolutions over time.")

    history = get_saved_plans_history(user_id=user_id, db_path=db_path)
    if not history:
        st.info("No saved plans found in database. Use the **💾 Save Plan to Profile** button in the Retirement Planner tab to save your milestones.")
        return

    latest = get_latest_saved_plan(user_id=user_id, db_path=db_path)
    if latest:
        st.markdown(f"#### 🌟 Latest Active Plan: **{latest.get('plan_name', 'Retirement Plan')}**")
        st.caption(f"Saved on {latest.get('created_at', '')[:19]}")

        lc1, lc2, lc3, lc4 = st.columns(4)
        lc1.metric("Retirement Age", f"{latest['target_retirement_age']} Yrs")
        lc2.metric("Target Corpus", format_inr(latest["target_corpus"]))
        lc3.metric("Projected Corpus", format_inr(latest["projected_corpus"]))
        lc4.metric("Required Monthly", format_inr(latest["required_monthly"]))

    st.markdown("---")
    st.markdown("##### 📁 Plan History Table")

    for p in history:
        col_p1, col_p2, col_p3 = st.columns([3, 1, 1])
        with col_p1:
            st.write(f"**{p['plan_name']}** — Target: {format_inr(p['target_corpus'])} at Age {p['target_retirement_age']}")
            st.caption(f"Created: {p['created_at'][:19]} | Required Monthly: {format_inr(p['required_monthly'])}")
        with col_p2:
            if p["is_latest"]:
                st.success("Active Plan")
            else:
                st.caption("Archived")
        with col_p3:
            if st.button("🗑️ Delete", key=f"btn_del_plan_{p['id']}"):
                delete_saved_plan(p["id"], user_id=user_id, db_path=db_path)
                st.rerun()


def _create_accumulation_chart(plan: Dict[str, Any]) -> go.Figure:
    """Create chart showing accumulation trajectory towards target corpus."""
    trajectory = plan["accumulation"].get("trajectory", [])
    target = plan["target_corpus"]

    if not trajectory:
        return go.Figure()

    df = pd.DataFrame(trajectory)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["year"],
        y=df["total_fv"],
        mode="lines+markers",
        name="Projected Corpus",
        line=dict(color="#10b981", width=3),
    ))
    fig.add_trace(go.Scatter(
        x=df["year"],
        y=df["principal"],
        mode="lines",
        name="Principal Contributions",
        line=dict(color="#3b82f6", width=2),
    ))
    fig.add_hline(
        y=target,
        line_dash="dash",
        line_color="#ef4444",
        annotation_text=f"Target: {format_inr(target)}",
        annotation_position="top left",
    )
    fig.update_layout(
        title="Retirement Accumulation Runway (INR)",
        xaxis_title="Years Until Retirement",
        yaxis_title="Corpus Amount (₹)",
        template="plotly_white",
        height=320,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig
