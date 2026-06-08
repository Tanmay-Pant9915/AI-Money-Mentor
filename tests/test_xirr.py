from datetime import datetime
from utils.xirr import calculate_xirr


def test_xirr():
    cashflows = [
        (datetime(2025, 1, 1), -10000),
        (datetime(2026, 1, 1), 12000),
    ]

    result = calculate_xirr(cashflows)

    assert 0.19 < result < 0.21