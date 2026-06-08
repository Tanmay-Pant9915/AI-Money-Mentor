"""
utils/benchmarks.py — Benchmark Comparison Engine
==================================================

ARCHITECTURE
------------
Three layers:

  1. DATA LAYER  — BenchmarkIndex TypedDict holding annualised return snapshots.
  2. MATH LAYER  — compare_fund_to_benchmark() computes outperformance / alpha.
  3. REPORT LAYER — generate_benchmark_report() assembles the full portfolio view.

MATHEMATICS
-----------
Given fund XIRR and benchmark CAGR (both in %):

    Alpha (pp)   =  XIRR_fund  −  Benchmark_return
    Relative %   =  (Alpha / |Benchmark_return|) × 100   [benchmark ≠ 0]

Alpha is expressed in percentage-point (pp) terms — the standard used in
SEBI-mandated fund fact-sheets.  A positive alpha means the fund beat the
index for the chosen period.

BENCHMARK DATA
--------------
Trailing-period annualised returns (CAGR) for each benchmark:
    1Y, 3Y, 5Y, 10Y, inception

Values are approximate long-run averages sourced from NSE / BSE historical
data.  Replace BENCHMARKS dict values with live API calls for production.

DATA STRUCTURES
---------------
BenchmarkIndex = TypedDict:
    name            display name  ("Nifty 50")
    ticker          exchange symbol ("^NSEI")
    returns         dict[period_label, annualised_CAGR_%]
    description     short blurb

FundComparison = TypedDict:
    scheme          fund scheme name
    fund_xirr       fund XIRR (%) or None
    benchmark_name  benchmark display name
    benchmark_return benchmark CAGR % for matched period
    alpha_pp        outperformance in percentage points (or None)
    relative_pct    alpha as % of benchmark return (or None)
    verdict         "OUTPERFORM" | "UNDERPERFORM" | "IN LINE" | "N/A"

BenchmarkReport = TypedDict:
    benchmark_name      index display name
    benchmark_return    CAGR % used for comparison
    period              comparison period label
    fund_comparisons    list[FundComparison]
    portfolio_alpha     value-weighted average alpha (pp) across all funds
    outperforming       count of funds with verdict == "OUTPERFORM"
    underperforming     count of funds with verdict == "UNDERPERFORM"
    insight             one-line human-readable portfolio-level summary
"""

from __future__ import annotations

import math
from typing import TypedDict

import streamlit as st


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

class BenchmarkIndex(TypedDict):
    name: str
    ticker: str
    returns: dict[str, float]
    description: str


class FundComparison(TypedDict):
    scheme: str
    fund_xirr: float | None
    benchmark_name: str
    benchmark_return: float
    alpha_pp: float | None
    relative_pct: float | None
    verdict: str


class BenchmarkReport(TypedDict):
    benchmark_name: str
    benchmark_return: float
    period: str
    fund_comparisons: list[FundComparison]
    portfolio_alpha: float | None
    outperforming: int
    underperforming: int
    insight: str


# ---------------------------------------------------------------------------
# MVP Benchmark Database
# Approximate long-run CAGR % (NSE / BSE historical data).
# ---------------------------------------------------------------------------

