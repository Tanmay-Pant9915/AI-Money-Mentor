from unittest.mock import patch, MagicMock

from utils.ai_summary import generate_portfolio_summary


# ---------------------------------------------------------------------------
# Sample data — matches the shape produced by portfolio_service.analyze_portfolio
# ---------------------------------------------------------------------------
SAMPLE_SINGLE_FUND = {
    "scheme": "ABC Large Cap Fund - Direct Growth",
    "current_value": 7327.74,
    "xirr": 10.01,
    "expense_ratio": 0.75,
    "annual_expense_cost": 54.96
}

SAMPLE_MULTI_FUND = [
    {
        "scheme": "ABC Large Cap Fund - Direct Growth",
        "current_value": 7327.74,
        "xirr": 10.01,
        "expense_ratio": 0.75,
        "annual_expense_cost": 54.96
    },
    {
        "scheme": "XYZ Mid Cap Fund - Direct Growth",
        "current_value": 15000.00,
        "xirr": 14.50,
        "expense_ratio": 0.90,
        "annual_expense_cost": 135.00
    }
]

MOCK_RESPONSE = """
### 🏥 Portfolio Health
Portfolio looks healthy with 1 fund.

### 📈 Returns Analysis
• ABC Large Cap Fund - Direct Growth: XIRR 10.01% — Average

### 💸 Expense Analysis
• ABC Large Cap Fund - Direct Growth: Expense Ratio 0.75% — costs ₹55/year
Total annual fee drag: ₹55

### ⚠️ Key Risks
• Single fund concentration risk.

### ✅ Actionable Recommendations
1. Consider diversifying across more funds.
""".strip()


def _make_mock_client():
    """Return a mock Groq client that returns MOCK_RESPONSE."""
    mock_choice = MagicMock()
    mock_choice.message.content = MOCK_RESPONSE

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion
    return mock_client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_generate_portfolio_summary_single_fund_dict():
    """A bare dict (single fund) should be accepted and produce a string."""
    with patch("utils.ai_summary.client", _make_mock_client()):
        result = generate_portfolio_summary(SAMPLE_SINGLE_FUND)

    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_portfolio_summary_list_of_funds():
    """A list of fund dicts should also produce a string."""
    with patch("utils.ai_summary.client", _make_mock_client()):
        result = generate_portfolio_summary(SAMPLE_MULTI_FUND)

    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_portfolio_summary_contains_sections():
    """Output should contain all five required section headings."""
    with patch("utils.ai_summary.client", _make_mock_client()):
        result = generate_portfolio_summary(SAMPLE_SINGLE_FUND)

    assert "Portfolio Health" in result
    assert "Returns Analysis" in result
    assert "Expense Analysis" in result
    assert "Key Risks" in result
    assert "Actionable Recommendations" in result