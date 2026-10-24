"""
tests/test_risk_profile_service.py
Integration tests for submitting risk questionnaires, retrieving latest assessment,
retaking flow, and history preservation.
"""
import os
import tempfile
import pytest

from services.risk_profile_service import (
    get_latest_risk_assessment,
    get_risk_assessment_history,
    submit_risk_assessment,
)
from utils.risk_scoring import RISK_QUESTIONS


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


def make_answers(score: int):
    return {q["id"]: score for q in RISK_QUESTIONS}


class TestRiskProfileService:

    def test_submit_and_retrieve_latest_assessment(self, temp_db):
        answers = {q["id"]: (2 if i % 2 == 0 else 3) for i, q in enumerate(RISK_QUESTIONS)}
        saved = submit_risk_assessment(answers, user_id="test_user", db_path=temp_db)
        assert saved is not None
        assert saved["score"] > 0
        assert saved["classification"] == "Moderate"

        latest = get_latest_risk_assessment(user_id="test_user", db_path=temp_db)
        assert latest is not None
        assert latest["score"] == saved["score"]
        assert latest["classification"] == "Moderate"
        assert latest["answers"]["q1_life_stage"] == answers["q1_life_stage"]

    def test_retaking_questionnaire_preserves_history(self, temp_db):
        # 1st attempt: Conservative (all 1s)
        ans1 = make_answers(1)
        submit_risk_assessment(ans1, user_id="user_history", db_path=temp_db)

        # 2nd attempt: Moderate (all 2s)
        ans2 = make_answers(2)
        submit_risk_assessment(ans2, user_id="user_history", db_path=temp_db)

        # 3rd attempt: Aggressive (all 4s)
        ans3 = make_answers(4)
        submit_risk_assessment(ans3, user_id="user_history", db_path=temp_db)

        # Check latest
        latest = get_latest_risk_assessment(user_id="user_history", db_path=temp_db)
        assert latest["classification"] == "Aggressive"
        assert latest["score"] == 100.0

        # Check history
        history = get_risk_assessment_history(user_id="user_history", db_path=temp_db)
        assert len(history) == 3
        # Exactly one record is is_latest = 1
        assert sum(1 for h in history if h["is_latest"] == 1) == 1
        # Latest record has is_latest == 1
        assert history[0]["is_latest"] == 1
        assert history[0]["classification"] == "Aggressive"

    def test_get_nonexistent_assessment(self, temp_db):
        assert get_latest_risk_assessment(user_id="nonexistent", db_path=temp_db) is None
        assert get_risk_assessment_history(user_id="nonexistent", db_path=temp_db) == []