BENCHMARKS: dict[str, BenchmarkIndex] = {
    "nifty50": BenchmarkIndex(
        name="Nifty 50",
        ticker="^NSEI",
        description="NSE's flagship index of India's top 50 large-cap companies.",
        returns={
            "1Y":        14.5,
            "3Y":        12.8,
            "5Y":        13.5,
            "10Y":       12.0,
            "inception": 11.5,
        },
    ),
    "sensex": BenchmarkIndex(
        name="Sensex",
        ticker="^BSESN",
        description="BSE Sensex — 30 largest and most actively traded BSE stocks.",
        returns={
            "1Y":        14.2,
            "3Y":        12.5,
            "5Y":        13.2,
            "10Y":       11.8,
            "inception": 11.2,
        },
    ),
    "nifty_midcap": BenchmarkIndex(
        name="Nifty Midcap 150",
        ticker="NIFTYMIDCAP150.NS",
        description="Top 150 mid-cap stocks by free-float market cap on NSE.",
        returns={
            "1Y":        22.5,
            "3Y":        18.0,
            "5Y":        17.5,
            "10Y":       15.0,
            "inception": 14.0,
        },
    ),
    "nifty_smallcap": BenchmarkIndex(
        name="Nifty Smallcap 250",
        ticker="NIFTYSMALLCAP250.NS",
        description="Top 250 small-cap stocks by free-float market cap on NSE.",
        returns={
            "1Y":        30.0,
            "3Y":        20.5,
            "5Y":        16.5,
            "10Y":       12.5,
            "inception": 11.0,
        },
    ),
}

# Verdict thresholds (percentage points)
_OUTPERFORM_THRESHOLD   =  0.5
_UNDERPERFORM_THRESHOLD = -0.5


# ---------------------------------------------------------------------------
# Internal math helpers
# ---------------------------------------------------------------------------

def _compute_alpha(
    fund_xirr: float,
    benchmark_return: float,
) -> tuple[float, float | None]:
    """
    Returns (alpha_pp, relative_pct).

    alpha_pp     = fund_xirr - benchmark_return
    relative_pct = alpha_pp / |benchmark_return| * 100   (None if bm == 0)
    """
    alpha_pp = round(fund_xirr - benchmark_return, 2)
    if benchmark_return == 0:
        return alpha_pp, None
    return alpha_pp, round(alpha_pp / abs(benchmark_return) * 100, 1)


def _verdict(alpha_pp: float) -> str:
    if alpha_pp > _OUTPERFORM_THRESHOLD:
        return "OUTPERFORM"
    if alpha_pp < _UNDERPERFORM_THRESHOLD:
        return "UNDERPERFORM"
    return "IN LINE"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@st.cache_data
def get_available_benchmarks() -> dict[str, str]:
    """Return {key: display_name} for all registered benchmarks."""
    return {k: v["name"] for k, v in BENCHMARKS.items()}


def get_benchmark(key: str) -> BenchmarkIndex | None:
    """Look up a BenchmarkIndex by its key. Returns None for unknown keys."""
    return BENCHMARKS.get(key)


def compare_fund_to_benchmark(
    scheme: str,
    fund_xirr: float | None,
    benchmark_key: str,
    period: str = "3Y",
) -> FundComparison:
    """
    Compare a single fund's XIRR to a benchmark return for a given period.

    Args:
        scheme:         Fund scheme name (display only).
        fund_xirr:      Fund XIRR in percent.  None → verdict becomes "N/A".
        benchmark_key:  Key into BENCHMARKS (e.g. "nifty50", "sensex").
        period:         Period label — "1Y", "3Y", "5Y", "10Y", "inception".

    Returns:
        FundComparison TypedDict.
    """
    bm = BENCHMARKS.get(benchmark_key)
    if bm is None:
        raise ValueError(
            f"Unknown benchmark key '{benchmark_key}'. "
            f"Choose from: {list(BENCHMARKS.keys())}"
        )

    bm_return = bm["returns"].get(period) or bm["returns"].get("3Y", 12.0)

    if fund_xirr is None:
        return FundComparison(
            scheme=scheme,
            fund_xirr=None,
            benchmark_name=bm["name"],
            benchmark_return=bm_return,
            alpha_pp=None,
            relative_pct=None,
            verdict="N/A",
        )

    alpha_pp, relative_pct = _compute_alpha(fund_xirr, bm_return)
    return FundComparison(
        scheme=scheme,
        fund_xirr=round(fund_xirr, 2),
        benchmark_name=bm["name"],
        benchmark_return=bm_return,
        alpha_pp=alpha_pp,
        relative_pct=relative_pct,
        verdict=_verdict(alpha_pp),
    )


