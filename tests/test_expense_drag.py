"""
tests/test_expense_drag.py — Unit tests for utils/expense_drag.py
"""
import pytest
from utils.expense_drag import calculate_expense_drag


class TestCalculateExpenseDrag:

    def test_basic_calculation(self):
        """₹9,850 at 0.75% expense ratio = ₹73.875 annual drag."""
        cost = calculate_expense_drag(current_value=9850, expense_ratio=0.75)
        assert cost == pytest.approx(73.875, rel=1e-4)

    def test_zero_value_returns_zero(self):
        assert calculate_expense_drag(current_value=0, expense_ratio=1.0) == 0.0

    def test_none_value_returns_zero(self):
        assert calculate_expense_drag(current_value=None, expense_ratio=1.0) == 0.0

    def test_none_ratio_returns_zero(self):
        assert calculate_expense_drag(current_value=10000, expense_ratio=None) == 0.0

    def test_negative_value_returns_zero(self):
        assert calculate_expense_drag(current_value=-500, expense_ratio=1.0) == 0.0

    def test_negative_ratio_returns_zero(self):
        assert calculate_expense_drag(current_value=10000, expense_ratio=-1.0) == 0.0

    def test_large_portfolio(self):
        """₹10,00,000 at 1.5% = ₹15,000 annual drag."""
        cost = calculate_expense_drag(current_value=1_000_000, expense_ratio=1.5)
        assert cost == pytest.approx(15_000.0, rel=1e-6)