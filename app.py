import os

import pandas as pd
import plotly.express as px
import streamlit as st

from services.portfolio_service import analyze_portfolio
from utils.ai_summary import generate_portfolio_summary
from utils.benchmarks import generate_benchmark_report as _gen_bm
from utils.benchmarks import get_available_benchmarks
from utils.pdf_parser import EmptyPDFError, PDFReadError, extract_text, parse_funds


st.set_page_config(
    page_title="AI Money Mentor",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling using CSS variables for dark/light mode compatibility
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    /* Apply font family */
    html, body, [data-testid="stSidebar"], .stMarkdown {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Metric Card styling */
    .metric-card {
        background: linear-gradient(135deg, var(--secondary-background-color), var(--background-color));
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 22px;
        border-radius: 16px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
        text-align: center;
        margin-bottom: 15px;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
        border-color: var(--primary-color);
    }
    .metric-label {
        font-size: 0.85rem;
        color: var(--text-color);
        opacity: 0.75;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 1.75rem;
        color: var(--primary-color);
        font-weight: 800;
    }
    </style>
    """,
    unsafe_allow_html=True
)

if "result" not in st.session_state:
    st.session_state.result = None
if "summary" not in st.session_state:
    st.session_state.summary = None
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None
if "overlap_report" not in st.session_state:
    st.session_state.overlap_report = None
if "benchmark_report" not in st.session_state:
    st.session_state.benchmark_report = None

st.sidebar.title("💰 AI Money Mentor")
st.sidebar.subheader("Portfolio Control Panel")

uploaded_file = st.sidebar.file_uploader(
    "Upload CAMS CAS PDF",
    type=["pdf"]
)

if uploaded_file:
    if st.session_state.uploaded_file_name != uploaded_file.name:
        st.session_state.result = None
        st.session_state.summary = None
        st.session_state.uploaded_file_name = uploaded_file.name

if st.session_state.result is not None:
    if st.sidebar.button("🧹 Clear & Reset", use_container_width=True):
        st.session_state.result = None
        st.session_state.summary = None
        st.session_state.uploaded_file_name = None
        st.rerun()

st.sidebar.divider()
st.sidebar.markdown(
    """
    ### 📂 How to get your statement:
    1. Request a **Consolidated Account Statement (CAS)** from [CAMS Online](https://www.camsonline.com/).
    2. Choose **Detailed** statement (includes transaction history for XIRR calculation).
    3. Enter a password if required.
    4. Download the PDF statement.
    """
)

st.title("💰 AI Money Mentor")
st.caption("Mutual Fund Portfolio X-Ray & AI-Powered Advisory")
st.divider()

if uploaded_file and st.session_state.result is None:
    if st.sidebar.button("🚀 Analyze Portfolio", type="primary", use_container_width=True):
        try:
            with st.spinner("Analyzing Statement..."):
                with open("temp.pdf", "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Step 1: Extract PDF text — may raise PDFReadError or EmptyPDFError.
                text = extract_text("temp.pdf")

                # Step 2: Parse fund blocks from text.
                df = parse_funds(text)

                if df.empty:
                    st.error(
                        "❌ **No mutual fund data found.** "
                        "The PDF was readable but contained no CAMS scheme blocks. "
                        "Please upload a **Detailed** CAMS Consolidated Account Statement."
                    )
                    st.stop()

                # Step 3: Run portfolio analysis (XIRR + expense drag + overlap + benchmark).
                result, overlap_report, benchmark_report = analyze_portfolio(df)
                st.session_state.result = result
                st.session_state.overlap_report = overlap_report
                st.session_state.benchmark_report = benchmark_report

                # Step 4: Generate LLM recommendations.
                # ai_summary never raises — returns a user-friendly string on any error.
                ai_df = result.drop(columns=["transactions"], errors="ignore")
                portfolio_json = ai_df.to_dict(orient="records")

            with st.spinner("Consulting AI Money Mentor..."):
                summary = generate_portfolio_summary(portfolio_json)
                st.session_state.summary = summary

            st.success("✅ Analysis Complete!")
            st.rerun()

        except PDFReadError as exc:
            st.error(
                f"❌ **Could not read the PDF.** {exc} "
                "\n\nMake sure you uploaded a valid, non-encrypted CAMS PDF."
            )

        except EmptyPDFError as exc:
            st.error(f"❌ **PDF has no readable text.** {exc}")

        except ValueError as exc:
            # Raised by analyze_portfolio for missing columns or empty DataFrames.
            st.error(f"❌ **Portfolio data error:** {exc}")

        except OSError as exc:
            st.error(
                f"❌ **File system error** while saving the uploaded PDF: {exc}"
            )

        except Exception:
            st.error(
                "❌ **An unexpected error occurred.** "
                "Please try re-uploading your statement."
            )

        finally:
            # Always clean up the temporary PDF — never persist user data to disk.
            if os.path.exists("temp.pdf"):
                os.remove("temp.pdf")


def format_indian_currency(val: float | None) -> str:
    """Format a numeric value as an Indian-locale currency string."""
    if val is None or pd.isna(val):
        return "₹0.00"
    return f"₹{val:,.2f}"


if st.session_state.result is not None:
    df_metrics = st.session_state.result

    total_portfolio_value = df_metrics["current_value"].sum()

    # Value-weighted average XIRR; falls back to simple mean when value data is absent.
    valid_xirr_df = df_metrics.dropna(subset=["xirr", "current_value"])
    if not valid_xirr_df.empty and total_portfolio_value > 0:
        weighted_xirr = (
            (valid_xirr_df["xirr"] * valid_xirr_df["current_value"]).sum()
            / total_portfolio_value
        )
    else:
        weighted_xirr = df_metrics["xirr"].mean() if not df_metrics["xirr"].dropna().empty else 0.0

    total_annual_expense = df_metrics["annual_expense_cost"].sum()
    num_funds = df_metrics["scheme"].nunique()

    # 1. Summary Metrics Cards (4 Columns)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
            <div class="metric-card" title="Total current market value of all mutual fund holdings parsed from the statement.">
                <div class="metric-label">Total Portfolio Value</div>
                <div class="metric-value">{format_indian_currency(total_portfolio_value)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card" title="XIRR (Extended Internal Rate of Return) is your annualized return accounting for the exact dates and amounts of all transactions (purchases, SIPs, redemptions).">
                <div class="metric-label">Average XIRR (Weighted)</div>
                <div class="metric-value">{weighted_xirr:.2f}%</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card" title="Estimated annual fees paid to fund houses, calculated based on each scheme's expense ratio and current value.">
                <div class="metric-label">Total Annual Cost Drag</div>
                <div class="metric-value">{format_indian_currency(total_annual_expense)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col4:
        st.markdown(
            f"""
            <div class="metric-card" title="Total number of unique mutual fund schemes in your portfolio.">
                <div class="metric-label">Number of Funds</div>
                <div class="metric-value">{num_funds}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.write("")

    # 2. Charts & Key Insights
    layout_col1, layout_col2 = st.columns([3, 2])

    with layout_col1:
        st.subheader("📊 Portfolio Allocation")
        fig = px.pie(
            df_metrics,
            values="current_value",
            names="scheme",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig.update_traces(
            textposition="inside",
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>Value: ₹%{value:,.2f}<br>Percent: %{percent:.1%}<extra></extra>"
        )
        fig.update_layout(
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            height=300,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Outfit, sans-serif")
        )
        st.plotly_chart(fig, use_container_width=True)

    with layout_col2:
        st.subheader("💡 Portfolio Insights")

        largest_holding = df_metrics.loc[df_metrics["current_value"].idxmax()]
        highest_drag = df_metrics.loc[df_metrics["annual_expense_cost"].idxmax()]
        valid_xirr_only = df_metrics.dropna(subset=["xirr"])
        if not valid_xirr_only.empty:
            top_perf = valid_xirr_only.loc[valid_xirr_only["xirr"].idxmax()]
            top_perf_text = f"**{top_perf['scheme']}** ({top_perf['xirr']:.2f}%)"
        else:
            top_perf_text = "*N/A (No transactions history found)*"
            
        st.markdown(
            f"""
            <div style="background-color: var(--secondary-background-color); border: 1px solid rgba(128,128,128,0.15); padding: 20px; border-radius: 12px; height: 300px; display: flex; flex-direction: column; justify-content: center;">
                <p style="margin: 8px 0; font-size: 0.95rem;">🎯 <b>Largest Holding:</b><br><span style="color: var(--primary-color); font-weight: 600;">{largest_holding['scheme']}</span> ({format_indian_currency(largest_holding['current_value'])})</p>
                <p style="margin: 8px 0; font-size: 0.95rem;">📈 <b>Top Performing Fund (XIRR):</b><br>{top_perf_text}</p>
                <p style="margin: 8px 0; font-size: 0.95rem;">💸 <b>Highest Cost Drag:</b><br><span style="color: #ef4444; font-weight: 600;">{highest_drag['scheme']}</span> ({format_indian_currency(highest_drag['annual_expense_cost'])}/year)</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.write("")

    # Row 2: Performance Comparison & Expense Cost Comparison
    bar_col1, bar_col2 = st.columns(2)

    with bar_col1:
        st.subheader("📈 Annualized Return (XIRR) by Fund")
        df_xirr_sorted = df_metrics.dropna(subset=["xirr"]).sort_values(by="xirr", ascending=False)
        fig_xirr = px.bar(
            df_xirr_sorted,
            x="scheme",
            y="xirr",
            labels={"scheme": "Scheme Name", "xirr": "XIRR (%)"},
            color="xirr",
            color_continuous_scale=px.colors.sequential.Tealgrn
        )
        fig_xirr.update_layout(
            xaxis_title=None,
            yaxis_title="XIRR (%)",
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(t=20, b=20, l=10, r=10),
            height=320,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Outfit, sans-serif")
        )
        fig_xirr.update_traces(
            hovertemplate="<b>%{x}</b><br>XIRR: %{y:.2f}%<extra></extra>"
        )
        st.plotly_chart(fig_xirr, use_container_width=True)

    with bar_col2:
        st.subheader("💸 Annual Expense Drag (Fees) by Fund")
        df_expense_sorted = df_metrics.dropna(subset=["annual_expense_cost"]).sort_values(by="annual_expense_cost", ascending=False)
        fig_expense = px.bar(
            df_expense_sorted,
            x="scheme",
            y="annual_expense_cost",
            labels={"scheme": "Scheme Name", "annual_expense_cost": "Annual Cost Drag (₹)"},
            color="annual_expense_cost",
            color_continuous_scale=px.colors.sequential.OrRd
        )
        fig_expense.update_layout(
            xaxis_title=None,
            yaxis_title="Annual Drag (₹)",
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(t=20, b=20, l=10, r=10),
            height=320,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Outfit, sans-serif")
        )
        fig_expense.update_traces(
            hovertemplate="<b>%{x}</b><br>Annual Drag: ₹%{y:,.2f}<extra></extra>"
        )
        st.plotly_chart(fig_expense, use_container_width=True)

    st.divider()

    # 3. AI Advisor Analysis
    st.subheader("🤖 AI Mentor Analysis")
    if st.session_state.summary:
        st.markdown(
            """
            <div style="border-left: 4px solid var(--primary-color); padding-left: 15px; margin-bottom: 20px; background-color: var(--secondary-background-color); padding: 15px; border-radius: 4px;">
            """,
            unsafe_allow_html=True
        )
        st.markdown(st.session_state.summary)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("AI Analysis could not be generated. Please check your environment keys.")

    st.divider()

    # 4. Details Table
    st.subheader("🔍 Fund-wise Details")
    
    # Columns configuration to rename/format columns and hide 'transactions'
    column_config = {
        "transactions": None,  # Hide technical columns like transactions
        "scheme": st.column_config.TextColumn(
            "Scheme Name",
            help="Name of the Mutual Fund Scheme",
            width="large"
        ),
        "current_value": st.column_config.NumberColumn(
            "Current Value",
            format="₹%,.2f",
            help="Current value of holdings"
        ),
        "xirr": st.column_config.NumberColumn(
            "XIRR (%)",
            format="%.2f%%",
            help="Annualized Internal Rate of Return"
        ),
        "expense_ratio": st.column_config.NumberColumn(
            "Expense Ratio (%)",
            format="%.2f%%",
            help="Annual Expense Ratio of the Fund"
        ),
        "annual_expense_cost": st.column_config.NumberColumn(
            "Annual Expense Drag",
            format="₹%,.2f",
            help="Annual cost impact of the expense ratio"
        ),
        "folio": st.column_config.TextColumn("Folio Number"),
        "units": st.column_config.NumberColumn("Units", format="%.3f"),
        "nav": st.column_config.NumberColumn("NAV (₹)", format="₹%.4f")
    }

    # Hide dataframe index and apply column config
    st.dataframe(
        df_metrics,
        column_config=column_config,
        use_container_width=True,
        hide_index=True
    )

    # -------------------------------------------------------------------------
    # 5. Fund Overlap Detection
    # -------------------------------------------------------------------------
    st.divider()
    st.subheader("🔁 Fund Overlap Detection")

    overlap = st.session_state.overlap_report

    if overlap is None:
        st.info(
            "ℹ️ Overlap data is not available for your funds yet. "
            "Holdings data for your schemes will be added to `data/fund_holdings.py` "
            "as the database grows.",
            icon="ℹ️"
        )
    elif not overlap["pairs"]:
        st.success("✅ Only one fund found in the holdings database — no overlap to compute.")
    else:
        # --- Risk summary badges ---
        high_count   = len(overlap["high_overlap_pairs"])
        conc_count   = len(overlap["concentrated_stocks"])

        badge_col1, badge_col2, badge_col3 = st.columns(3)
        with badge_col1:
            st.markdown(
                f"""
                <div class="metric-card" title="Total number of unique pairs of funds in your portfolio compared for stock holding overlap.">
                    <div class="metric-label">Fund Pairs Analysed</div>
                    <div class="metric-value">{len(overlap['pairs'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with badge_col2:
            color = "#ef4444" if high_count > 0 else "#10b981"
            st.markdown(
                f"""
                <div class="metric-card" title="Number of fund pairs sharing 60% or more overlap in their underlying stock holdings, indicating low diversification.">
                    <div class="metric-label">High Overlap Pairs (&ge;60%)</div>
                    <div class="metric-value" style="color:{color}">{high_count}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with badge_col3:
            color2 = "#f59e0b" if conc_count > 0 else "#10b981"
            st.markdown(
                f"""
                <div class="metric-card" title="Number of individual stocks that appear in 3 or more of your mutual funds, creating higher single-stock concentration risk.">
                    <div class="metric-label">Concentrated Stocks</div>
                    <div class="metric-value" style="color:{color2}">{conc_count}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.write("")

        # --- Pairwise overlap table ---
        overlap_table_col, freq_col = st.columns([3, 2])

        with overlap_table_col:
            st.markdown("**Pairwise Overlap Matrix**")
            _RISK_COLOR = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
            pairs_display = [
                {
                    "Fund A": p["fund_a"],
                    "Fund B": p["fund_b"],
                    "Common Holdings": ", ".join(p["common_holdings"]) or "None",
                    "Common #": p["common_count"],
                    "Union #": p["union_count"],
                    "Overlap %": p["overlap_pct"],
                    "Risk": _RISK_COLOR.get(p["risk_level"], "") + " " + p["risk_level"],
                }
                for p in overlap["pairs"]
            ]
            st.dataframe(
                pairs_display,
                use_container_width=True,
                hide_index=True,
            )

        with freq_col:
            st.markdown("**Stock Frequency Across Funds**")
            freq = overlap["stock_frequency"]
            if freq:
                freq_df = pd.DataFrame(
                    [{"Stock": stock, "Funds": len(funds)} for stock, funds in freq.items()]
                ).head(15)   # Top 15 most-duplicated stocks
                fig_freq = px.bar(
                    freq_df,
                    x="Funds",
                    y="Stock",
                    orientation="h",
                    color="Funds",
                    color_continuous_scale=px.colors.sequential.Burg,
                )
                fig_freq.update_layout(
                    xaxis_title="Number of Funds",
                    yaxis_title=None,
                    showlegend=False,
                    coloraxis_showscale=False,
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=350,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Outfit, sans-serif"),
                    yaxis=dict(autorange="reversed"),
                )
                fig_freq.update_traces(
                    hovertemplate="<b>%{y}</b><br>Held by %{x} fund(s)<extra></extra>"
                )
                st.plotly_chart(fig_freq, use_container_width=True)

        # --- Concentrated stocks warning ---
        if overlap["concentrated_stocks"]:
            st.write("")
            st.warning(
                "⚠️ **Concentrated Stocks** — these holdings appear across 3 or more "
                "of your funds, amplifying single-stock risk:"
            )
            for stock, funds in overlap["concentrated_stocks"].items():
                st.markdown(f"- **{stock}** → {', '.join(funds)}")

    # -------------------------------------------------------------------------
    # 6. Benchmark Comparison
    # -------------------------------------------------------------------------
    st.divider()
    st.subheader("📊 Benchmark Comparison")

    bm_report = st.session_state.benchmark_report

    # Selectors — let the user pick benchmark and period interactively.
    bm_options = get_available_benchmarks()
    period_options = ["1Y", "3Y", "5Y", "10Y"]

    bm_sel_col, period_sel_col, _ = st.columns([2, 1, 3])
    with bm_sel_col:
        bm_choice = st.selectbox(
            "Compare against",
            options=list(bm_options.keys()),
            format_func=lambda k: bm_options[k],
            index=0,
            key="bm_selector",
        )
    with period_sel_col:
        period_choice = st.selectbox(
            "Period",
            options=period_options,
            index=1,
            key="period_selector",
        )

    # Re-compute on selector change — uses already-analysed df, no PDF re-parse needed.
    try:
        bm_report = _gen_bm(
            df_metrics.drop(columns=["transactions"], errors="ignore"),
            benchmark_key=bm_choice,
            period=period_choice,
        )
    except Exception:
        bm_report = None  # Handled gracefully by the None check below.

    if bm_report is None:
        st.info("Benchmark comparison data is unavailable for this portfolio.")
    else:
        # --- Portfolio-level alpha badges ---
        bm_badge1, bm_badge2, bm_badge3, bm_badge4 = st.columns(4)

        with bm_badge1:
            st.markdown(
                f"""
                <div class="metric-card" title="The annualized return of the selected benchmark index over the chosen period.">
                    <div class="metric-label">Benchmark ({period_choice})</div>
                    <div class="metric-value">{bm_report['benchmark_return']:.1f}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with bm_badge2:
            alpha = bm_report["portfolio_alpha"]
            alpha_str = f"{alpha:+.2f} pp" if alpha is not None else "N/A"
            alpha_color = "#10b981" if (alpha or 0) > 0 else "#ef4444"
            st.markdown(
                f"""
                <div class="metric-card" title="Portfolio Alpha measures the outperformance (in percentage points) of your portfolio compared to the selected benchmark index. A positive alpha indicates outperformance.">
                    <div class="metric-label">Portfolio Alpha</div>
                    <div class="metric-value" style="color:{alpha_color}">{alpha_str}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with bm_badge3:
            st.markdown(
                f"""
                <div class="metric-card" title="Number of funds in your portfolio that have a higher XIRR than the selected benchmark's return.">
                    <div class="metric-label">Funds Outperforming</div>
                    <div class="metric-value" style="color:#10b981">{bm_report['outperforming']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with bm_badge4:
            st.markdown(
                f"""
                <div class="metric-card" title="Number of funds in your portfolio that have a lower XIRR than the selected benchmark's return.">
                    <div class="metric-label">Funds Underperforming</div>
                    <div class="metric-value" style="color:#ef4444">{bm_report['underperforming']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # --- Insight banner ---
        st.write("")
        st.info(bm_report["insight"])

        # --- Fund-by-fund alpha chart + comparison table ---
        bm_chart_col, bm_table_col = st.columns([3, 2])

        valid_comps = [c for c in bm_report["fund_comparisons"] if c["alpha_pp"] is not None]

        with bm_chart_col:
            if valid_comps:
                bm_df = pd.DataFrame(valid_comps)
                bm_df["Color"] = bm_df["alpha_pp"].apply(
                    lambda v: "Outperform" if v > 0.5 else ("Underperform" if v < -0.5 else "In Line")
                )
                _color_map = {
                    "Outperform":   "#10b981",
                    "In Line":      "#f59e0b",
                    "Underperform": "#ef4444",
                }
                fig_bm = px.bar(
                    bm_df,
                    x="scheme",
                    y="alpha_pp",
                    color="Color",
                    color_discrete_map=_color_map,
                    labels={"scheme": "", "alpha_pp": "Alpha (pp)"},
                    title=f"Alpha vs {bm_report['benchmark_name']} ({period_choice})",
                )
                fig_bm.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
                fig_bm.update_layout(
                    showlegend=True,
                    legend_title_text="Verdict",
                    margin=dict(t=40, b=20, l=10, r=10),
                    height=320,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Outfit, sans-serif"),
                )
                fig_bm.update_traces(
                    hovertemplate="<b>%{x}</b><br>Alpha: %{y:+.2f} pp<extra></extra>"
                )
                st.plotly_chart(fig_bm, use_container_width=True)
            else:
                st.info("No XIRR data available to plot alpha chart.")

        with bm_table_col:
            st.markdown(f"**Fund vs {bm_report['benchmark_name']} ({period_choice})**")
            _VERDICT_ICON = {"OUTPERFORM": "🟢", "UNDERPERFORM": "🔴", "IN LINE": "🟡", "N/A": "➖"}
            table_rows = [
                {
                    "Fund": c["scheme"],
                    "XIRR (%)": f"{c['fund_xirr']:.2f}" if c["fund_xirr"] is not None else "N/A",
                    "Benchmark (%)": f"{c['benchmark_return']:.1f}",
                    "Alpha (pp)": f"{c['alpha_pp']:+.2f}" if c["alpha_pp"] is not None else "N/A",
                    "Verdict": _VERDICT_ICON.get(c["verdict"], "") + " " + c["verdict"],
                }
                for c in bm_report["fund_comparisons"]
            ]
            st.dataframe(table_rows, use_container_width=True, hide_index=True)

else:
    # App Landing Page State
    st.markdown(
        """
        <div style="text-align: center; padding: 40px 10px;">
            <h2 style="font-size: 2.3rem; font-weight: 800; background: linear-gradient(to right, #3b82f6, #10b981); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 15px;">
                Your Personal Mutual Fund Health Check
            </h2>
            <p style="font-size: 1.05rem; opacity: 0.8; max-width: 650px; margin: 0 auto 35px auto; line-height: 1.6;">
                Get an instant X-Ray analysis of your mutual fund portfolio. Understand your true returns (XIRR), identify expensive funds (Expense Drag), and receive tailored AI recommendations to optimize your wealth.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        st.markdown(
            """
            <div style="background-color: var(--secondary-background-color); border: 1px solid rgba(128,128,128,0.12); padding: 25px; border-radius: 16px; text-align: center; height: 100%;">
                <div style="font-size: 2.5rem; margin-bottom: 12px;">📈</div>
                <h4 style="margin: 0 0 10px 0; font-weight: 700;">Precision XIRR</h4>
                <p style="font-size: 0.9rem; opacity: 0.8; margin: 0; line-height: 1.5;">Calculates exact annualized returns using your transaction dates, giving you the real yield of your investments.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_f2:
        st.markdown(
            """
            <div style="background-color: var(--secondary-background-color); border: 1px solid rgba(128,128,128,0.12); padding: 25px; border-radius: 16px; text-align: center; height: 100%;">
                <div style="font-size: 2.5rem; margin-bottom: 12px;">💸</div>
                <h4 style="margin: 0 0 10px 0; font-weight: 700;">Expense Drag Analysis</h4>
                <p style="font-size: 0.9rem; opacity: 0.8; margin: 0; line-height: 1.5;">Uncovers the compound drag of high expense ratios and shows the exact yearly cost impact of direct vs. regular funds.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_f3:
        st.markdown(
            """
            <div style="background-color: var(--secondary-background-color); border: 1px solid rgba(128,128,128,0.12); padding: 25px; border-radius: 16px; text-align: center; height: 100%;">
                <div style="font-size: 2.5rem; margin-bottom: 12px;">🤖</div>
                <h4 style="margin: 0 0 10px 0; font-weight: 700;">AI Advisor Recommendations</h4>
                <p style="font-size: 0.9rem; opacity: 0.8; margin: 0; line-height: 1.5;">Get clear, customized suggestions to optimize asset classes, reduce costs, and accelerate compounding.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.write("")
    st.write("")
    
    st.info("👈 **Get started by uploading your CAMS Consolidated Account Statement (CAS) PDF in the sidebar.**", icon="ℹ️")