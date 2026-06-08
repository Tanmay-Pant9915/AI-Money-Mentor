from datetime import datetime

import pandas as pd

from data.expense_ratios import EXPENSE_RATIOS
from data.fund_holdings import FUND_HOLDINGS
from utils.benchmarks import BenchmarkReport, generate_benchmark_report
from utils.expense_drag import calculate_expense_drag
from utils.overlap import OverlapReport, generate_overlap_report, get_holdings_for_portfolio
from utils.xirr import calculate_xirr


def transactions_to_cashflows(
    transactions: list,
    current_value: float,
) -> list:
    """
    Convert transaction records into XIRR cashflows.

    Purchases -> negative cashflows
    Current portfolio value -> positive cashflow (terminal inflow)
    """
    if not transactions:
        raise ValueError("No transactions available for this fund.")

    if current_value is None or current_value <= 0:
        raise ValueError("current_value is missing or zero — cannot build cashflows.")

    cashflows = []
    for txn in transactions:
        try:
            cashflows.append((txn["date"], -txn["amount"]))
        except (KeyError, TypeError):
            # Skip individual malformed transaction entries.
            continue

    if not cashflows:
        raise ValueError("All transactions were malformed — no valid cashflows built.")

    cashflows.append((datetime.today(), current_value))
    return cashflows


def add_expense_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add expense_ratio and annual_expense_cost columns.

    Per-row errors fall back to defaults (ratio=1.0, cost=0.0) so the
    row remains usable for the rest of the pipeline.
    """
    df = df.copy()
    expense_ratios = []
    expense_costs = []

    for _, row in df.iterrows():
        try:
            scheme = row.get("scheme")
            ratio = EXPENSE_RATIOS.get(scheme, 1.0) if scheme else 1.0
        except Exception:
            ratio = 1.0

        try:
            cost = calculate_expense_drag(row.get("current_value"), ratio)
        except Exception:
            cost = 0.0

        expense_ratios.append(ratio)
        expense_costs.append(cost)

    df["expense_ratio"] = expense_ratios
    df["annual_expense_cost"] = expense_costs
    return df


def add_xirr_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add an xirr column for each fund.

    XIRR is set to None when:
    - Transactions list is empty or missing.
    - current_value is missing or zero.
    - The scipy solver does not converge.
    - Any other unexpected error.

    None is the correct sentinel — it flows through to the UI which
    renders it as "data unavailable" rather than crashing.
    """
    df = df.copy()
    xirr_values = []

    for _, row in df.iterrows():
        xirr: float | None = None
        try:
            transactions = row.get("transactions")
            if not isinstance(transactions, list):
                raise ValueError("transactions field is not a list.")

            cashflows = transactions_to_cashflows(
                transactions,
                row.get("current_value"),
            )
            xirr = round(calculate_xirr(cashflows) * 100, 2)

        except (ValueError, TypeError):
            # Expected: insufficient data or solver failure → leave as None.
            xirr = None
        except Exception:
            # Unexpected: still safe to proceed with None.
            xirr = None

        xirr_values.append(xirr)

    df["xirr"] = xirr_values
    return df


def get_overlap_report(scheme_names: list[str]) -> OverlapReport | None:
    """
    Build a fund overlap report for the schemes in the portfolio.

    Looks up each scheme in the FUND_HOLDINGS database.  Returns None
    when fewer than 2 schemes are found in the database (not enough
    funds to compare).

    Args:
        scheme_names: List of scheme name strings from the portfolio DataFrame.

    Returns:
        OverlapReport or None.
    """
    try:
        holdings = get_holdings_for_portfolio(scheme_names, FUND_HOLDINGS)
        if len(holdings) < 2:
            return None
        return generate_overlap_report(holdings)
    except Exception:
        # Overlap is a non-critical feature — never let it crash the main flow.
        return None


def get_benchmark_report(
    df: pd.DataFrame,
    benchmark_key: str = "nifty50",
    period: str = "3Y",
) -> BenchmarkReport | None:
    """
    Generate a benchmark comparison report against a chosen index.

    Returns None when the DataFrame has no usable rows (non-critical feature).

    Args:
        df:             Portfolio DataFrame with [scheme, xirr, current_value].
        benchmark_key:  Key from BENCHMARKS dict (default: "nifty50").
        period:         Return period label (default: "3Y").
    """
    try:
        return generate_benchmark_report(df, benchmark_key=benchmark_key, period=period)
    except Exception:
        # Benchmark is a non-critical feature — never crash the main pipeline.
        return None


def analyze_portfolio(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, OverlapReport | None, BenchmarkReport | None]:
    """
    Run complete portfolio analysis.

    Raises ValueError for completely unusable input (empty DataFrame,
    missing required columns) so the UI can surface a clear error.

    Returns:
        (result_df, overlap_report, benchmark_report)
        overlap_report   — None when fewer than 2 funds are in the holdings DB.
        benchmark_report — None on any error (non-critical).
    """
    if df is None or df.empty:
        raise ValueError("Portfolio DataFrame is empty — nothing to analyse.")

    required_columns = {"scheme", "current_value", "transactions"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(
            f"Portfolio data is missing required columns: {missing}. "
            "Please check that you uploaded a valid CAMS statement."
        )

    df = add_expense_analysis(df)
    df = add_xirr_analysis(df)

    overlap   = get_overlap_report(df["scheme"].dropna().tolist())
    benchmark = get_benchmark_report(df)

    return df, overlap, benchmark