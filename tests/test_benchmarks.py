"""
tests/test_benchmarks.py — Unit tests for utils/benchmarks.py
"""

import pandas as pd
import pytest

from utils.benchmarks import (
    BENCHMARKS,
    compare_fund_to_benchmark,
    generate_benchmark_report,
    get_available_benchmarks,
    get_benchmark,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_DF = pd.DataFrame([
    {"scheme": "Fund Alpha", "xirr": 15.5, "current_value": 100_000},
    {"scheme": "Fund Beta",  "xirr":  9.0, "current_value":  50_000},
    {"scheme": "Fund Gamma", "xirr": None, "current_value":  25_000},
])


# ---------------------------------------------------------------------------
# get_available_benchmarks / get_benchmark
# ---------------------------------------------------------------------------

class TestGetBenchmarks:

    def test_available_benchmarks_returns_dict(self):
        bms = get_available_benchmarks()
        assert isinstance(bms, dict)
        assert "nifty50" in bms
        assert "sensex"  in bms

    def test_get_benchmark_known_key(self):
        bm = get_benchmark("nifty50")
        assert bm is not None
        assert bm["name"] == "Nifty 50"
        assert "3Y" in bm["returns"]

    def test_get_benchmark_unknown_key_returns_none(self):
        assert get_benchmark("unknown_index") is None


# ---------------------------------------------------------------------------
# compare_fund_to_benchmark — Math verification
# ---------------------------------------------------------------------------

class TestCompareFundToBenchmark:

    def test_outperform_verdict(self):
        """Fund XIRR 15% vs Nifty 50 3Y 12.8% → alpha = +2.2 pp → OUTPERFORM"""
        result = compare_fund_to_benchmark("Test Fund", 15.0, "nifty50", "3Y")
        assert result["verdict"] == "OUTPERFORM"
        assert result["alpha_pp"] > 0

    def test_underperform_verdict(self):
        """Fund XIRR 8% vs Nifty 50 3Y 12.8% → alpha = -4.8 pp → UNDERPERFORM"""
        result = compare_fund_to_benchmark("Test Fund", 8.0, "nifty50", "3Y")
        assert result["verdict"] == "UNDERPERFORM"
        assert result["alpha_pp"] < 0

    def test_in_line_verdict(self):
        """Fund XIRR == benchmark return exactly → alpha = 0 → IN LINE"""
        bm_return = BENCHMARKS["nifty50"]["returns"]["3Y"]
        result = compare_fund_to_benchmark("Test Fund", bm_return, "nifty50", "3Y")
        assert result["verdict"] == "IN LINE"
        assert result["alpha_pp"] == 0.0

    def test_none_xirr_gives_na_verdict(self):
        result = compare_fund_to_benchmark("Test Fund", None, "nifty50", "3Y")
        assert result["verdict"] == "N/A"
        assert result["alpha_pp"] is None
        assert result["relative_pct"] is None

    def test_alpha_calculation_accuracy(self):
        """
        Fund = 15.5%, Nifty50 3Y = 12.8%
        Alpha = 15.5 - 12.8 = 2.7 pp
        Relative = 2.7 / 12.8 * 100 = 21.09% ≈ 21.1%
        """
        result = compare_fund_to_benchmark("Test Fund", 15.5, "nifty50", "3Y")
        assert result["alpha_pp"] == pytest.approx(2.7, abs=0.01)
        assert result["relative_pct"] == pytest.approx(21.1, abs=0.1)

    def test_sensex_comparison(self):
        result = compare_fund_to_benchmark("Test Fund", 14.0, "sensex", "1Y")
        assert result["benchmark_name"] == "Sensex"
        assert result["benchmark_return"] == BENCHMARKS["sensex"]["returns"]["1Y"]

    def test_unknown_benchmark_raises(self):
        with pytest.raises(ValueError, match="Unknown benchmark key"):
            compare_fund_to_benchmark("Test Fund", 12.0, "mystery_index", "3Y")

    def test_all_four_benchmarks_work(self):
        for key in ["nifty50", "sensex", "nifty_midcap", "nifty_smallcap"]:
            result = compare_fund_to_benchmark("Fund", 12.0, key, "3Y")
            assert result["benchmark_name"] == BENCHMARKS[key]["name"]


# ---------------------------------------------------------------------------
# generate_benchmark_report — Full report
# ---------------------------------------------------------------------------

class TestGenerateBenchmarkReport:

    def test_report_keys_present(self):
        report = generate_benchmark_report(SAMPLE_DF)
        for key in [
            "benchmark_name", "benchmark_return", "period",
            "fund_comparisons", "portfolio_alpha",
            "outperforming", "underperforming", "insight",
        ]:
            assert key in report

    def test_fund_comparisons_count_matches_df(self):
        report = generate_benchmark_report(SAMPLE_DF)
        assert len(report["fund_comparisons"]) == len(SAMPLE_DF)

    def test_none_xirr_fund_gets_na_verdict(self):
        report = generate_benchmark_report(SAMPLE_DF)
        gamma_comp = next(
            c for c in report["fund_comparisons"] if c["scheme"] == "Fund Gamma"
        )
        assert gamma_comp["verdict"] == "N/A"

    def test_outperforming_count(self):
        """Fund Alpha (15.5%) beats Nifty50 3Y (12.8%) → 1 outperform"""
        report = generate_benchmark_report(SAMPLE_DF, benchmark_key="nifty50", period="3Y")
        assert report["outperforming"] == 1

    def test_underperforming_count(self):
        """Fund Beta (9.0%) trails Nifty50 3Y (12.8%) → 1 underperform"""
        report = generate_benchmark_report(SAMPLE_DF, benchmark_key="nifty50", period="3Y")
        assert report["underperforming"] == 1

    def test_weighted_portfolio_alpha(self):
        """
        Fund Alpha: alpha = 15.5 - 12.8 = +2.7 pp, weight = 100_000
        Fund Beta:  alpha =  9.0 - 12.8 = -3.8 pp, weight =  50_000
        Fund Gamma: alpha = N/A (excluded from weighting)

        Weighted alpha = (2.7 * 100_000 + (-3.8) * 50_000) / 150_000
                       = (270_000 - 190_000) / 150_000
                       = 80_000 / 150_000
                       ≈ 0.53 pp
        """
        report = generate_benchmark_report(SAMPLE_DF, benchmark_key="nifty50", period="3Y")
        assert report["portfolio_alpha"] == pytest.approx(0.53, abs=0.05)

    def test_insight_string_not_empty(self):
        report = generate_benchmark_report(SAMPLE_DF)
        assert isinstance(report["insight"], str)
        assert len(report["insight"]) > 10

    def test_period_selection(self):
        for period in ["1Y", "3Y", "5Y", "10Y"]:
            report = generate_benchmark_report(SAMPLE_DF, period=period)
            assert report["period"] == period
            assert report["benchmark_return"] == BENCHMARKS["nifty50"]["returns"][period]

    def test_empty_df_returns_report_not_crash(self):
        """Empty DF means no comparisons; should still return a usable report."""
        empty_df = pd.DataFrame(columns=["scheme", "xirr", "current_value"])
        report = generate_benchmark_report(empty_df)
        assert report["fund_comparisons"] == []
        assert report["portfolio_alpha"] is None
