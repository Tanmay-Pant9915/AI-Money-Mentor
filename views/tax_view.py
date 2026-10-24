"""
views/tax_view.py
Streamlit view for Task 7: Tax Optimization & Tax Planning.
Provides side-by-side Old vs New Regime comparison, deduction planner,
what-if tax-saving simulator, capital gains analysis, and prioritized recommendations.
"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data.tax_rules import DEDUCTION_LIMITS, SUPPORTED_FINANCIAL_YEARS, get_tax_rules
from services.profile_service import format_inr
from services.tax_planning_service import (
    delete_tax_scenario,
    get_saved_tax_scenarios,
    get_tax_profile,
    get_user_tax_context,
    save_tax_assessment,
    save_tax_profile,
    save_tax_scenario,
)
from utils.capital_gains_calculator import (
    analyze_cas_holdings_capital_gains,
    calculate_transaction_capital_gain,
)
from utils.tax_calculator import (
    DeductionBreakdown,
    IncomeBreakdown,
    calculate_hra_exemption,
    compare_tax_regimes,
)
from utils.tax_recommendations import generate_tax_recommendations
from utils.tax_scenario_calculator import (
    PRESET_TAX_SAVING_MOVES,
    ProposedTaxMove,
    simulate_tax_scenario,
)


def render_tax_view(user_id: str = "default_user", db_path: str = None) -> None:
    """Render the main Tax Optimization & Planning interface."""
    st.header("🏷️ Tax Optimization & Tax Planning")
    st.markdown(
        """
        Evaluate your income tax liability, compare the **Old vs. New Tax Regimes**, plan eligible deductions,
        simulate tax-saving investment scenarios, and analyze mutual fund capital gains under the **Finance Act 2024**.
        """
    )

    # 1. Load baseline context from Financial Profile
    ctx = get_user_tax_context(user_id=user_id, db_path=db_path)

    # Financial Year selection
    fy_keys = list(SUPPORTED_FINANCIAL_YEARS.keys())
    col_fy, col_age = st.columns([2, 1])
    with col_fy:
        selected_fy = st.selectbox(
            "Select Financial Year",
            options=fy_keys,
            format_func=lambda k: SUPPORTED_FINANCIAL_YEARS[k]["label"],
            index=0,
            help="Choose applicable Financial Year. Rules and slabs update accordingly.",
        )
    with col_age:
        user_age = st.number_input(
            "Taxpayer Age",
            min_value=18,
            max_value=120,
            value=max(18, int(ctx.get("age", 30))),
            step=1,
            help="Tax slabs under Old Regime differ for Senior Citizens (60+) and Super Senior Citizens (80+).",
        )

    # Load stored tax profile if available
    saved_tax_prof = get_tax_profile(user_id=user_id, financial_year=selected_fy, db_path=db_path)

    # Pre-populate defaults
    if saved_tax_prof:
        init_salary = float(saved_tax_prof.get("salary_gross", 0.0))
        init_house = float(saved_tax_prof.get("house_property_net", 0.0))
        init_interest = float(saved_tax_prof.get("other_sources_interest", 0.0))
        init_other = float(saved_tax_prof.get("other_sources_other", 0.0))
        init_biz = float(saved_tax_prof.get("business_profession_net", 0.0))
        init_tds = float(saved_tax_prof.get("taxes_paid", 0.0))
        saved_deds = saved_tax_prof.get("deductions", {})
        init_80c = float(saved_deds.get("sec_80c", 0.0))
        init_80d_self = float(saved_deds.get("sec_80d_self", 0.0))
        init_80d_parents = float(saved_deds.get("sec_80d_parents", 0.0))
        init_self_senior = bool(saved_deds.get("is_self_senior", user_age >= 60))
        init_parents_senior = bool(saved_deds.get("is_parents_senior", False))
        init_nps_1b = float(saved_deds.get("sec_80ccd_1b", 0.0))
        init_nps_2 = float(saved_deds.get("sec_80ccd_2", 0.0))
        init_24b = float(saved_deds.get("sec_24b", 0.0))
        init_80e = float(saved_deds.get("sec_80e", 0.0))
        init_80g = float(saved_deds.get("sec_80g", 0.0))
        init_hra = float(saved_deds.get("hra_exemption", 0.0))
    else:
        init_salary = float(ctx.get("annual_salary", 0.0))
        init_house = 0.0
        init_interest = 0.0
        init_other = 0.0
        init_biz = 0.0
        init_tds = 0.0
        init_80c = 0.0
        init_80d_self = 0.0
        init_80d_parents = 0.0
        init_self_senior = user_age >= 60
        init_parents_senior = False
        init_nps_1b = 0.0
        init_nps_2 = 0.0
        init_24b = 0.0
        init_80e = 0.0
        init_80g = 0.0
        init_hra = 0.0

    # UI Tabs
    tab_comp, tab_inputs, tab_sim, tab_cg, tab_recs, tab_history = st.tabs([
        "⚖️ Old vs New Regime Comparison",
        "📝 Income & Deductions Breakdown",
        "🧪 What-If Tax Simulator",
        "📈 Mutual Fund Capital Gains",
        "🎯 Recommendations & Action Plan",
        "📜 Saved Scenarios",
    ])

    # Build active models from current session state or initial defaults
    active_income = IncomeBreakdown(
        salary_gross=st.session_state.get(f"tax_salary_{selected_fy}", init_salary),
        house_property_net=st.session_state.get(f"tax_house_{selected_fy}", init_house),
        other_sources_interest=st.session_state.get(f"tax_interest_{selected_fy}", init_interest),
        other_sources_other=st.session_state.get(f"tax_other_{selected_fy}", init_other),
        business_profession_net=st.session_state.get(f"tax_biz_{selected_fy}", init_biz),
    )
    active_deductions = DeductionBreakdown(
        sec_80c=st.session_state.get(f"tax_80c_{selected_fy}", init_80c),
        sec_80d_self=st.session_state.get(f"tax_80d_self_{selected_fy}", init_80d_self),
        sec_80d_parents=st.session_state.get(f"tax_80d_parents_{selected_fy}", init_80d_parents),
        is_self_senior=st.session_state.get(f"tax_self_senior_{selected_fy}", init_self_senior),
        is_parents_senior=st.session_state.get(f"tax_parents_senior_{selected_fy}", init_parents_senior),
        sec_80ccd_1b=st.session_state.get(f"tax_nps_1b_{selected_fy}", init_nps_1b),
        sec_80ccd_2=st.session_state.get(f"tax_nps_2_{selected_fy}", init_nps_2),
        sec_24b=st.session_state.get(f"tax_24b_{selected_fy}", init_24b),
        sec_80e=st.session_state.get(f"tax_80e_{selected_fy}", init_80e),
        sec_80g=st.session_state.get(f"tax_80g_{selected_fy}", init_80g),
        hra_exemption=st.session_state.get(f"tax_hra_{selected_fy}", init_hra),
    )
    active_tds = float(st.session_state.get(f"tax_tds_{selected_fy}", init_tds))

    # Evaluate comparison
    comparison = compare_tax_regimes(
        income=active_income,
        deductions=active_deductions,
        financial_year=selected_fy,
        age=user_age,
        taxes_paid=active_tds,
    )

    # Capital gains analysis on CAS portfolio if available
    cas_df = st.session_state.get("result")
    cg_summary = analyze_cas_holdings_capital_gains(cas_df, financial_year=selected_fy)

    # Recommendations
    recommendations = generate_tax_recommendations(
        comparison=comparison,
        income=active_income,
        deductions=active_deductions,
        taxes_paid=active_tds,
        emergency_months=ctx.get("emergency_runway_months", 6.0),
        monthly_surplus=ctx.get("monthly_surplus", 0.0),
        has_capital_gains=cg_summary.get("has_data", False),
        capital_gains_summary=cg_summary,
    )

    # -------------------------------------------------------------------------
    # TAB 1: OLD VS NEW REGIME COMPARISON
    # -------------------------------------------------------------------------
    with tab_comp:
        _render_regime_comparison_tab(comparison, active_tds, user_id, db_path)

    # -------------------------------------------------------------------------
    # TAB 2: INCOME & DEDUCTIONS BREAKDOWN FORM
    # -------------------------------------------------------------------------
    with tab_inputs:
        _render_income_deductions_tab(
            selected_fy=selected_fy,
            user_age=user_age,
            init_salary=init_salary,
            init_house=init_house,
            init_interest=init_interest,
            init_other=init_other,
            init_biz=init_biz,
            init_tds=init_tds,
            init_80c=init_80c,
            init_80d_self=init_80d_self,
            init_80d_parents=init_80d_parents,
            init_self_senior=init_self_senior,
            init_parents_senior=init_parents_senior,
            init_nps_1b=init_nps_1b,
            init_nps_2=init_nps_2,
            init_24b=init_24b,
            init_80e=init_80e,
            init_80g=init_80g,
            init_hra=init_hra,
            user_id=user_id,
            db_path=db_path,
        )

    # -------------------------------------------------------------------------
    # TAB 3: WHAT-IF TAX SIMULATOR
    # -------------------------------------------------------------------------
    with tab_sim:
        _render_scenario_simulator_tab(
            baseline_income=active_income,
            baseline_deductions=active_deductions,
            financial_year=selected_fy,
            user_age=user_age,
            monthly_surplus=ctx.get("monthly_surplus", 0.0),
            emergency_months=ctx.get("emergency_runway_months", 6.0),
            user_id=user_id,
            db_path=db_path,
        )

    # -------------------------------------------------------------------------
    # TAB 4: MUTUAL FUND CAPITAL GAINS
    # -------------------------------------------------------------------------
    with tab_cg:
        _render_capital_gains_tab(cg_summary, selected_fy)

    # -------------------------------------------------------------------------
    # TAB 5: RECOMMENDATIONS & ACTION PLAN
    # -------------------------------------------------------------------------
    with tab_recs:
        _render_recommendations_tab(recommendations, comparison)

    # -------------------------------------------------------------------------
    # TAB 6: SAVED SCENARIOS
    # -------------------------------------------------------------------------
    with tab_history:
        _render_saved_scenarios_tab(user_id=user_id, financial_year=selected_fy, db_path=db_path)


def _render_regime_comparison_tab(
    comparison: Any,
    taxes_paid: float,
    user_id: str,
    db_path: Optional[str],
) -> None:
    """Render side-by-side comparison between Old and New regimes."""
    st.subheader(f"📊 Regime Comparison Analysis ({comparison.financial_year})")

    old_r = comparison.old_regime
    new_r = comparison.new_regime

    # Recommendation Banner
    if comparison.recommended_regime == "New Regime":
        st.success(
            f"🎉 **Recommendation: New Tax Regime saves {format_inr(comparison.tax_difference)}** "
            f"({comparison.percentage_savings:.1f}% lower tax). {comparison.summary_explanation}"
        )
    elif comparison.recommended_regime == "Old Regime":
        st.info(
            f"🎯 **Recommendation: Old Tax Regime saves {format_inr(comparison.tax_difference)}** "
            f"({comparison.percentage_savings:.1f}% lower tax). {comparison.summary_explanation}"
        )
    else:
        st.warning("⚖️ **Both regimes result in the identical tax liability** for your income level.")

    # High-level Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Gross Total Income", format_inr(old_r.gross_total_income))
    with m2:
        st.metric(
            "Old Regime Tax",
            format_inr(old_r.total_tax_liability),
            delta=f"-{format_inr(comparison.tax_difference)}" if comparison.recommended_regime == "Old Regime" else None,
            delta_color="normal",
        )
    with m3:
        st.metric(
            "New Regime Tax",
            format_inr(new_r.total_tax_liability),
            delta=f"-{format_inr(comparison.tax_difference)}" if comparison.recommended_regime == "New Regime" else None,
            delta_color="normal",
        )
    with m4:
        st.metric("Net Tax Savings", format_inr(comparison.tax_difference))

    # Break-even deduction insight
    st.markdown(
        f"""
        > 💡 **Break-Even Deduction Requirement:** Under the Old Regime, you need eligible deductions and exemptions 
        > of at least **{format_inr(comparison.break_even_deductions)}** to match the New Regime's tax liability. 
        > Your currently eligible Old Regime deductions: **{format_inr(old_r.total_deductions_exemptions)}**.
        """
    )

    # Comparison Table
    st.markdown("### 📋 Side-by-Side Tax Computation Sheet")
    comp_data = [
        {
            "Computation Component": "1. Gross Total Income",
            "Old Regime (₹)": format_inr(old_r.gross_total_income),
            "New Regime (₹)": format_inr(new_r.gross_total_income),
            "Statutory Note": "Total reported income across all heads",
        },
        {
            "Computation Component": "2. Standard Deduction (Salary)",
            "Old Regime (₹)": format_inr(old_r.standard_deduction),
            "New Regime (₹)": format_inr(new_r.standard_deduction),
            "Statutory Note": "₹50k (Old) vs ₹75k (New) under Budget 2024",
        },
        {
            "Computation Component": "3. HRA Exemption (Sec 10(13A))",
            "Old Regime (₹)": format_inr(old_r.hra_exemption),
            "New Regime (₹)": "Not Eligible",
            "Statutory Note": "Exemption on rent paid (Old regime only)",
        },
        {
            "Computation Component": "4. Home Loan Interest (Sec 24b)",
            "Old Regime (₹)": format_inr(old_r.sec_24b_deduction),
            "New Regime (₹)": "Not Eligible",
            "Statutory Note": "Self-occupied house interest up to ₹2,00,000",
        },
        {
            "Computation Component": "5. Chapter VI-A Deductions (80C, 80D, NPS)",
            "Old Regime (₹)": format_inr(old_r.chapter_via_deductions),
            "New Regime (₹)": format_inr(new_r.chapter_via_deductions),
            "Statutory Note": "80CCD(2) employer NPS eligible in both regimes",
        },
        {
            "Computation Component": "6. Total Deductions & Exemptions",
            "Old Regime (₹)": format_inr(old_r.total_deductions_exemptions),
            "New Regime (₹)": format_inr(new_r.total_deductions_exemptions),
            "Statutory Note": "Sum of all allowable deductions",
        },
        {
            "Computation Component": "7. Total Taxable Income (Sec 288A)",
            "Old Regime (₹)": format_inr(old_r.taxable_income),
            "New Regime (₹)": format_inr(new_r.taxable_income),
            "Statutory Note": "Rounded to nearest ₹10",
        },
        {
            "Computation Component": "8. Tax Computed at Slab Rates",
            "Old Regime (₹)": format_inr(old_r.tax_at_slab_rates),
            "New Regime (₹)": format_inr(new_r.tax_at_slab_rates),
            "Statutory Note": "Progressive tax bracket rates",
        },
        {
            "Computation Component": "9. Section 87A Tax Rebate",
            "Old Regime (₹)": format_inr(old_r.sec_87a_rebate),
            "New Regime (₹)": format_inr(new_r.sec_87a_rebate),
            "Statutory Note": "Up to ₹12.5k (Old <= 5L) / ₹25k (New <= 7L)",
        },
        {
            "Computation Component": "10. Marginal Relief (Section 87A)",
            "Old Regime (₹)": "N/A",
            "New Regime (₹)": format_inr(new_r.marginal_relief_87a),
            "Statutory Note": "Tax capped at income exceeding ₹7,00,000",
        },
        {
            "Computation Component": "11. Health & Education Cess (4%)",
            "Old Regime (₹)": format_inr(old_r.health_education_cess),
            "New Regime (₹)": format_inr(new_r.health_education_cess),
            "Statutory Note": "4% on tax and surcharge",
        },
        {
            "Computation Component": "12. TOTAL TAX LIABILITY (Sec 288B)",
            "Old Regime (₹)": format_inr(old_r.total_tax_liability),
            "New Regime (₹)": format_inr(new_r.total_tax_liability),
            "Statutory Note": "Final gross income tax liability",
        },
        {
            "Computation Component": "13. TDS & Advance Tax Paid",
            "Old Regime (₹)": format_inr(old_r.tds_and_taxes_paid),
            "New Regime (₹)": format_inr(new_r.tds_and_taxes_paid),
            "Statutory Note": "Taxes already deducted or prepaid",
        },
        {
            "Computation Component": "14. Net Tax Payable / (Refund)",
            "Old Regime (₹)": format_inr(old_r.net_tax_payable) if old_r.net_tax_payable > 0 else f"({format_inr(old_r.potential_refund)} Refund)",
            "New Regime (₹)": format_inr(new_r.net_tax_payable) if new_r.net_tax_payable > 0 else f"({format_inr(new_r.potential_refund)} Refund)",
            "Statutory Note": "Balance payable before filing ITR",
        },
    ]

    df_comp = pd.DataFrame(comp_data)
    st.table(df_comp)

    # Interactive Bar Chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Tax at Slab Rates",
        x=["Old Regime", "New Regime"],
        y=[old_r.tax_at_slab_rates, new_r.tax_at_slab_rates],
        marker_color="#3B82F6",
    ))
    fig.add_trace(go.Bar(
        name="Section 87A Rebate",
        x=["Old Regime", "New Regime"],
        y=[-old_r.sec_87a_rebate, -new_r.sec_87a_rebate],
        marker_color="#10B981",
    ))
    fig.add_trace(go.Bar(
        name="Cess (4%)",
        x=["Old Regime", "New Regime"],
        y=[old_r.health_education_cess, new_r.health_education_cess],
        marker_color="#F59E0B",
    ))
    fig.update_layout(
        barmode="relative",
        title="Tax Composition Comparison: Old vs New Regime",
        yaxis_title="Amount (₹)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Save Assessment Button
    if st.button("💾 Save Assessment Snapshot", key="btn_save_tax_assessment"):
        recs = generate_tax_recommendations(comparison, old_r, old_r.deduction_details)
        save_tax_assessment(user_id=user_id, comparison=comparison, recommendations=recs, db_path=db_path)
        st.success("✅ Tax calculation snapshot successfully saved to history!")


def _render_income_deductions_tab(
    selected_fy: str,
    user_age: int,
    init_salary: float,
    init_house: float,
    init_interest: float,
    init_other: float,
    init_biz: float,
    init_tds: float,
    init_80c: float,
    init_80d_self: float,
    init_80d_parents: float,
    init_self_senior: bool,
    init_parents_senior: bool,
    init_nps_1b: float,
    init_nps_2: float,
    init_24b: float,
    init_80e: float,
    init_80g: float,
    init_hra: float,
    user_id: str,
    db_path: Optional[str],
) -> None:
    """Render interactive form for editing income sources, deductions, and exemptions."""
    st.subheader(f"📝 Annual Income & Deduction Details ({selected_fy})")
    st.markdown("Enter your annual figures below. All fields update the calculation automatically.")

    with st.form("form_tax_inputs"):
        st.markdown("#### 1. Annual Income Heads")
        c1, c2 = st.columns(2)
        with c1:
            salary_gross = st.number_input(
                "Gross Annual Salary Income (₹)",
                min_value=0.0,
                value=max(0.0, float(init_salary)),
                step=10000.0,
                help="Total salary before standard deduction or exemptions.",
            )
            house_property_net = st.number_input(
                "Income / (Loss) from House Property (₹)",
                value=float(init_house),
                step=5000.0,
                help="Net rental income after 30% statutory maintenance deduction and municipal taxes.",
            )
            biz_net = st.number_input(
                "Business / Professional Net Income (₹)",
                min_value=0.0,
                value=max(0.0, float(init_biz)),
                step=10000.0,
                help="Net taxable business or freelance/consulting earnings.",
            )
        with c2:
            interest_income = st.number_input(
                "Savings Bank & FD Interest Income (₹)",
                min_value=0.0,
                value=max(0.0, float(init_interest)),
                step=5000.0,
                help="Total interest earned across savings bank accounts, fixed deposits, and recurring deposits.",
            )
            other_income = st.number_input(
                "Other Taxable Income (Dividends, etc.) (₹)",
                min_value=0.0,
                value=max(0.0, float(init_other)),
                step=5000.0,
                help="Dividends, lottery, or other sources.",
            )
            tds_paid = st.number_input(
                "TDS Deducted & Advance Tax Already Paid (₹)",
                min_value=0.0,
                value=max(0.0, float(init_tds)),
                step=5000.0,
                help="Total tax credits from Form 26AS / AIS.",
            )

        st.markdown("---")
        st.markdown("#### 2. Deductions & Exemptions (Chapter VI-A & Salary Exemptions)")

        # HRA Exemption Calculator Expander
        with st.expander("🏠 HRA Exemption Calculator (Optional)"):
            ch1, ch2, ch3, ch4 = st.columns(4)
            with ch1:
                hra_rec = st.number_input("Annual HRA Received", min_value=0.0, value=0.0, step=5000.0)
            with ch2:
                basic_sal = st.number_input("Annual Basic Salary", min_value=0.0, value=max(0.0, salary_gross * 0.50), step=10000.0)
            with ch3:
                rent_paid = st.number_input("Annual Rent Paid", min_value=0.0, value=0.0, step=5000.0)
            with ch4:
                is_metro = st.checkbox("Residing in Metro City (Delhi, Mumbai, Kolkata, Chennai)")

            calc_hra = calculate_hra_exemption(hra_rec, basic_sal, rent_paid, is_metro)
            if hra_rec > 0 and rent_paid > 0:
                st.info(f"Calculated eligible HRA exemption: **{format_inr(calc_hra['eligible_exemption'])}**")
                auto_hra = calc_hra["eligible_exemption"]
            else:
                auto_hra = init_hra

        d1, d2 = st.columns(2)
        with d1:
            sec_80c = st.number_input(
                "Section 80C (PPF, EPF, ELSS, Life Ins, Principal) (Max ₹1.5L)",
                min_value=0.0,
                value=max(0.0, float(init_80c)),
                step=5000.0,
                help="Old Regime only. Capped at ₹1,50,000.",
            )
            sec_80d_self = st.number_input(
                "Section 80D - Health Insurance (Self & Family)",
                min_value=0.0,
                value=max(0.0, float(init_80d_self)),
                step=2500.0,
                help="Max ₹25,000 (or ₹50,000 if senior citizen). Old Regime only.",
            )
            sec_80d_parents = st.number_input(
                "Section 80D - Health Insurance (Parents)",
                min_value=0.0,
                value=max(0.0, float(init_80d_parents)),
                step=2500.0,
                help="Max ₹25,000 (or ₹50,000 if parents are senior citizens). Old Regime only.",
            )
            parents_senior = st.checkbox("Parents are Senior Citizens (Age 60+)", value=init_parents_senior)
            sec_80ccd_1b = st.number_input(
                "Section 80CCD(1B) - Additional NPS Tier 1 (Max ₹50k)",
                min_value=0.0,
                value=max(0.0, float(init_nps_1b)),
                step=5000.0,
                help="Voluntary NPS contribution up to ₹50,000. Old Regime only.",
            )

        with d2:
            sec_80ccd_2 = st.number_input(
                "Section 80CCD(2) - Employer NPS Contribution",
                min_value=0.0,
                value=max(0.0, float(init_nps_2)),
                step=5000.0,
                help="Employer NPS contribution (up to 14% of basic). Allowed in BOTH Old and New Regimes!",
            )
            sec_24b = st.number_input(
                "Section 24(b) - Home Loan Interest (Self-Occupied)",
                min_value=0.0,
                value=max(0.0, float(init_24b)),
                step=5000.0,
                help="Interest on housing loan up to ₹2,00,000. Old Regime only.",
            )
            sec_80e = st.number_input(
                "Section 80E - Education Loan Interest",
                min_value=0.0,
                value=max(0.0, float(init_80e)),
                step=5000.0,
                help="Interest paid on loan for higher education. Old Regime only.",
            )
            sec_80g = st.number_input(
                "Section 80G - Charitable Donations",
                min_value=0.0,
                value=max(0.0, float(init_80g)),
                step=2500.0,
                help="Donations to eligible charitable institutions. Old Regime only.",
            )
            hra_claimed = st.number_input(
                "HRA Exemption Claimed (Sec 10(13A))",
                min_value=0.0,
                value=max(0.0, float(auto_hra)),
                step=5000.0,
                help="Eligible HRA exemption under Old Regime.",
            )

        submit_save = st.form_submit_button("💾 Save & Recalculate Tax Profile", use_container_width=True)

    if submit_save:
        inc_model = IncomeBreakdown(
            salary_gross=salary_gross,
            house_property_net=house_property_net,
            other_sources_interest=interest_income,
            other_sources_other=other_income,
            business_profession_net=biz_net,
        )
        ded_model = DeductionBreakdown(
            sec_80c=sec_80c,
            sec_80d_self=sec_80d_self,
            sec_80d_parents=sec_80d_parents,
            is_self_senior=user_age >= 60,
            is_parents_senior=parents_senior,
            sec_80ccd_1b=sec_80ccd_1b,
            sec_80ccd_2=sec_80ccd_2,
            sec_24b=sec_24b,
            sec_80e=sec_80e,
            sec_80g=sec_80g,
            hra_exemption=hra_claimed,
        )

        save_tax_profile(
            user_id=user_id,
            financial_year=selected_fy,
            age=user_age,
            income=inc_model,
            deductions=ded_model,
            taxes_paid=tds_paid,
            db_path=db_path,
        )

        # Store in session state for instant view update
        st.session_state[f"tax_salary_{selected_fy}"] = salary_gross
        st.session_state[f"tax_house_{selected_fy}"] = house_property_net
        st.session_state[f"tax_interest_{selected_fy}"] = interest_income
        st.session_state[f"tax_other_{selected_fy}"] = other_income
        st.session_state[f"tax_biz_{selected_fy}"] = biz_net
        st.session_state[f"tax_tds_{selected_fy}"] = tds_paid
        st.session_state[f"tax_80c_{selected_fy}"] = sec_80c
        st.session_state[f"tax_80d_self_{selected_fy}"] = sec_80d_self
        st.session_state[f"tax_80d_parents_{selected_fy}"] = sec_80d_parents
        st.session_state[f"tax_parents_senior_{selected_fy}"] = parents_senior
        st.session_state[f"tax_nps_1b_{selected_fy}"] = sec_80ccd_1b
        st.session_state[f"tax_nps_2_{selected_fy}"] = sec_80ccd_2
        st.session_state[f"tax_24b_{selected_fy}"] = sec_24b
        st.session_state[f"tax_80e_{selected_fy}"] = sec_80e
        st.session_state[f"tax_80g_{selected_fy}"] = sec_80g
        st.session_state[f"tax_hra_{selected_fy}"] = hra_claimed

        st.success("✅ Tax profile saved! Switch to Tab 1 to see the updated regime comparison.")
        st.rerun()


def _render_scenario_simulator_tab(
    baseline_income: IncomeBreakdown,
    baseline_deductions: DeductionBreakdown,
    financial_year: str,
    user_age: int,
    monthly_surplus: float,
    emergency_months: float,
    user_id: str,
    db_path: Optional[str],
) -> None:
    """Render interactive what-if tax saving scenario simulator."""
    st.subheader("🧪 What-If Tax-Saving Decision Simulator")
    st.markdown(
        """
        Simulate proposed investments or deductible expenses to see your **actual incremental tax reduction**, 
        cash-flow impact, and lock-in requirements. Scenarios are strictly temporary until you save them.
        """
    )

    col_presets, col_custom = st.columns([1, 1])
    with col_presets:
        st.markdown("#### Quick Preset Scenarios")
        selected_presets = st.multiselect(
            "Select Preset Tax Moves",
            options=list(PRESET_TAX_SAVING_MOVES.keys()),
            format_func=lambda k: PRESET_TAX_SAVING_MOVES[k].description,
            default=["ELSS_MAX", "NPS_80CCD_1B"],
            help="Choose standard tax-saving investment strategies.",
        )

    with col_custom:
        st.markdown("#### Custom Move")
        custom_name = st.text_input("Custom Investment Name", value="Additional Health Insurance")
        custom_amt = st.number_input("Custom Amount (₹)", min_value=0.0, value=0.0, step=5000.0)
        custom_cat = st.selectbox("Category", options=["80D", "80C", "80CCD_2", "24B", "CUSTOM"])

    # Build moves
    proposed_moves: List[ProposedTaxMove] = []
    for p_key in selected_presets:
        proposed_moves.append(PRESET_TAX_SAVING_MOVES[p_key])

    if custom_amt > 0:
        proposed_moves.append(
            ProposedTaxMove(
                category=custom_cat,
                description=custom_name,
                proposed_amount=custom_amt,
                lock_in_note="Custom user proposed tax move.",
            )
        )

    if not proposed_moves:
        st.info("Select one or more preset moves or enter a custom amount above to simulate tax savings.")
        return

    # Simulate
    scenario_title = st.text_input("Scenario Name", value="My Proposed Tax-Saving Plan")
    sim_result = simulate_tax_scenario(
        scenario_name=scenario_title,
        baseline_income=baseline_income,
        baseline_deductions=baseline_deductions,
        proposed_moves=proposed_moves,
        financial_year=financial_year,
        age=user_age,
        monthly_surplus=monthly_surplus,
        emergency_fund_months=emergency_months,
    )

    # Display Results
    st.markdown("---")
    st.markdown("### 📊 Simulation Results")

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("Total Proposed Outflow", format_inr(sim_result.total_proposed_outflow))
    with s2:
        st.metric(
            "Effective Tax Saved",
            format_inr(sim_result.effective_tax_saved),
            delta=f"{sim_result.tax_savings_roi_pct:.1f}% ROI",
        )
    with s3:
        st.metric("Net Out-of-Pocket Outflow", format_inr(sim_result.net_cash_outflow))
    with s4:
        st.metric("Revised Optimal Regime", sim_result.revised_recommended)

    st.info(sim_result.actionable_summary)

    if sim_result.affordability_warning:
        st.warning(f"⚠️ **Cash Flow Notice:** {sim_result.affordability_warning}")

    if sim_result.lock_in_warnings:
        with st.expander("🔒 Statutory Lock-In & Liquidity Conditions"):
            for w in sim_result.lock_in_warnings:
                st.write(f"- {w}")

    # Save Named Scenario
    if st.button("💾 Save This Scenario", key="btn_save_sim_scen"):
        save_tax_scenario(user_id=user_id, scenario_result=sim_result, db_path=db_path)
        st.success(f"✅ Scenario '{sim_result.scenario_name}' saved! View it in the 'Saved Scenarios' tab.")


def _render_capital_gains_tab(cg_summary: Dict[str, Any], financial_year: str) -> None:
    """Render capital gains portfolio analysis and interactive calculator."""
    st.subheader(f"📈 Mutual Fund Capital Gains Tax Analysis ({financial_year})")

    # Statutory rules under Finance Act 2024
    st.markdown(
        r"""
        > 📜 **Finance (No. 2) Act, 2024 Provisions (Effective 23 July 2024):**
        > - **Equity Mutual Funds:** Short-term gains (held $\le$ 12 months) taxed @ **20%** (Section 111A). 
        >   Long-term gains (held > 12 months) taxed @ **12.5%** on gains exceeding annual **₹1,25,000 exemption** (Section 112A).
        > - **Specified Debt Mutual Funds:** Taxed at individual slab rates under Section 50AA.
        > - **Health & Education Cess:** 4% applies on all capital gains tax liabilities.
        """
    )

    # CAS Portfolio Analysis
    if cg_summary.get("has_data"):
        st.markdown("### 📊 CAMS CAS Portfolio Unrealized Gains")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Portfolio Valuation", format_inr(cg_summary["total_portfolio_value"]))
        with c2:
            st.metric("Total Invested", format_inr(cg_summary["total_invested_amount"]))
        with c3:
            st.metric("Unrealized Gain", format_inr(cg_summary["total_unrealized_gain"]))
        with c4:
            st.metric(
                "LTCG Exemption Left",
                format_inr(cg_summary["exemption_remaining"]),
                help=f"Annual ₹1.25 Lakh exemption limit under Section 112A.",
            )

        st.caption(f"Estimated tax liability if entire portfolio was redeemed today: **{format_inr(cg_summary['estimated_tax_if_redeemed_today'])}**")

        with st.expander("🔍 View Per-Scheme Capital Gains Breakdown"):
            holdings_rows = []
            for h in cg_summary.get("holdings", []):
                holdings_rows.append({
                    "Scheme Name": h["scheme"],
                    "Category": h["category"],
                    "Current Value": format_inr(h["current_value"]),
                    "Invested Amount": format_inr(h["invested_amount"]),
                    "Unrealized Gain": format_inr(h["unrealized_gain"]),
                    "Oldest Purchase": h["oldest_purchase_date"],
                    "Holding Classification": h["holding_period_label"],
                })
            st.dataframe(pd.DataFrame(holdings_rows), use_container_width=True)
    else:
        st.info("ℹ️ Upload a CAMS CAS PDF on the main dashboard to view automated mutual fund portfolio capital gains analysis.")

    # Interactive Transaction Capital Gains Calculator
    st.markdown("---")
    st.markdown("### 🧮 Standalone Capital Gains Calculator")
    st.markdown("Calculate capital gains and tax liability for any specific mutual fund or equity transaction.")

    with st.form("form_cg_calc"):
        g1, g2, g3 = st.columns(3)
        with g1:
            asset_title = st.text_input("Fund / Asset Name", value="Parag Parikh Flexi Cap Fund")
            asset_cat = st.selectbox("Asset Category", options=["EQUITY", "DEBT", "OTHER"])
        with g2:
            buy_date = st.date_input("Purchase Date", value=date(2023, 1, 15))
            sell_date = st.date_input("Sale Date", value=date.today())
        with g3:
            cost_basis = st.number_input("Total Cost of Investment (₹)", min_value=0.0, value=100000.0, step=10000.0)
            sale_value = st.number_input("Total Sale Value (₹)", min_value=0.0, value=180000.0, step=10000.0)

        calc_cg_btn = st.form_submit_button("Calculate Capital Gain & Tax", use_container_width=True)

    if calc_cg_btn:
        try:
            res_cg = calculate_transaction_capital_gain(
                asset_name=asset_title,
                asset_category=asset_cat,
                purchase_date=buy_date,
                sale_date=sell_date,
                cost_basis=cost_basis,
                sale_proceeds=sale_value,
                financial_year=financial_year,
            )

            res_cols = st.columns(4)
            res_cols[0].metric("Holding Duration", f"{res_cg.holding_period_months:.1f} Months", f"{res_cg.holding_period_days} Days")
            res_cols[1].metric("Net Gain / (Loss)", format_inr(res_cg.net_capital_gain))
            res_cols[2].metric("Taxable Gain", format_inr(res_cg.taxable_gain), f"Type: {res_cg.gain_type}")
            res_cols[3].metric("Total Tax (incl. Cess)", format_inr(res_cg.total_tax), f"Rate: {res_cg.tax_rate_pct:.1f}%")

            st.success(f"📌 **Statutory Assessment:** {res_cg.note}")
        except Exception as e:
            st.error(f"Error calculating capital gain: {e}")

    # Statutory Disclaimers
    st.markdown("---")
    st.caption(
        "⚠️ **Data Limitations & Disclaimers:** CAMS CAS statements summarize holdings and purchase transactions. "
        "Actual realized capital gains for income-tax return (ITR) filing require broker Capital Gains Statements / AIS Form 26AS "
        "to accurately account for grandfathering (pre-2018 units), indexation rules, and tax-loss harvesting."
    )


def _render_recommendations_tab(recs: List[Any], comparison: Any) -> None:
    """Render prioritized, explainable tax-planning action items."""
    st.subheader("🎯 Prioritized Tax-Planning Action Plan")

    if not recs:
        st.info("No specific tax adjustments required based on your current inputs.")
        return

    priority_badges = {
        "CRITICAL": "🚨 CRITICAL",
        "HIGH": "⚠️ HIGH",
        "MEDIUM": "💡 MEDIUM",
        "LOW": "ℹ️ LOW",
    }
    badge_colors = {
        "CRITICAL": "red",
        "HIGH": "orange",
        "MEDIUM": "blue",
        "LOW": "gray",
    }

    for i, r in enumerate(recs):
        p_badge = priority_badges.get(r.priority, r.priority)
        with st.container():
            st.markdown(f"#### {p_badge}: {r.title}")
            st.markdown(f"**Why this matters:** {r.reason}")
            st.markdown(f"👉 **Suggested Action:** `{r.suggested_action}`")
            if r.potential_tax_saving:
                st.markdown(f"💰 **Estimated Tax Relief:** **{format_inr(r.potential_tax_saving)}**")
            if r.assumptions_note:
                st.caption(f"Assumptions: {r.assumptions_note}")
            st.divider()

    # Statutory Educational Disclaimer
    st.info(
        "⚖️ **Legal & Regulatory Disclaimer:** AI Money Mentor provides educational tax estimation tools for informational "
        "purposes. We are not a Chartered Accountant or SEBI-registered tax advisor. Final tax liabilities depend on official "
        "provisions of the Income-tax Act, 1961, verification of documents, and applicable notifications by CBDT. "
        "Please consult a qualified tax professional before filing your Income Tax Return."
    )


def _render_saved_scenarios_tab(user_id: str, financial_year: str, db_path: Optional[str]) -> None:
    """Render saved what-if tax scenarios and management controls."""
    st.subheader(f"📜 Saved Tax Planning Scenarios ({financial_year})")

    scenarios = get_saved_tax_scenarios(user_id=user_id, financial_year=financial_year, db_path=db_path)

    if not scenarios:
        st.info("No saved scenarios yet. Use the 'What-If Tax Simulator' tab to test and save planning scenarios.")
        return

    for s in scenarios:
        det = s.get("details", {})
        scen_id = s.get("id")
        with st.expander(f"📁 {s.get('scenario_name')} (Outflow: {format_inr(s.get('total_outflow', 0))})"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Proposed Outflow", format_inr(s.get("total_outflow", 0)))
            c2.metric("Effective Tax Saved", format_inr(s.get("tax_saved", 0)))
            c3.metric("Net Cost", format_inr(det.get("net_cash_outflow", 0)))
            c4.metric("Revised Regime", det.get("revised_recommended", "N/A"))

            st.write(f"**Summary:** {det.get('actionable_summary', 'N/A')}")

            moves = det.get("proposed_moves", [])
            if moves:
                st.write("**Included Moves:**")
                for m in moves:
                    st.write(f"- {m.get('description')}: {format_inr(m.get('proposed_amount', 0))}")

            if st.button("🗑️ Delete Scenario", key=f"del_scen_{scen_id}"):
                delete_tax_scenario(scenario_id=scen_id, user_id=user_id, db_path=db_path)
                st.success("Scenario deleted!")
                st.rerun()
