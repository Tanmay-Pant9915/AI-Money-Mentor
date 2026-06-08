"""
tests/test_portfolio_service.py
"""
import pandas as pd
import pytest
from unittest.mock import patch

from services.portfolio_service import analyze_portfolio, get_overlap_report
from utils.pdf_parser import extract_text, parse_funds


# ---------------------------------------------------------------------------
# analyze_portfolio — now returns (df, overlap_report) tuple
# ---------------------------------------------------------------------------

class TestAnalyzePortfolio:

    def test_returns_tuple(self):
        df = parse_funds(extract_text("data/sample_statements/Sample_CAMS_Statement.pdf"))
        result = analyze_portfolio(df)
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_result_df_has_required_columns(self):
        df = parse_funds(extract_text("data/sample_statements/Sample_CAMS_Statement.pdf"))
        result_df, _, _ = analyze_portfolio(df)
        for col in ["scheme", "current_value", "xirr", "expense_ratio", "annual_expense_cost"]:
            assert col in result_df.columns

    def test_raises_on_empty_df(self):
        with pytest.raises(ValueError, match="empty"):
            analyze_portfolio(pd.DataFrame())

    def test_raises_on_missing_columns(self):
        df = pd.DataFrame({"scheme": ["ABC Fund"]})
        with pytest.raises(ValueError, match="missing required columns"):
            analyze_portfolio(df)


# ---------------------------------------------------------------------------
# get_overlap_report — non-critical, returns None when not enough data
# ---------------------------------------------------------------------------

class TestGetOverlapReport:

    def test_returns_none_for_single_scheme_not_in_db(self):
        report = get_overlap_report(["Unknown Fund That Is Not In DB"])
        assert report is None

    def test_returns_none_for_single_known_scheme(self):
        report = get_overlap_report(["Axis Bluechip Fund - Direct Growth"])
        assert report is None

    def test_returns_report_for_known_demo_funds(self):
        # "Fund A" and "Fund B" are seeded in data/fund_holdings.py
        report = get_overlap_report(["Fund A", "Fund B"])
        assert report is not None
        assert len(report["pairs"]) == 1

    def test_returns_report_for_multiple_known_schemes(self):
        report = get_overlap_report([
            "Axis Bluechip Fund - Direct Growth",
            "UTI Nifty 50 Index Fund - Direct Growth"
        ])
        assert report is not None
        assert len(report["pairs"]) == 1
        assert report["pairs"][0]["overlap_pct"] == 60.0

    def test_returns_none_on_exception(self):
        # Simulate a crash inside generate_overlap_report — should not propagate.
        with patch("services.portfolio_service.generate_overlap_report", side_effect=RuntimeError("boom")):
            report = get_overlap_report(["Fund A", "Fund B"])
        assert report is None