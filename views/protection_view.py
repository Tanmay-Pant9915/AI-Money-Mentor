"""
views/protection_view.py
Streamlit UI dashboard for Emergency Fund & Insurance Planning in AI Money Mentor.
Includes interactive Emergency Fund Planner, Health & Life Insurance Needs Assessment,
Personal Accident protection review, Combined Multi-Pillar Protection Scorecard,
Prioritized Actionable Recommendations, and historical snapshot management.
"""
from datetime import date
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.emergency_fund_service import (
    delete_emergency_fund_plan,
    evaluate_emergency_fund_plan,
    get_emergency_fund_history,
    get_latest_emergency_fund_plan,
    get_user_emergency_fund_context,
    save_emergency_fund_plan,
)
from services.insurance_planning_service import (
    delete_insurance_assessment,
    evaluate_insurance_assessment,
    get_insurance_assessment_history,
    get_latest_insurance_assessment,
    get_user_insurance_context,
    save_insurance_assessment,
)
from services.profile_service import format_inr
from utils.protection_recommendations import (
    evaluate_overall_protection_status,
    generate_protection_recommendations,
)


def render_protection_view(user_id: str = "default_user", db_path: Optional[str] = None):
    """Primary render function for Emergency Fund & Insurance Planning view."""
    st.header("🛡️ Emergency Fund & Insurance Planning")
    st.caption(
        "Build a robust financial defense: establish your liquid emergency cushion, "
        "assess health and life insurance coverage gaps, and evaluate personal disability protection."
    )

    # Educational Disclaimer Banner
    st.info(
        "ℹ️ **Educational Planning Prototype:** This module provides mathematical planning models and checklists. "
        "It is **not** a substitute for advice from a SEBI-registered investment adviser or an IRDAI-licensed insurance broker. "
        "AI Money Mentor does not sell insurance policies or promote specific insurance providers. Always verify policy terms independently."
    )
    st.divider()

    # Load baseline context from user profile
    ef_ctx = get_user_emergency_fund_context(user_id=user_id, db_path=db_path)
    ins_ctx = get_user_insurance_context(user_id=user_id, db_path=db_path)

    # Initialize Session State
    if "ef_inputs" not in st.session_state:
        st.session_state.ef_inputs = {
            "essential_expenses": ef_ctx["essential_expenses"],
            "target_months": ef_ctx["target_months"],
            "current_liquid_savings": ef_ctx["current_liquid_savings"],
            "monthly_contribution": ef_ctx["monthly_contribution"],
            "available_monthly_surplus": ef_ctx["available_monthly_surplus"],
            "monthly_debt_repayment": ef_ctx["monthly_debt_repayment"],
        }

    if "ins_inputs" not in st.session_state:
        st.session_state.ins_inputs = {
            "annual_income": ins_ctx["annual_income"],
            "dependents": ins_ctx["dependents"],
            "outstanding_debt": ins_ctx["outstanding_debt"],
            "future_family_obligations": ins_ctx["future_family_obligations"],
            "family_goals_sum": ins_ctx["family_goals_sum"],
            "eligible_assets": ins_ctx["eligible_assets"],
            "number_of_members": ins_ctx["number_of_members"],
            "health_personal_coverage": ins_ctx["health_personal_coverage"],
            "health_employer_coverage": ins_ctx["health_employer_coverage"],
            "health_target_coverage": ins_ctx["health_target_coverage"],
            "health_policy_type": ins_ctx["health_policy_type"],
            "life_existing_coverage": ins_ctx["life_existing_coverage"],
            "life_income_multiplier_years": ins_ctx["life_income_multiplier_years"],
            "has_accident_disability_cover": ins_ctx["has_accident_disability_cover"],
            "accident_cover_amount": ins_ctx["accident_cover_amount"],
        }

    # Evaluate current plans
    ef_plan = evaluate_emergency_fund_plan(st.session_state.ef_inputs, user_id=user_id, db_path=db_path)
    ins_assessment = evaluate_insurance_assessment(st.session_state.ins_inputs, user_id=user_id, db_path=db_path)

    if not ef_plan["is_valid"]:
        for err in ef_plan.get("errors", []):
            st.error(f"⚠️ {err}")
        return

    if not ins_assessment["is_valid"]:
        for err in ins_assessment.get("errors", []):
            st.error(f"⚠️ {err}")
        return

    # Overall scorecard and recommendations
    scorecard = evaluate_overall_protection_status(
        emergency_plan=ef_plan,
        health_assessment=ins_assessment["health_assessment"],
        life_assessment=ins_assessment["life_assessment"],
        accident_assessment=ins_assessment["accident_assessment"],
    )

    recommendations = generate_protection_recommendations(
        emergency_plan=ef_plan,
        health_assessment=ins_assessment["health_assessment"],
        life_assessment=ins_assessment["life_assessment"],
        accident_assessment=ins_assessment["accident_assessment"],
        available_surplus=st.session_state.ef_inputs.get("available_monthly_surplus"),
    )

    # 1. TOP-LEVEL EXECUTIVE METRICS
    _render_executive_metrics(ef_plan, ins_assessment, scorecard)

    st.markdown("---")

    # 2. MAIN TABS NAVIGATION
    tab_ef, tab_ins, tab_combined, tab_history = st.tabs(
        [
            "🛡️ Emergency Fund Planner",
            "🏥 Health & Life Insurance Needs",
            "📊 Combined Protection Dashboard & Action Plan",
            "📜 Saved Plans & History",
        ]
    )

    with tab_ef:
        _render_emergency_fund_tab(ef_plan, user_id=user_id, db_path=db_path)

    with tab_ins:
        _render_insurance_tab(ins_assessment, user_id=user_id, db_path=db_path)

    with tab_combined:
        _render_combined_dashboard_tab(scorecard, recommendations, ef_plan, ins_assessment)

    with tab_history:
        _render_history_tab(user_id=user_id, db_path=db_path)