def generate_benchmark_report(
    portfolio_df,               # pd.DataFrame: scheme | xirr | current_value
    benchmark_key: str = "nifty50",
    period: str = "3Y",
) -> BenchmarkReport:
    """
    Full benchmark comparison report for a portfolio DataFrame.

    Args:
        portfolio_df:   DataFrame with columns [scheme, xirr, current_value].
        benchmark_key:  Benchmark to compare against (default: "nifty50").
        period:         Return period to use (default: "3Y").

    Returns:
        BenchmarkReport TypedDict.
    """
    bm = BENCHMARKS.get(benchmark_key)
    if bm is None:
        raise ValueError(f"Unknown benchmark key '{benchmark_key}'.")

    bm_return = bm["returns"].get(period) or bm["returns"].get("3Y", 12.0)

    comparisons: list[FundComparison] = []
    for _, row in portfolio_df.iterrows():
        try:
            raw_xirr = row.get("xirr")
            # pandas stores None as NaN in float columns — treat NaN as None.
            fund_xirr = None if (raw_xirr is None or (isinstance(raw_xirr, float) and math.isnan(raw_xirr))) else raw_xirr
            comp = compare_fund_to_benchmark(
                scheme=str(row.get("scheme", "Unknown")),
                fund_xirr=fund_xirr,
                benchmark_key=benchmark_key,
                period=period,
            )
        except Exception:
            comp = FundComparison(
                scheme=str(row.get("scheme", "Unknown")),
                fund_xirr=None,
                benchmark_name=bm["name"],
                benchmark_return=bm_return,
                alpha_pp=None,
                relative_pct=None,
                verdict="N/A",
            )
        comparisons.append(comp)

    # Value-weighted portfolio alpha
    portfolio_alpha: float | None = None
    weighted_pairs = []
    for i, comp in enumerate(comparisons):
        if comp["alpha_pp"] is None:
            continue
        try:
            raw_val = portfolio_df.iloc[i].get("current_value") or 0
            val = 0.0 if (raw_val is None or (isinstance(raw_val, float) and math.isnan(raw_val))) else float(raw_val)
        except (TypeError, ValueError):
            val = 0.0
        if val > 0:
            weighted_pairs.append((comp["alpha_pp"], val))

    if weighted_pairs:
        total_weight = sum(w for _, w in weighted_pairs)
        if total_weight > 0:
            portfolio_alpha = round(
                sum(a * w for a, w in weighted_pairs) / total_weight, 2
            )

    outperforming   = sum(1 for c in comparisons if c["verdict"] == "OUTPERFORM")
    underperforming = sum(1 for c in comparisons if c["verdict"] == "UNDERPERFORM")
    total_valid     = sum(1 for c in comparisons if c["verdict"] != "N/A")

    # Portfolio-level insight string
    if total_valid == 0:
        insight = f"No XIRR data available to compare against {bm['name']}."
    elif portfolio_alpha is None:
        insight = f"Portfolio alpha vs {bm['name']} could not be computed."
    elif portfolio_alpha > _OUTPERFORM_THRESHOLD:
        insight = (
            f"✅ Portfolio is beating {bm['name']} by {portfolio_alpha:+.2f} pp "
            f"({period}). {outperforming}/{total_valid} funds outperform."
        )
    elif portfolio_alpha < _UNDERPERFORM_THRESHOLD:
        insight = (
            f"⚠️ Portfolio trails {bm['name']} by {abs(portfolio_alpha):.2f} pp "
            f"({period}). {underperforming}/{total_valid} funds underperform."
        )
    else:
        insight = (
            f"➡️ Portfolio is broadly in line with {bm['name']} "
            f"({portfolio_alpha:+.2f} pp, {period})."
        )

    return BenchmarkReport(
        benchmark_name=bm["name"],
        benchmark_return=bm_return,
        period=period,
        fund_comparisons=comparisons,
        portfolio_alpha=portfolio_alpha,
        outperforming=outperforming,
        underperforming=underperforming,
        insight=insight,
    )
