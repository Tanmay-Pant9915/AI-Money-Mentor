"""
tests/test_financial_mentor_service.py
Unit and integration tests for AI Financial Mentor service, mocking LLM calls.
"""
from unittest.mock import MagicMock
import pytest

from services.financial_mentor_service import ask_financial_mentor


def test_mentor_fallback_when_client_none():
    res = ask_financial_mentor(
        user_query="How healthy is my financial situation?",
        user_id="test_user_offline",
        groq_client=None,
    )
    assert res.is_ai_generated is False
    assert "Financial Overview" in res.content
    assert res.intent == "HEALTH_SCORE"
    assert res.error_note is not None


def test_mentor_successful_ai_response():
    # Mock Groq client
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Based on your financial data, your emergency fund currently covers 6 months of living expenses."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    res = ask_financial_mentor(
        user_query="Analyze my emergency fund",
        user_id="test_user_ai",
        groq_client=mock_client,
    )

    assert res.is_ai_generated is True
    assert "emergency fund currently covers 6 months" in res.content
    assert res.intent == "EMERGENCY_FUND"
    assert mock_client.chat.completions.create.called


def test_mentor_graceful_exception_handling():
    # Mock Groq client raising API error
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("Groq API 500 Internal Error")

    res = ask_financial_mentor(
        user_query="Which tax regime is better for me?",
        user_id="test_user_err",
        groq_client=mock_client,
    )

    assert res.is_ai_generated is False
    assert "Financial Overview" in res.content
    assert "AI service connection notice" in res.error_note


def test_mentor_what_if_scenario_simulation():
    # Even when offline, what-if should compute simulation
    res = ask_financial_mentor(
        user_query="What if I save ₹5,000 more each month?",
        user_id="test_user_whatif",
        groq_client=None,
    )
    assert res.intent == "WHAT_IF_SCENARIO"
    # Should include scenario section in fallback
    assert res.simulation_result is not None
    assert "₹5,000" in res.simulation_result.get("extra_monthly_amount", "")
