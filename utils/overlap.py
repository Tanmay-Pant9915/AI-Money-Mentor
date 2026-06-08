"""
utils/overlap.py — Fund Overlap Detection Engine
=================================================

MATHEMATICS
-----------
For two funds A and B with holding sets H_A and H_B:

  Overlap %  =  |H_A ∩ H_B|  /  |H_A ∪ H_B|  × 100
             =  Jaccard Similarity × 100

The Jaccard index is the canonical choice because it penalises both funds
equally for having many unique-only holdings.  Pure intersection /
min(|A|, |B|) would overstate overlap when one fund is very small.

For N funds the pairwise matrix has N*(N-1)/2 unique pairs.

CONCENTRATION RISK THRESHOLDS  (standard in Indian MF research)
  HIGH:   overlap >= 60%  — portfolios behave nearly identically
  MEDIUM: overlap >= 30%  — meaningful diversification reduction
  LOW:    overlap <  30%  — acceptable

DATA STRUCTURES
---------------
FundHoldings  = dict[str, set[str]]

PairResult    = TypedDict:
    fund_a, fund_b        — scheme names
    common_holdings       — sorted list of shared stocks
    common_count          — len(common_holdings)
    union_count           — |A ∪ B|
    overlap_pct           — Jaccard * 100, rounded to 2 dp
    risk_level            — "HIGH" | "MEDIUM" | "LOW"

OverlapReport = TypedDict:
    pairs                 — list[PairResult]
    stock_frequency       — dict[str, list[str]]  stock → [fund names]
    high_overlap_pairs    — pairs with overlap >= 60%
    concentrated_stocks   — stocks appearing in 3+ funds
"""

from __future__ import annotations

from itertools import combinations
from typing import TypedDict

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
FundHoldings = dict[str, set[str]]


class PairResult(TypedDict):
    fund_a: str
    fund_b: str
    common_holdings: list[str]
    common_count: int
    union_count: int
    overlap_pct: float
    risk_level: str


class OverlapReport(TypedDict):
    pairs: list[PairResult]
    stock_frequency: dict[str, list[str]]
    high_overlap_pairs: list[PairResult]
    concentrated_stocks: dict[str, list[str]]


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
_HIGH_OVERLAP_THRESHOLD   = 60.0
_MEDIUM_OVERLAP_THRESHOLD = 30.0
_CONCENTRATION_MIN_FUNDS  = 3      # stock must appear in >= this many funds


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalise_holdings(raw: dict[str, list[str]]) -> FundHoldings:
    """
    Convert {fund: [stock, ...]} to {fund: set(normalised_stock)}.
    Strips whitespace and title-cases names so "reliance " == "Reliance".
    """
    return {
        fund: {s.strip().title() for s in stocks if s and s.strip()}
        for fund, stocks in raw.items()
        if fund and stocks
    }


def _jaccard(set_a: set[str], set_b: set[str]) -> tuple[float, set[str], set[str]]:
    """
    Returns (overlap_pct, intersection, union).
    Returns (0.0, empty, empty) when both sets are empty.
    """
    intersection = set_a & set_b
    union        = set_a | set_b
    if not union:
        return 0.0, intersection, union
    return round(len(intersection) / len(union) * 100, 2), intersection, union


def _risk_level(pct: float) -> str:
    if pct >= _HIGH_OVERLAP_THRESHOLD:
        return "HIGH"
    if pct >= _MEDIUM_OVERLAP_THRESHOLD:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_pairwise_overlap(raw_holdings: dict[str, list[str]]) -> list[PairResult]:
    """
    Compute Jaccard overlap % for every unique fund pair.

    Args:
        raw_holdings: {fund_name: [stock1, stock2, ...]}

    Returns:
        List of PairResult dicts, sorted by overlap_pct descending.
        Empty list if fewer than 2 funds are provided.
    """
    if len(raw_holdings) < 2:
        return []

    holdings = _normalise_holdings(raw_holdings)
    results: list[PairResult] = []

    for fund_a, fund_b in combinations(holdings.keys(), 2):
        overlap_pct, intersection, union = _jaccard(
            holdings[fund_a], holdings[fund_b]
        )
        results.append(
            PairResult(
                fund_a=fund_a,
                fund_b=fund_b,
                common_holdings=sorted(intersection),
                common_count=len(intersection),
                union_count=len(union),
                overlap_pct=overlap_pct,
                risk_level=_risk_level(overlap_pct),
            )
        )

    return sorted(results, key=lambda r: r["overlap_pct"], reverse=True)


def build_stock_frequency(raw_holdings: dict[str, list[str]]) -> dict[str, list[str]]:
    """
    Inverted index: stock → list of funds that hold it.
    Sorted by number of funds (descending), then alphabetically.
    """
    holdings = _normalise_holdings(raw_holdings)
    freq: dict[str, list[str]] = {}

    for fund, stocks in holdings.items():
        for stock in stocks:
            freq.setdefault(stock, []).append(fund)

    return dict(
        sorted(freq.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    )


def generate_overlap_report(raw_holdings: dict[str, list[str]]) -> OverlapReport:
    """
    Full analysis: pairwise Jaccard + stock frequency + risk flags.

    Args:
        raw_holdings: {fund_name: [stock1, stock2, ...]}

    Returns:
        OverlapReport with keys:
          pairs              — all pairwise results (sorted by overlap desc)
          stock_frequency    — stock → [funds] inverted index
          high_overlap_pairs — pairs with overlap >= 60%
          concentrated_stocks — stocks appearing in 3+ funds
    """
    pairs      = calculate_pairwise_overlap(raw_holdings)
    stock_freq = build_stock_frequency(raw_holdings)

    return OverlapReport(
        pairs=pairs,
        stock_frequency=stock_freq,
        high_overlap_pairs=[p for p in pairs if p["overlap_pct"] >= _HIGH_OVERLAP_THRESHOLD],
        concentrated_stocks={
            stock: funds
            for stock, funds in stock_freq.items()
            if len(funds) >= _CONCENTRATION_MIN_FUNDS
        },
    )


def get_holdings_for_portfolio(
    scheme_names: list[str],
    holdings_db: dict[str, list[str]],
) -> dict[str, list[str]]:
    """
    Filter a holdings database to only schemes in the investor's portfolio.

    In production, holdings_db comes from an AMC data feed or Value Research
    API.  For the MVP it is the FUND_HOLDINGS dict in data/fund_holdings.py.

    Args:
        scheme_names: Scheme names from the parsed portfolio DataFrame.
        holdings_db:  Full {scheme: [stocks]} reference dict.

    Returns:
        Filtered dict with only matched schemes.
    """
    return {
        scheme: holdings_db[scheme]
        for scheme in scheme_names
        if scheme in holdings_db
    }
