"""
tests/test_capital_gains_calculator.py
Unit tests for capital gains calculations, fund classification, holding period rules, and CAS analysis.
"""
from datetime import date
import pandas as pd
import pytest

from utils.capital_gains_calculator import (
    analyze_cas_holdings_capital_gains,
    calculate_transaction_capital_gain,
    classify_fund_asset_type,
)


def test_classify_fund_asset_type():
    assert classify_fund_asset_type("HDFC Top 100 Fund - Growth") == "EQUITY"
    assert classify_fund_asset_type("Nippon India Small Cap Fund") == "EQUITY"
    assert classify_fund_asset_type("ICICI Prudential Corporate Bond Fund") == "DEBT"
    assert classify_fund_asset_type("SBI Liquid Fund - Regular Plan") == "DEBT"
    assert classify_fund_asset_type("Aditya Birla Sun Life Money Market Fund") == "DEBT"
    assert classify_fund_asset_type("") == "OTHER"


def test_equity_stcg_calculation():
    # Buy on 1 Jan 2024, sell on 1 May 2024 (4 months -> STCG)
    # Gain: 50,000. Tax rate 20%, cess 4% -> 20.8% = 10,400.
    res = calculate_transaction_capital_gain(
        asset_name="Nifty 50 Index Fund",
        asset_category="EQUITY",
        purchase_date=date(2024, 1, 1),
        sale_date=date(2024, 5, 1),
        cost_basis=100000.0,
        sale_proceeds=150000.0,
        financial_year="2024-25",
    )
    assert res.gain_type == "STCG"
    assert res.net_capital_gain == 50000.0
    assert res.exemption_applied == 0.0
    assert res.taxable_gain == 50000.0
    assert res.tax_rate_pct == 20.0
    assert res.base_tax == 10000.0
    assert res.cess == 400.0
    assert res.total_tax == 10400.0


def test_equity_ltcg_calculation_with_exemption():
    # Buy on 1 Jan 2022, sell on 1 Aug 2024 (> 2 years -> LTCG)
    # Gain: 2,00,000. Exemption: 1,25,000. Taxable: 75,000.
    # Tax rate: 12.5%, base tax: 9,375, cess: 375, total tax: 9,750.
    res = calculate_transaction_capital_gain(
        asset_name="HDFC Flexi Cap Fund",
        asset_category="EQUITY",
        purchase_date=date(2022, 1, 1),
        sale_date=date(2024, 8, 1),
        cost_basis=300000.0,
        sale_proceeds=500000.0,
        financial_year="2024-25",
    )
    assert res.gain_type == "LTCG"
    assert res.net_capital_gain == 200000.0
    assert res.exemption_applied == 125000.0
    assert res.taxable_gain == 75000.0
    assert res.tax_rate_pct == 12.5
    assert res.base_tax == 9375.0
    assert res.cess == 375.0
    assert res.total_tax == 9750.0


def test_capital_loss():
    res = calculate_transaction_capital_gain(
        asset_name="Tech Fund",
        asset_category="EQUITY",
        purchase_date=date(2023, 1, 1),
        sale_date=date(2024, 1, 1),
        cost_basis=100000.0,
        sale_proceeds=80000.0,
        financial_year="2024-25",
    )
    assert res.gain_type == "LOSS"
    assert res.net_capital_gain == -20000.0
    assert res.taxable_gain == 0.0
    assert res.total_tax == 0.0


def test_invalid_sale_date():
    with pytest.raises(ValueError, match="Sale date cannot be earlier"):
        calculate_transaction_capital_gain(
            asset_name="Fund",
            asset_category="EQUITY",
            purchase_date=date(2024, 5, 1),
            sale_date=date(2024, 1, 1),
            cost_basis=100000.0,
            sale_proceeds=120000.0,
        )


def test_analyze_cas_holdings_empty_and_valid():
    # Empty case
    empty_res = analyze_cas_holdings_capital_gains(None)
    assert empty_res["has_data"] is False

    # Valid DataFrame
    sample_df = pd.DataFrame([
        {
            "scheme": "Parag Parikh Flexi Cap Fund",
            "current_value": 250000.0,
            "units": 3500.0,
            "nav": 71.4,
            "transactions": [
                {"date": date(2022, 5, 10), "amount": 150000.0}
            ]
        },
        {
            "scheme": "ICICI Prudential Liquid Fund",
            "current_value": 105000.0,
            "units": 300.0,
            "nav": 350.0,
            "transactions": [
                {"date": date(2024, 1, 15), "amount": 100000.0}
            ]
        }
    ])
    res = analyze_cas_holdings_capital_gains(sample_df, current_date=date(2024, 10, 1))
    assert res["has_data"] is True
    assert res["total_portfolio_value"] == 355000.0
    assert res["total_invested_amount"] == 250000.0
    assert res["total_unrealized_gain"] == 105000.0
    assert len(res["holdings"]) == 2