def _render_executive_metrics(
    ef_plan: Dict[str, Any], ins_assessment: Dict[str, Any], scorecard: Dict[str, Any]
):
    """Render top-level executive KPI cards."""
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Emergency Coverage</div>
                <div class="metric-value" style="color:{ef_plan['color']};">{ef_plan['coverage_months']:.1f} Mo</div>
                <div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">Target: {ef_plan['target_months']:.0f} Mo ({ef_plan['status']})</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Liquid Savings</div>
                <div class="metric-value">{format_inr(ef_plan['current_liquid_savings'])}</div>
                <div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">Target: {format_inr(ef_plan['target_amount'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        h_eval = ins_assessment["health_assessment"]
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Health Cover Gap</div>
                <div class="metric-value" style="color:{h_eval['color']};">{format_inr(h_eval['total_coverage_gap'])}</div>
                <div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">Cover: {format_inr(h_eval['total_current_coverage'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        l_eval = ins_assessment["life_assessment"]
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Term Life Gap</div>
                <div class="metric-value" style="color:{l_eval['color']};">{format_inr(l_eval['net_additional_need'])}</div>
                <div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">Active: {format_inr(l_eval['existing_life_insurance'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col5:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Defense Readiness</div>
                <div class="metric-value" style="color:{scorecard['overall_color']}; font-size:1.35rem;">{scorecard['overall_badge']}</div>
                <div style="font-size:0.8rem; opacity:0.75; margin-top:4px;">{scorecard['overall_status']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_emergency_fund_tab(
    plan: Dict[str, Any], user_id: str = "default_user", db_path: Optional[str] = None
):
    """Render interactive Emergency Fund Planner."""
    st.subheader("🛡️ Emergency Fund Planner")
    st.caption("Calculate your target safety buffer, assess coverage runway, and simulate monthly contribution timelines.")

    # Alerts
    for alert in plan.get("alerts", []):
        lvl = alert.get("level", "info")
        msg = f"**{alert.get('title')}:** {alert.get('message')}"
        if lvl == "error":
            st.error(f"🚨 {msg}")
        elif lvl == "warning":
            st.warning(f"⚠️ {msg}")
        elif lvl == "success":
            st.success(f"🎉 {msg}")
        else:
            st.info(f"💡 {msg}")

    col_inputs, col_viz = st.columns([1, 1.2])

    with col_inputs:
        st.markdown("#### ⚙️ Planning Assumptions")

        c1, c2 = st.columns(2)
        with c1:
            essential_exp = st.number_input(
                "Monthly Essential Expenses (₹)",
                min_value=0.0,
                value=max(0.0, float(st.session_state.ef_inputs["essential_expenses"])),
                step=2500.0,
                help="Rent, groceries, utilities, EMIs, and non-negotiable living costs.",
            )
            target_months_opt = st.selectbox(
                "Target Coverage Duration",
                options=[3.0, 6.0, 9.0, 12.0, "Custom"],
                index=[3.0, 6.0, 9.0, 12.0].index(st.session_state.ef_inputs["target_months"])
                if st.session_state.ef_inputs["target_months"] in [3.0, 6.0, 9.0, 12.0]
                else 1,
            )
            if target_months_opt == "Custom":
                target_months = st.number_input(
                    "Custom Months to Cover",
                    min_value=1.0,
                    max_value=36.0,
                    value=float(st.session_state.ef_inputs["target_months"]),
                    step=1.0,
                )
            else:
                target_months = float(target_months_opt)

        with c2:
            current_savings = st.number_input(
                "Current Liquid Cash Savings (₹)",
                min_value=0.0,
                value=max(0.0, float(st.session_state.ef_inputs["current_liquid_savings"])),
                step=10000.0,
                help="Only include high-yield savings, sweep-in accounts, and instantly accessible liquid funds. Exclude volatile stocks and locked PF.",
            )
            planned_contrib = st.number_input(
                "Planned Monthly Contribution (₹)",
                min_value=0.0,
                value=max(0.0, float(st.session_state.ef_inputs["monthly_contribution"])),
                step=2500.0,
                help="Monthly amount directed toward building this emergency fund.",
            )

        st.caption(
            "💡 *Planning Note:* Salaried professionals with no dependents and minimal debt often target **3–6 months**. "
            "Self-employed individuals, business owners, or families with multiple dependents and high debt typically target **6–12 months**."
        )

        # Update Session State
        st.session_state.ef_inputs.update({
            "essential_expenses": essential_exp,
            "target_months": target_months,
            "current_liquid_savings": current_savings,
            "monthly_contribution": planned_contrib,
        })

        # Save Plan Action
        b1, b2 = st.columns(2)
        with b1:
            if st.button("💾 Save Emergency Fund Plan", key="btn_save_ef_plan", type="primary"):
                succ, _, errs = save_emergency_fund_plan(plan, user_id=user_id, db_path=db_path)
                if succ:
                    st.success("🎉 Emergency fund plan saved to your profile database!")
                else:
                    for e in errs:
                        st.error(e)

        with b2:
            if st.button("🔄 Reset to Profile Defaults", key="btn_reset_ef_plan"):
                ctx_reset = get_user_emergency_fund_context(user_id=user_id, db_path=db_path)
                st.session_state.ef_inputs.update(ctx_reset)
                st.rerun()

    with col_viz:
        st.markdown("#### 🎯 Fund Progress & Target Status")

        # Metrics overview
        m1, m2, m3 = st.columns(3)
        m1.metric("Target Corpus", format_inr(plan["target_amount"]))
        m2.metric("Remaining Gap", format_inr(plan["fund_gap"]), delta=f"{plan['progress_pct']:.0f}% funded")
        m3.metric(
            "Months to Target",
            f"{plan['months_to_target']} Mo" if plan["months_to_target"] is not None else "N/A",
            help="At your planned monthly contribution.",
        )

        # Visual Progress Bar
        st.write(f"**Funding Progress: {plan['actual_pct']:.1f}%** ({plan['badge']})")
        st.progress(min(1.0, plan["progress_pct"] / 100.0))

        # Chart: Current vs Target
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name="Current Liquid Savings",
            x=["Emergency Fund"],
            y=[plan["current_liquid_savings"]],
            marker_color="#10b981" if plan["is_target_reached"] else "#3b82f6",
            text=[format_inr(plan["current_liquid_savings"])],
            textposition="auto",
        ))
        if plan["fund_gap"] > 0:
            fig_bar.add_trace(go.Bar(
                name="Remaining Gap",
                x=["Emergency Fund"],
                y=[plan["fund_gap"]],
                marker_color="#ef4444",
                text=[format_inr(plan["fund_gap"])],
                textposition="auto",
            ))
        fig_bar.update_layout(
            barmode="stack",
            title="Current Savings vs Target Cushion",
            yaxis_title="Amount (₹)",
            template="plotly_white",
            height=280,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # Scenarios Table & Contribution Affordability
    st.subheader("⏱️ Monthly Contribution Scenarios & Timeline")
    st.caption("How varying your monthly savings pace accelerates emergency preparedness.")

    scenarios = plan.get("contribution_scenarios", [])
    if scenarios:
        df_sc = pd.DataFrame(scenarios)
        df_display = df_sc.copy()
        df_display["monthly_amount"] = df_display["monthly_amount"].apply(format_inr)
        df_display["months_to_target"] = df_display["months_to_target"].apply(
            lambda m: f"{m} Months" if m is not None else "Unreachable"
        )

        st.dataframe(
            df_display.rename(
                columns={
                    "monthly_amount": "Monthly Allocation",
                    "months_to_target": "Time to Complete",
                    "completion_date": "Estimated Target Date",
                    "affordability_status": "Budget Affordability",
                }
            )[["Monthly Allocation", "Time to Complete", "Estimated Target Date", "Budget Affordability"]],
            hide_index=True,
            use_container_width=True,
        )


def _render_insurance_tab(
    assessment: Dict[str, Any], user_id: str = "default_user", db_path: Optional[str] = None
):
    """Render interactive Health & Life Insurance needs assessment."""
    st.subheader("🏥 Insurance Needs Assessment")
    st.caption("Evaluate your family's health safety net and estimate term life insurance requirements using capital needs analysis.")

    tab_health, tab_life, tab_acc = st.tabs(
        ["🏥 Health Insurance", "🕊️ Life Insurance Needs", "🩹 Accident & Disability Protection"]
    )

    # SUB-TAB 1: HEALTH INSURANCE
    with tab_health:
        h_eval = assessment["health_assessment"]

        col_h1, col_h2 = st.columns([1, 1.2])
        with col_h1:
            st.markdown("##### 🩺 Health Coverage Inputs")
            p_cov = st.number_input(
                "Personal Health Insurance (₹)",
                min_value=0.0,
                value=max(0.0, float(st.session_state.ins_inputs["health_personal_coverage"])),
                step=50000.0,
                help="Standalone policy owned directly by you (Individual or Family Floater).",
            )
            e_cov = st.number_input(
                "Employer Health Insurance (₹)",
                min_value=0.0,
                value=max(0.0, float(st.session_state.ins_inputs["health_employer_coverage"])),
                step=50000.0,
                help="Corporate group medical cover provided by employer.",
            )
            t_cov = st.number_input(
                "Target Protection Desired (₹)",
                min_value=100000.0,
                value=max(100000.0, float(st.session_state.ins_inputs["health_target_coverage"])),
                step=100000.0,
                help="Desired total family medical coverage (e.g. ₹10 Lakhs, ₹25 Lakhs, ₹50 Lakhs).",
            )
            members = st.number_input(
                "Number of Family Members Covered",
                min_value=1,
                max_value=10,
                value=max(1, int(st.session_state.ins_inputs["number_of_members"])),
                step=1,
            )
            pol_type = st.selectbox(
                "Policy Type",
                options=["Family Floater", "Individual"],
                index=0 if st.session_state.ins_inputs["health_policy_type"] == "Family Floater" else 1,
            )

            st.session_state.ins_inputs.update({
                "health_personal_coverage": p_cov,
                "health_employer_coverage": e_cov,
                "health_target_coverage": t_cov,
                "number_of_members": members,
                "health_policy_type": pol_type,
            })

        with col_h2:
            st.markdown("##### 📊 Health Coverage Summary")
            hc1, hc2, hc3 = st.columns(3)
            hc1.metric("Total Active Cover", format_inr(h_eval["total_current_coverage"]))
            hc2.metric("Protection Target", format_inr(h_eval["target_coverage"]))
            hc3.metric(
                "Coverage Gap",
                format_inr(h_eval["total_coverage_gap"]),
                delta="Under-Insured" if h_eval["total_coverage_gap"] > 0 else "Adequate",
                delta_color="inverse" if h_eval["total_coverage_gap"] > 0 else "normal",
            )

            st.info(f"**Assessment:** {h_eval['summary']}")

            # Chart
            fig_h = go.Figure()
            fig_h.add_trace(go.Bar(
                name="Personal Policy",
                x=["Coverage vs Target"],
                y=[h_eval["personal_coverage"]],
                marker_color="#10b981",
            ))
            fig_h.add_trace(go.Bar(
                name="Employer Policy",
                x=["Coverage vs Target"],
                y=[h_eval["employer_coverage"]],
                marker_color="#3b82f6",
            ))
            if h_eval["total_coverage_gap"] > 0:
                fig_h.add_trace(go.Bar(
                    name="Coverage Gap",
                    x=["Coverage vs Target"],
                    y=[h_eval["total_coverage_gap"]],
                    marker_color="#ef4444",
                ))
            fig_h.update_layout(
                barmode="stack",
                title="Health Insurance Composition (INR)",
                template="plotly_white",
                height=260,
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig_h, use_container_width=True)

        with st.expander("📋 Health Policy Review Checklist (Exclusions & Fine Print)", expanded=False):
            for item in h_eval.get("checklist", []):
                st.markdown(f"- {item}")

    # SUB-TAB 2: LIFE INSURANCE
    with tab_life:
        l_eval = assessment["life_assessment"]

        col_l1, col_l2 = st.columns([1, 1.2])
        with col_l1:
            st.markdown("##### 🕊️ Capital Needs Inputs")
            annual_inc = st.number_input(
                "Annual Take-Home Income (₹)",
                min_value=0.0,
                value=max(0.0, float(st.session_state.ins_inputs["annual_income"])),
                step=50000.0,
            )
            deps = st.number_input(
                "Financial Dependents",
                min_value=0,
                max_value=15,
                value=max(0, int(st.session_state.ins_inputs["dependents"])),
                step=1,
                help="Spouse, children, or elderly parents who depend on your income.",
            )
            multiplier = st.slider(
                "Income Replacement Multiplier (Years)",
                min_value=5.0,
                max_value=25.0,
                value=float(st.session_state.ins_inputs["life_income_multiplier_years"]),
                step=1.0,
                help="Standard thumb rule is 10x to 15x annual income.",
            )
            debts = st.number_input(
                "Outstanding Debt & Liabilities (₹)",
                min_value=0.0,
                value=max(0.0, float(st.session_state.ins_inputs["outstanding_debt"])),
                step=50000.0,
                help="Home loans, car loans, personal debts to be cleared.",
            )
            family_ob = st.number_input(
                "Future Goals & Obligations (₹)",
                min_value=0.0,
                value=max(0.0, float(st.session_state.ins_inputs["future_family_obligations"])),
                step=50000.0,
                help="Children higher education, marriage, and family commitments.",
            )
            assets = st.number_input(
                "Eligible Available Assets (₹)",
                min_value=0.0,
                value=max(0.0, float(st.session_state.ins_inputs["eligible_assets"])),
                step=50000.0,
                help="Liquid savings and investments available for family support.",
            )
            existing_life = st.number_input(
                "Current Active Term Life Cover (₹)",
                min_value=0.0,
                value=max(0.0, float(st.session_state.ins_inputs["life_existing_coverage"])),
                step=500000.0,
                help="Existing pure term life insurance sum assured.",
            )

            st.session_state.ins_inputs.update({
                "annual_income": annual_inc,
                "dependents": deps,
                "life_income_multiplier_years": multiplier,
                "outstanding_debt": debts,
                "future_family_obligations": family_ob,
                "eligible_assets": assets,
                "life_existing_coverage": existing_life,
            })

        with col_l2:
            st.markdown("##### 📊 Life Protection Needs Analysis")
            lc1, lc2, lc3 = st.columns(3)
            lc1.metric("Gross Need", format_inr(l_eval["gross_protection_need"]))
            lc2.metric("Existing Resources", format_inr(l_eval["total_existing_resources"]))
            lc3.metric(
                "Additional Life Gap",
                format_inr(l_eval["net_additional_need"]),
                delta="Need Term Cover" if l_eval["net_additional_need"] > 0 else "Adequate",
                delta_color="inverse" if l_eval["net_additional_need"] > 0 else "normal",
            )

            st.info(f"**Assessment:** {l_eval['summary']}")

            # Component breakdown table
            breakdown_data = [
                {"Component": f"Income Replacement ({multiplier:.0f} Yrs)", "Amount (₹)": l_eval["income_replacement_reserve"]},
                {"Component": "Outstanding Debt Liabilities", "Amount (₹)": l_eval["outstanding_liabilities"]},
                {"Component": "Future Obligations & Goals", "Amount (₹)": l_eval["future_family_obligations"] + l_eval["specified_goals"]},
                {"Component": "Less: Eligible Savings & Assets", "Amount (₹)": -l_eval["existing_eligible_assets"]},
                {"Component": "Less: Existing Life Insurance", "Amount (₹)": -l_eval["existing_life_insurance"]},
                {"Component": "Net Additional Term Cover Needed", "Amount (₹)": l_eval["net_additional_need"]},
            ]
            df_bd = pd.DataFrame(breakdown_data)
            df_bd["Amount (₹)"] = df_bd["Amount (₹)"].apply(format_inr)
            st.dataframe(df_bd, hide_index=True, use_container_width=True)

        with st.expander("ℹ️ Calculation Formulas & Methodology", expanded=False):
            for asmp in l_eval.get("assumptions", []):
                st.markdown(f"- {asmp}")

    # SUB-TAB 3: ACCIDENT & DISABILITY
    with tab_acc:
        acc_eval = assessment["accident_assessment"]

        col_a1, col_a2 = st.columns([1, 1.2])
        with col_a1:
            st.markdown("##### 🩹 Accident & Disability Inputs")
            has_accident = st.checkbox(
                "I currently have Personal Accident & Disability Insurance",
                value=bool(st.session_state.ins_inputs["has_accident_disability_cover"]),
            )
            acc_cover = 0.0
            if has_accident:
                acc_cover = st.number_input(
                    "Current Accident Sum Insured (₹)",
                    min_value=0.0,
                    value=max(0.0, float(st.session_state.ins_inputs["accident_cover_amount"])),
                    step=500000.0,
                )

            st.session_state.ins_inputs.update({
                "has_accident_disability_cover": has_accident,
                "accident_cover_amount": acc_cover,
            })

        with col_a2:
            st.markdown("##### 🛡️ Disability Protection Evaluation")
            st.metric("Benchmark Range", acc_eval["benchmark_recommended_range"])
            st.info(f"**Assessment:** {acc_eval['summary']}")

            st.markdown("###### Key Benefits to Verify:")
            for item in acc_eval.get("checklist", []):
                st.markdown(f"- {item}")

    st.markdown("---")
    # Save Assessment Button
    if st.button("💾 Save Insurance Assessment to Profile", key="btn_save_ins_assessment", type="primary"):
        succ, _, errs = save_insurance_assessment(assessment, user_id=user_id, db_path=db_path)
        if succ:
            st.success("🎉 Insurance assessment saved to your profile database!")
        else:
            for e in errs:
                st.error(e)


def _render_combined_dashboard_tab(
    scorecard: Dict[str, Any],
    recommendations: List[Dict[str, Any]],
    ef_plan: Dict[str, Any],
    ins_assessment: Dict[str, Any],
):
    """Render combined Multi-Pillar Scorecard and Prioritized Action Plan."""
    st.subheader("📊 Combined Financial Protection Dashboard")
    st.caption("A holistic overview of your financial defense across emergency cash, health, life, and disability pillars.")

    # Defense Pillars Overview Table
    st.markdown(f"#### 🛡️ Overall Protection Status: **{scorecard['overall_badge']}**")
    st.info(scorecard["summary_text"])

    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    cols = [col_p1, col_p2, col_p3, col_p4]
    for idx, p in enumerate(scorecard["pillars"]):
        with cols[idx]:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{p['pillar']}</div>
                    <div class="metric-value" style="font-size:1.4rem; color:{p['color']};">{p['metric']}</div>
                    <div style="font-size:0.85rem; margin-top:6px; font-weight:600;">{p['badge']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # Prioritized Action Plan
    st.subheader("🎯 Prioritized Financial Defense Action Plan")
    st.caption("Deterministic recommendations ranked by urgency to optimize your household resilience.")

    for idx, rec in enumerate(recommendations):
        pri = rec["priority"]
        badge_color = "#ef4444" if pri == "High" else ("#f59e0b" if pri == "Medium" else "#3b82f6")
        with st.container():
            st.markdown(
                f"""
                <div style="border-left: 4px solid {badge_color}; background-color: var(--secondary-background-color); padding: 14px 18px; border-radius: 8px; margin-bottom: 12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; font-size:1.05rem;">{idx + 1}. {rec['title']}</span>
                        <span style="background-color:{badge_color}; color:white; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600;">{pri} Priority</span>
                    </div>
                    <div style="margin-top:6px; font-size:0.9rem; opacity:0.9;"><strong>Why:</strong> {rec['reason']}</div>
                    <div style="margin-top:4px; font-size:0.9rem; color:var(--primary-color);"><strong>Action:</strong> {rec['suggested_action']}</div>
                    <div style="margin-top:4px; font-size:0.75rem; opacity:0.7;"><em>{rec['assumptions']}</em></div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_history_tab(user_id: str = "default_user", db_path: Optional[str] = None):
    """Render saved emergency fund plans and insurance assessments."""
    st.subheader("📜 Saved Plans & Assessment History")
    st.caption("Review past protection assessments and track how your safety cushion has strengthened over time.")

    col_h_ef, col_h_ins = st.columns(2)

    with col_h_ef:
        st.markdown("#### 🛡️ Emergency Fund Plan History")
        ef_hist = get_emergency_fund_history(user_id=user_id, db_path=db_path)
        if not ef_hist:
            st.info("No saved emergency fund plans found in database.")
        else:
            for p in ef_hist:
                col_p1, col_p2 = st.columns([3, 1])
                with col_p1:
                    status_badge = "🌟 Active" if p["is_latest"] else "Archived"
                    st.write(f"**{p['plan_name']}** ({status_badge})")
                    st.caption(
                        f"Target: {format_inr(p['target_amount'])} ({p['target_months']:.0f} Mo) | "
                        f"Savings: {format_inr(p['current_savings'])} | Saved: {p['created_at'][:19]}"
                    )
                with col_p2:
                    if st.button("🗑️ Delete", key=f"btn_del_ef_{p['id']}"):
                        delete_emergency_fund_plan(p["id"], user_id=user_id, db_path=db_path)
                        st.rerun()

    with col_h_ins:
        st.markdown("#### 🏥 Insurance Assessment History")
        ins_hist = get_insurance_assessment_history(user_id=user_id, db_path=db_path)
        if not ins_hist:
            st.info("No saved insurance assessments found in database.")
        else:
            for a in ins_hist:
                col_a1, col_a2 = st.columns([3, 1])
                with col_a1:
                    status_badge = "🌟 Active" if a["is_latest"] else "Archived"
                    st.write(f"**{a['assessment_name']}** ({status_badge})")
                    st.caption(
                        f"Health Gap: {format_inr(a['health_gap'])} | "
                        f"Life Gap: {format_inr(a['life_gap'])} | Saved: {a['created_at'][:19]}"
                    )
                with col_a2:
                    if st.button("🗑️ Delete", key=f"btn_del_ins_{a['id']}"):
                        delete_insurance_assessment(a["id"], user_id=user_id, db_path=db_path)
                        st.rerun()
