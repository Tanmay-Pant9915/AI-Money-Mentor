"""
services/risk_profile_service.py
Service layer for risk questionnaire assessment, scoring, and history persistence.
"""
from datetime import datetime
import json
from typing import Any, Dict, List, Optional

from data.database import get_connection, init_db
from utils.risk_scoring import RISK_QUESTIONS, calculate_risk_profile


def submit_risk_assessment(
    answers: Dict[str, int],
    user_id: str = "default_user",
    financial_profile: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Score questionnaire answers and persist as the user's latest assessment.
    Marks all prior assessments as is_latest = 0, preserving history.
    """
    init_db(db_path)
    result = calculate_risk_profile(answers, financial_profile=financial_profile)
    now_str = datetime.now().isoformat()

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Mark older assessments as not latest
        cursor.execute(
            "UPDATE risk_assessments SET is_latest = 0 WHERE user_id = ?",
            (user_id,)
        )

        # Insert new latest assessment
        cursor.execute(
            """
            INSERT INTO risk_assessments (
                user_id, score, classification, tolerance_score, capacity_score,
                responses_json, factors_json, constraints_json, created_at, is_latest
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                user_id,
                result["score"],
                result["classification"],
                result["tolerance_score"],
                result["capacity_score"],
                json.dumps(answers),
                json.dumps(result["factors"]),
                json.dumps(result["constraints"]),
                now_str,
            )
        )
        assessment_id = cursor.lastrowid
        conn.commit()

    result["id"] = assessment_id
    result["created_at"] = now_str
    result["answers"] = answers
    return result


def get_latest_risk_assessment(
    user_id: str = "default_user",
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve the most recent risk assessment for a given user.
    Returns None if no assessment has been completed.
    """
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM risk_assessments
            WHERE user_id = ? AND is_latest = 1
            ORDER BY id DESC LIMIT 1
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        data = dict(row)
        try:
            answers = json.loads(data["responses_json"])
        except Exception:
            answers = {}

        # Re-derive full educational text deterministically
        profile_res = calculate_risk_profile(answers)
        profile_res["id"] = data["id"]
        profile_res["created_at"] = data["created_at"]
        profile_res["answers"] = answers
        return profile_res


def get_risk_assessment_history(
    user_id: str = "default_user",
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve chronological list of past risk assessments.
    """
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, score, classification, tolerance_score, capacity_score,
                   created_at, is_latest
            FROM risk_assessments
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (user_id,)
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
