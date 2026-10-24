"""
views/profile_view.py
Streamlit UI view for Financial Profile management and Goal tracking.
"""
from datetime import date, datetime, timedelta
import streamlit as st

from services.profile_service import (
    VALID_EMPLOYMENT_STATUSES,
    calculate_profile_metrics,
    format_inr,
    get_profile,
    save_profile,
    validate_goal_data,
    validate_profile_data,
)


def render_profile_view():
    st.header("👤 Financial Profile & Goals")
    st.caption("Manage your income, expenses, assets, liabilities, and track financial goals.")
    st.divider()

    # Load existing profile
    profile = get_profile(user_id="default_user")

    # Session state for editing toggle
    if "is_editing_profile" not in st.session_state:
        st.session_state.is_editing_profile = profile is None

    # Top action bar
    if profile is not None and not st.session_state.is_editing_profile:
        col_btn1, col_btn2 = st.columns([6, 1])
        with col_btn2:
            if st.button("✏️ Edit Profile", use_container_width=True, type="secondary"):
                st.session_state.is_editing_profile = True
                st.rerun()

        _render_saved_profile_summary(profile)
    else:
        _render_profile_form(profile)


def _render_saved_profile_summary(profile: dict):
    metrics = profile.get("metrics") or calculate_profile_metrics(profile, profile.get("goals", []))

    st.subheader(f"Welcome back, {profile.get('name', 'Investor')}!")
    st.write(
        f"**Age:** {profile.get('age')} | "
        f"**Employment:** {profile.get('employment_status')} | "
        f"**Dependents:** {profile.get('dependents', 0)}"
    )

    st.markdown("### 📊 Monthly Cash Flow Snapshot")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)

    with m_col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Monthly Take-Home</div>
                <div class="metric-value">{format_inr(metrics['monthly_income'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m_col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Total Monthly Expenses</div>
                <div class="metric-value" style="color: #f59e0b;">{format_inr(metrics['total_monthly_expenses'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m_col3:
        surplus_color = "#ef4444" if metrics["is_deficit"] else "#10b981"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{metrics['surplus_label']}</div>
                <div class="metric-value" style="color: {surplus_color};">{format_inr(metrics['monthly_surplus'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m_col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Emergency Runway</div>
                <div class="metric-value">{metrics['emergency_months']} mos</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if metrics["is_deficit"]:
        st.warning(
            f"⚠️ **Monthly Deficit Alert:** Your monthly expenses ({format_inr(metrics['total_monthly_expenses'])}) "
            f"exceed your income ({format_inr(metrics['monthly_income'])}). "
            f"You are spending {format_inr(abs(metrics['monthly_surplus']))} more than you earn each month."
        )

    st.markdown("### 🏦 Balance Sheet & Net Worth")
    b_col1, b_col2, b_col3, b_col4 = st.columns(4)

    with b_col1:
        st.metric("Liquid Savings / Cash", format_inr(metrics["savings_liquid"]))
    with b_col2:
        st.metric("Investments", format_inr(metrics["existing_investments"]))
    with b_col3:
        st.metric("Outstanding Debt", format_inr(metrics["outstanding_debt"]))
    with b_col4:
        st.metric("Estimated Net Worth", format_inr(metrics["net_worth"]))

    st.markdown("### 🎯 Financial Goals")
    goals = profile.get("goals", [])
    if not goals:
        st.info("No financial goals configured yet. Click **Edit Profile** to set up your milestone targets.")
    else:
        for g in goals:
            target = float(g.get("target_amount") or 0)
            current = float(g.get("current_amount") or 0)
            pct = min(1.0, (current / target)) if target > 0 else 0.0

            g_col1, g_col2 = st.columns([3, 1])
            with g_col1:
                st.write(f"**{g.get('name')}** (Target: {g.get('target_date')})")
                st.progress(pct, text=f"{format_inr(current)} of {format_inr(target)} ({int(pct*100)}%)")
            with g_col2:
                remaining = max(0.0, target - current)
                st.caption(f"Remaining: {format_inr(remaining)}")

    st.caption(f"Profile last updated: {profile.get('updated_at', 'N/A')[:19]}")


def _render_profile_form(existing_profile: dict = None):
    st.subheader("Edit Financial Profile")
    st.caption("Please fill in your current financial details. All data is saved securely in your local database.")

    # Defaults
    defaults = existing_profile or {}

    with st.form("financial_profile_form", clear_on_submit=False):
        st.markdown("#### 1. Personal & Professional Information")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            name = st.text_input("Name / Display Name *", value=str(defaults.get("name", "")).strip())
            age = st.number_input(
                "Age (Years) *",
                min_value=18,
                max_value=120,
                value=int(defaults.get("age", 30)),
                step=1,
            )
        with col_p2:
            curr_emp = defaults.get("employment_status", "Salaried Employee")
            emp_idx = VALID_EMPLOYMENT_STATUSES.index(curr_emp) if curr_emp in VALID_EMPLOYMENT_STATUSES else 0
            employment_status = st.selectbox("Employment Status *", VALID_EMPLOYMENT_STATUSES, index=emp_idx)
            dependents = st.number_input(
                "Financial Dependents",
                min_value=0,
                max_value=20,
                value=int(defaults.get("dependents", 0)),
                step=1,
            )

        st.markdown("#### 2. Monthly Income & Cash Outflows (INR)")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            income = st.number_input(
                "Monthly Take-Home Income (₹) *",
                min_value=0.0,
                value=float(defaults.get("monthly_income", 100000.0)),
                step=5000.0,
                format="%.2f",
            )
            essential = st.number_input(
                "Essential Living Expenses (₹) *",
                help="Rent, groceries, utilities, school fees, essential bills",
                min_value=0.0,
                value=float(defaults.get("essential_expenses", 40000.0)),
                step=2000.0,
                format="%.2f",
            )
            discretionary = st.number_input(
                "Discretionary Expenses (₹) *",
                help="Dining out, entertainment, shopping, vacations",
                min_value=0.0,
                value=float(defaults.get("discretionary_expenses", 15000.0)),
                step=1000.0,
                format="%.2f",
            )
        with col_c2:
            other = st.number_input(
                "Other Monthly Expenses (₹)",
                min_value=0.0,
                value=float(defaults.get("other_expenses", 0.0)),
                step=1000.0,
                format="%.2f",
            )
            debt_repay = st.number_input(
                "Monthly Debt Repayments / EMIs (₹)",
                help="Home loan EMI, car loan EMI, personal loan, credit card minimums",
                min_value=0.0,
                value=float(defaults.get("monthly_debt_repayment", 10000.0)),
                step=2000.0,
                format="%.2f",
            )

        st.markdown("#### 3. Assets & Liabilities (INR)")
        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            savings = st.number_input(
                "Liquid Cash & Bank Savings (₹)",
                min_value=0.0,
                value=float(defaults.get("savings_liquid", 200000.0)),
                step=10000.0,
                format="%.2f",
            )
        with col_a2:
            debt = st.number_input(
                "Total Outstanding Debt Balance (₹)",
                min_value=0.0,
                value=float(defaults.get("outstanding_debt", 500000.0)),
                step=25000.0,
                format="%.2f",
            )
        with col_a3:
            investments = st.number_input(
                "Approximate Existing Investments (₹)",
                help="Mutual funds, stocks, PPF, EPF, NPS outside this CAS",
                min_value=0.0,
                value=float(defaults.get("existing_investments", 300000.0)),
                step=25000.0,
                format="%.2f",
            )

        submit_profile = st.form_submit_button("💾 Save Financial Profile", type="primary", use_container_width=True)

    # Goals management outside form for dynamic controls
    st.markdown("#### 4. Financial Goals Tracker")
    st.caption("Add milestones like buying a home, emergency fund, or child education.")

    if "edit_goals_list" not in st.session_state:
        st.session_state.edit_goals_list = [dict(g) for g in defaults.get("goals", [])]

    # Show existing goals in state
    if not st.session_state.edit_goals_list:
        st.info("No goals added yet. Use the tool below to add your first goal.")
    else:
        for idx, g in enumerate(st.session_state.edit_goals_list):
            g_c1, g_c2, g_c3, g_c4, g_c5 = st.columns([3, 2, 2, 2, 1])
            with g_c1:
                g["name"] = st.text_input(f"Goal Name #{idx+1}", value=g.get("name", ""), key=f"g_name_{idx}")
            with g_c2:
                g["target_amount"] = st.number_input(
                    f"Target (₹) #{idx+1}",
                    min_value=0.0,
                    value=float(g.get("target_amount", 100000.0)),
                    step=10000.0,
                    key=f"g_amt_{idx}",
                )
            with g_c3:
                g["current_amount"] = st.number_input(
                    f"Saved (₹) #{idx+1}",
                    min_value=0.0,
                    value=float(g.get("current_amount", 0.0)),
                    step=5000.0,
                    key=f"g_cur_{idx}",
                )
            with g_c4:
                d_val = g.get("target_date")
                if isinstance(d_val, str):
                    try:
                        d_obj = datetime.strptime(d_val, "%Y-%m-%d").date()
                    except ValueError:
                        d_obj = date.today() + timedelta(days=365)
                elif isinstance(d_val, (date, datetime)):
                    d_obj = d_val if isinstance(d_val, date) else d_val.date()
                else:
                    d_obj = date.today() + timedelta(days=365)

                g["target_date"] = st.date_input(
                    f"Target Date #{idx+1}",
                    value=d_obj,
                    min_value=date.today(),
                    key=f"g_date_{idx}",
                ).strftime("%Y-%m-%d")
            with g_c5:
                st.write("")
                st.write("")
                if st.button("🗑️", key=f"del_g_{idx}"):
                    st.session_state.edit_goals_list.pop(idx)
                    st.rerun()

    # Add new goal button
    if st.button("➕ Add Another Goal"):
        st.session_state.edit_goals_list.append({
            "name": "New Goal",
            "target_amount": 100000.0,
            "current_amount": 0.0,
            "target_date": (date.today() + timedelta(days=365)).strftime("%Y-%m-%d"),
        })
        st.rerun()

    # Handle profile submission
    if submit_profile:
        profile_data = {
            "name": name,
            "age": age,
            "employment_status": employment_status,
            "monthly_income": income,
            "essential_expenses": essential,
            "discretionary_expenses": discretionary,
            "other_expenses": other,
            "monthly_debt_repayment": debt_repay,
            "savings_liquid": savings,
            "outstanding_debt": debt,
            "existing_investments": investments,
            "dependents": dependents,
        }

        is_valid, errors, warnings = validate_profile_data(profile_data)

        # Validate goals
        goal_errors = []
        for g in st.session_state.edit_goals_list:
            g_valid, g_errs = validate_goal_data(g)
            if not g_valid:
                goal_errors.extend(g_errs)

        all_errors = errors + goal_errors

        if all_errors:
            for e in all_errors:
                st.error(f"❌ {e}")
        else:
            for w in warnings:
                st.warning(f"⚠️ {w}")

            # Save to SQLite database
            save_profile(
                profile_data=profile_data,
                goals=st.session_state.edit_goals_list,
                user_id="default_user",
            )
            st.success("✅ Profile and goals saved successfully!")
            st.session_state.is_editing_profile = False
            st.rerun()

    if existing_profile is not None:
        if st.button("Cancel & Return to Summary"):
            st.session_state.is_editing_profile = False
            st.rerun()
