"""
tests/test_overlap.py — Unit tests for utils/overlap.py
"""

import pytest
from utils.overlap import (
    calculate_pairwise_overlap,
    build_stock_frequency,
    generate_overlap_report,
    get_holdings_for_portfolio,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MVP_HOLDINGS = {
    "Fund A": ["Reliance", "TCS", "Infosys"],
    "Fund B": ["Reliance", "Infosys", "ICICI Bank"],
}

THREE_FUND_HOLDINGS = {
    "Fund A": ["Reliance", "TCS", "Infosys"],
    "Fund B": ["Reliance", "Infosys", "ICICI Bank"],
    "Fund C": ["Reliance", "HDFC Bank", "Bajaj Finance"],
}

NO_OVERLAP_HOLDINGS = {
    "Fund X": ["TCS", "Infosys"],
    "Fund Y": ["HDFC Bank", "ICICI Bank"],
}

HOLDINGS_DB = {
    "Scheme Alpha": ["Reliance", "TCS"],
    "Scheme Beta":  ["Reliance", "Infosys"],
    "Unknown Fund": ["SomeStock"],
}


# ---------------------------------------------------------------------------
# calculate_pairwise_overlap
# ---------------------------------------------------------------------------

class TestCalculatePairwiseOverlap:

    def test_returns_empty_for_single_fund(self):
        result = calculate_pairwise_overlap({"Fund A": ["Reliance", "TCS"]})
        assert result == []

    def test_returns_empty_for_empty_input(self):
        assert calculate_pairwise_overlap({}) == []

    def test_mvp_pair_overlap_pct(self):
        """
        Fund A = {Reliance, TCS, Infosys}, Fund B = {Reliance, Infosys, ICICI Bank}
        Intersection = {Reliance, Infosys} → 2 stocks
        Union        = {Reliance, TCS, Infosys, ICICI Bank} → 4 stocks
        Jaccard      = 2/4 = 0.50 → 50.0%
        """
        pairs = calculate_pairwise_overlap(MVP_HOLDINGS)
        assert len(pairs) == 1
        p = pairs[0]
        assert p["overlap_pct"] == 50.0
        assert p["common_count"] == 2
        assert p["union_count"] == 4
        assert set(p["common_holdings"]) == {"Reliance", "Infosys"}

    def test_risk_level_high(self):
        holdings = {
            "Fund A": ["A", "B", "C", "D", "E"],
            "Fund B": ["A", "B", "C", "D", "E", "F"],  # 5/6 = 83%
        }
        pairs = calculate_pairwise_overlap(holdings)
        assert pairs[0]["risk_level"] == "HIGH"

    def test_risk_level_medium(self):
        holdings = {
            "Fund A": ["A", "B", "C", "X", "Y", "Z", "P", "Q", "R", "S"],
            "Fund B": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"],
            # intersection=3, union=17 → 3/17 = 17.6% → LOW
            # Use a better example: intersection=4, union=10 → 40% MEDIUM
        }
        # 4/10 = 40%
        holdings2 = {
            "Fund A": ["A", "B", "C", "D", "E", "F"],
            "Fund B": ["A", "B", "C", "D", "G", "H"],
        }
        pairs = calculate_pairwise_overlap(holdings2)
        assert pairs[0]["risk_level"] == "MEDIUM"

    def test_risk_level_low(self):
        pairs = calculate_pairwise_overlap(NO_OVERLAP_HOLDINGS)
        assert pairs[0]["risk_level"] == "LOW"
        assert pairs[0]["overlap_pct"] == 0.0

    def test_results_sorted_descending(self):
        pairs = calculate_pairwise_overlap(THREE_FUND_HOLDINGS)
        pcts = [p["overlap_pct"] for p in pairs]
        assert pcts == sorted(pcts, reverse=True)

    def test_normalisation_case_insensitive(self):
        """'RELIANCE' and 'reliance ' should both match 'Reliance'."""
        holdings = {
            "Fund A": ["RELIANCE", "TCS"],
            "Fund B": ["reliance ", "Infosys"],
        }
        pairs = calculate_pairwise_overlap(holdings)
        assert pairs[0]["common_count"] == 1
        assert "Reliance" in pairs[0]["common_holdings"]


# ---------------------------------------------------------------------------
# build_stock_frequency
# ---------------------------------------------------------------------------

class TestBuildStockFrequency:

    def test_reliance_appears_in_both_funds(self):
        freq = build_stock_frequency(MVP_HOLDINGS)
        assert "Reliance" in freq
        assert len(freq["Reliance"]) == 2

    def test_tcs_appears_in_only_fund_a(self):
        freq = build_stock_frequency(MVP_HOLDINGS)
        assert len(freq["Tcs"]) == 1      # normalised to title case

    def test_sorted_by_frequency_descending(self):
        freq = build_stock_frequency(THREE_FUND_HOLDINGS)
        counts = [len(v) for v in freq.values()]
        assert counts == sorted(counts, reverse=True)

    def test_empty_input(self):
        assert build_stock_frequency({}) == {}


# ---------------------------------------------------------------------------
# generate_overlap_report
# ---------------------------------------------------------------------------

class TestGenerateOverlapReport:

    def test_report_keys_present(self):
        report = generate_overlap_report(MVP_HOLDINGS)
        assert "pairs" in report
        assert "stock_frequency" in report
        assert "high_overlap_pairs" in report
        assert "concentrated_stocks" in report

    def test_no_high_overlap_for_50_pct(self):
        """50% is below the 60% HIGH threshold."""
        report = generate_overlap_report(MVP_HOLDINGS)
        assert len(report["high_overlap_pairs"]) == 0

    def test_high_overlap_detected(self):
        holdings = {
            "Fund A": ["A", "B", "C", "D", "E"],
            "Fund B": ["A", "B", "C", "D", "F"],   # 4/6 = 66.7% → HIGH
        }
        report = generate_overlap_report(holdings)
        assert len(report["high_overlap_pairs"]) == 1

    def test_concentrated_stocks_detected(self):
        """A stock in 3 funds should appear in concentrated_stocks."""
        holdings = {
            "Fund A": ["Reliance", "TCS"],
            "Fund B": ["Reliance", "Infosys"],
            "Fund C": ["Reliance", "HDFC"],
        }
        report = generate_overlap_report(holdings)
        assert "Reliance" in report["concentrated_stocks"]


# ---------------------------------------------------------------------------
# get_holdings_for_portfolio
# ---------------------------------------------------------------------------

class TestGetHoldingsForPortfolio:

    def test_filters_to_known_schemes_only(self):
        result = get_holdings_for_portfolio(
            ["Scheme Alpha", "Scheme Beta", "Not In DB"],
            HOLDINGS_DB,
        )
        assert "Scheme Alpha" in result
        assert "Scheme Beta" in result
        assert "Not In DB" not in result

    def test_empty_scheme_list(self):
        assert get_holdings_for_portfolio([], HOLDINGS_DB) == {}

    def test_no_matches(self):
        assert get_holdings_for_portfolio(["Ghost Fund"], HOLDINGS_DB) == {}


# ---------------------------------------------------------------------------
# Integration Tests with Real/Realistic FUND_HOLDINGS data
# ---------------------------------------------------------------------------
from data.fund_holdings import FUND_HOLDINGS

class TestRealFundOverlap:

    def test_real_holdings_lookup(self):
        schemes = [
            "Axis Bluechip Fund - Direct Growth",
            "UTI Nifty 50 Index Fund - Direct Growth",
            "Parag Parikh Flexi Cap Fund - Direct Growth",
            "Kotak Emerging Equity Fund - Direct Growth",
            "Nippon India Small Cap Fund - Direct Growth",
            "Unknown Fund Growth",
        ]
        holdings = get_holdings_for_portfolio(schemes, FUND_HOLDINGS)
        assert len(holdings) == 5
        assert "Unknown Fund Growth" not in holdings
        for fund in schemes[:-1]:
            assert fund in holdings
            assert len(holdings[fund]) >= 15 and len(holdings[fund]) <= 25

    def test_real_overlap_calculations(self):
        holdings = get_holdings_for_portfolio([
            "Axis Bluechip Fund - Direct Growth",
            "UTI Nifty 50 Index Fund - Direct Growth",
            "Parag Parikh Flexi Cap Fund - Direct Growth",
            "Kotak Emerging Equity Fund - Direct Growth",
            "Nippon India Small Cap Fund - Direct Growth",
        ], FUND_HOLDINGS)
        
        report = generate_overlap_report(holdings)
        pairs = report["pairs"]
        
        # We expect N*(N-1)/2 = 5*4/2 = 10 pairs
        assert len(pairs) == 10
        
        # High overlap between Axis Bluechip and UTI Nifty 50 (60.0%)
        axis_nifty = next(p for p in pairs if {p["fund_a"], p["fund_b"]} == {
            "Axis Bluechip Fund - Direct Growth",
            "UTI Nifty 50 Index Fund - Direct Growth"
        })
        assert axis_nifty["overlap_pct"] == 60.0
        assert axis_nifty["risk_level"] == "HIGH"
        
        # Moderate overlap between Axis Bluechip and Parag Parikh (42.86%)
        axis_pp = next(p for p in pairs if {p["fund_a"], p["fund_b"]} == {
            "Axis Bluechip Fund - Direct Growth",
            "Parag Parikh Flexi Cap Fund - Direct Growth"
        })
        assert axis_pp["overlap_pct"] == 42.86
        assert axis_pp["risk_level"] == "MEDIUM"

        # Overlap between Kotak Emerging and Axis Bluechip (25.0%)
        kotak_axis = next(p for p in pairs if {p["fund_a"], p["fund_b"]} == {
            "Kotak Emerging Equity Fund - Direct Growth",
            "Axis Bluechip Fund - Direct Growth"
        })
        assert kotak_axis["overlap_pct"] == 25.0
        assert kotak_axis["risk_level"] == "LOW"

        # Low overlap between Nippon Small Cap and UTI Nifty (11.11%)
        nippon_nifty = next(p for p in pairs if {p["fund_a"], p["fund_b"]} == {
            "Nippon India Small Cap Fund - Direct Growth",
            "UTI Nifty 50 Index Fund - Direct Growth"
        })
        assert nippon_nifty["overlap_pct"] == 11.11
        assert nippon_nifty["risk_level"] == "LOW"

        # Low overlap between Parag Parikh and Nippon Small Cap (11.11%)
        parag_nippon = next(p for p in pairs if {p["fund_a"], p["fund_b"]} == {
            "Parag Parikh Flexi Cap Fund - Direct Growth",
            "Nippon India Small Cap Fund - Direct Growth"
        })
        assert parag_nippon["overlap_pct"] == 11.11
        assert parag_nippon["risk_level"] == "LOW"

    def test_single_fund_portfolio(self):
        holdings = get_holdings_for_portfolio([
            "Axis Bluechip Fund - Direct Growth"
        ], FUND_HOLDINGS)
        report = generate_overlap_report(holdings)
        assert len(report["pairs"]) == 0
        assert len(report["high_overlap_pairs"]) == 0

    def test_missing_schemes_handling(self):
        holdings = get_holdings_for_portfolio([
            "Ghost Fund Direct Growth",
            "Another Phantom Fund Growth"
        ], FUND_HOLDINGS)
        report = generate_overlap_report(holdings)
        assert len(report["pairs"]) == 0

