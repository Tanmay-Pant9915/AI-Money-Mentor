import pandas as pd
import pytest
from datetime import datetime
from utils.pdf_parser import parse_funds

def test_parse_funds_basic():
    text = """
Mutual Fund Holdings
Scheme: ABC Large Cap Fund - Direct Growth
Folio No: 1234567/89
Units Held: 125.432
NAV: n58.42
Current Value: n7,327.74
Recent Transactions
01-Apr-2026 | Purchase | n5,000.50
15-Apr-2026 | SIP Purchase | n2,000.00
"""
    df = parse_funds(text)
    
    assert len(df) == 1
    assert df.loc[0, "scheme"] == "ABC Large Cap Fund - Direct Growth"
    assert df.loc[0, "folio"] == "1234567/89"
    assert df.loc[0, "units"] == 125.432
    assert df.loc[0, "nav"] == 58.42
    assert df.loc[0, "current_value"] == 7327.74
    
    txns = df.loc[0, "transactions"]
    assert len(txns) == 2
    assert txns[0]["date"] == datetime(2026, 4, 1, 0, 0)
    assert txns[0]["type"] == "Purchase"
    assert txns[0]["amount"] == 5000.50
    assert txns[1]["amount"] == 2000.00

def test_parse_funds_different_folios():
    text = """
Scheme: Fund One
Folio: F12345
Units Held: 10
NAV: n10
Current Value: n100
Recent Transactions
01-Apr-2026 | Purchase | 100

Scheme: Fund Two
Folio No. F67890
Units Held: 20
NAV: 10
Current Value: 200
Recent Transactions
01-Apr-2026 | Purchase | 200

Scheme: Fund Three
FOLIO NO: 987-654-321
Units Held: 30
NAV: 10
Current Value: 300
"""
    df = parse_funds(text)
    assert len(df) == 3
    assert df.loc[0, "folio"] == "F12345"
    assert df.loc[1, "folio"] == "F67890"
    assert df.loc[2, "folio"] == "987-654-321"

def test_parse_funds_empty_protection():
    text = "Some random text that does not contain the keyword Scheme."
    df = parse_funds(text)
    
    assert df.empty
    expected_cols = ["scheme", "folio", "units", "nav", "current_value", "transactions"]
    assert list(df.columns) == expected_cols
