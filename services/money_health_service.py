"""
services/money_health_service.py
Service layer for orchestrating Money Health Score calculations, profile integration,
change detection, and persistence.
"""
from datetime import datetime
import json
from typing import Any, Dict, List, Optional

from data.database import get_connection, init_db
from services.profile_service import get_profile
from services.risk_profile_service import get_latest_risk_assessment
from utils.money_health_score import calculate_money_health_score


def get_or_calculate_health_score(
    user_id: str = "default_user",
    cas_portfolio: Optional[Dict[str, Any]] = None,
    force_recalculate: bool = False,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve latest persisted Money Health Score or recalculate if:
    1. No score is persisted yet.
    2. User explicitly triggers recalculation (force_recalculate=True).
    3. Financial Profile was updated since the last calculation.
    """
    init_db(db_path)
    profile = get_profile(user_id=user_id, db_path=db_path)
    profile_updated_at = profile.get("updated_at") if profile else None

    # Check existing persisted score
    if not force_recalculate and profile_updated_at:
        persisted = get_latest_health_score(user_id=user_id, db_path=db_path)
        if persisted and persisted.get("profile_updated_at") == profile_updated_at:
            # Check if CAS portfolio state is consistent
            return persisted

    # Needs fresh calculation
    risk_assessment = get_latest_risk_assessment(user_id=user_id, db_path=db_path)
    goals = profile.get("goals") if profile else []

    calc_result = calculate_money_health_score(
        profile_data=profile,
        goals=goals,
        risk_assessment=risk_assessment,
        cas_portfolio=cas_portfolio,
    )

    now_str = datetime.now().isoformat()
    calc_result["calculated_at"] = now_str
    calc_result["profile_updated_at"] = profile_updated_at

    # Persist the score
    if profile:
        _persist_health_score(calc_result, user_id=user_id, profile_updated_at=profile_updated_at, db_path=db_path)

    return calc_result


def _persist_health_score(
    result: Dict[str, Any],
    user_id: str = "default_user",
    profile_updated_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> None:
    """Save calculated score record in SQLite, marking previous as not latest."""
    init_db(db_path)
    now_str = result.get("calculated_at") or datetime.now().isoformat()

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE money_health_scores SET is_latest = 0 WHERE user_id = ?",
            (user_id,)
        )
        cursor.execute(
            """
            INSERT INTO money_health_scores (
                user_id, overall_score, rating, data_completeness,
                breakdown_json, insights_json, recommendations_json,
                profile_updated_at, calculated_at, is_latest
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                user_id,
                result.get("overall_score"),
                result.get("rating"),
                result.get("data_completeness", 0.0),
                json.dumps(result.get("components", {})),
                json.dumps(result.get("insights", [])),
                json.dumps(result.get("recommendations", [])),
                profile_updated_at,
                now_str,
            ),
        )
        conn.commit()


def get_latest_health_score(
    user_id: str = "default_user",
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieve the latest persisted health score record."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM money_health_scores
            WHERE user_id = ? AND is_latest = 1
            ORDER BY id DESC LIMIT 1
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        data = dict(row)
        try:
            components = json.loads(data["breakdown_json"])
            insights = json.loads(data["insights_json"])
            recommendations = json.loads(data["recommendations_json"])
        except Exception:
            components, insights, recommendations = {}, [], []

        return {
            "id": data["id"],
            "overall_score": data["overall_score"],
            "rating": data["rating"],
            "data_completeness": data["data_completeness"],
            "is_sufficient_data": data["overall_score"] is not None,
            "components": components,
            "insights": insights,
            "recommendations": recommendations,
            "profile_updated_at": data["profile_updated_at"],
            "calculated_at": data["calculated_at"],
            "excluded_components": [
                comp.get("name")
                for comp in components.values()
                if not comp.get("is_available")
            ],
            "disclaimer": (
                "Educational Financial Health Notice: The Money Health Score is a deterministic educational indicator "
                "designed to highlight personal finance patterns and general best practices. It does not constitute official "
                "SEBI investment advice, credit scoring, or a guarantee of investment results. Actual financial planning should "
                "be customized to your individual tax status and personal goals."
            ),
        }


def get_health_score_history(
    user_id: str = "default_user",
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve chronological history of health scores."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, overall_score, rating, data_completeness, calculated_at, is_latest
            FROM money_health_scores
            WHERE user_id = ?
            ORDER BY calculated_at DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
