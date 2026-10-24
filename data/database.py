"""
data/database.py
Database initialization and connection management for AI Money Mentor.
Uses SQLite for robust local single-user persistence.
"""
import os
import sqlite3
from typing import Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "ai_money_mentor.db")


def get_db_path(custom_path: Optional[str] = None) -> str:
    """Return the absolute path to the SQLite database file."""
    if custom_path:
        return os.path.abspath(custom_path)
    return os.path.abspath(DEFAULT_DB_PATH)


from contextlib import contextmanager


@contextmanager
def get_connection(db_path: Optional[str] = None):
    """
    Establish and yield a connection to the SQLite database.
    Guarantees connection is closed when exiting context.
    """
    path = get_db_path(db_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()



def init_db(db_path: Optional[str] = None) -> None:
    """
    Initialize SQLite database tables idempotently.
    Safe to call repeatedly across restarts.
    """
    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS financial_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL DEFAULT 'default_user',
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                employment_status TEXT NOT NULL,
                monthly_income REAL NOT NULL,
                essential_expenses REAL NOT NULL,
                discretionary_expenses REAL NOT NULL,
                other_expenses REAL NOT NULL DEFAULT 0.0,
                savings_liquid REAL NOT NULL DEFAULT 0.0,
                outstanding_debt REAL NOT NULL DEFAULT 0.0,
                monthly_debt_repayment REAL NOT NULL DEFAULT 0.0,
                existing_investments REAL NOT NULL DEFAULT 0.0,
                dependents INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS financial_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'Other',
                target_amount REAL NOT NULL,
                target_date TEXT NOT NULL,
                current_amount REAL NOT NULL DEFAULT 0.0,
                monthly_contribution REAL NOT NULL DEFAULT 0.0,
                priority TEXT NOT NULL DEFAULT 'Medium',
                is_completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (profile_id) REFERENCES financial_profiles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS risk_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                score REAL NOT NULL,
                classification TEXT NOT NULL,
                tolerance_score REAL NOT NULL,
                capacity_score REAL NOT NULL,
                responses_json TEXT NOT NULL,
                factors_json TEXT NOT NULL,
                constraints_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_latest INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS money_health_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                overall_score INTEGER,
                rating TEXT,
                data_completeness REAL NOT NULL,
                breakdown_json TEXT NOT NULL,
                insights_json TEXT NOT NULL,
                recommendations_json TEXT NOT NULL,
                profile_updated_at TEXT,
                calculated_at TEXT NOT NULL,
                is_latest INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS financial_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                profile_id INTEGER,
                plan_name TEXT NOT NULL DEFAULT 'Monthly Financial Plan',
                created_at TEXT NOT NULL,
                input_snapshot_json TEXT NOT NULL,
                current_summary_json TEXT NOT NULL,
                recommended_budget_json TEXT NOT NULL,
                adjusted_budget_json TEXT NOT NULL,
                priorities_json TEXT NOT NULL,
                goals_allocation_json TEXT NOT NULL,
                ai_explanation TEXT,
                is_latest INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (profile_id) REFERENCES financial_profiles(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS retirement_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                profile_id INTEGER,
                plan_name TEXT NOT NULL DEFAULT 'Retirement & FIRE Plan',
                created_at TEXT NOT NULL,
                current_age INTEGER NOT NULL,
                target_retirement_age INTEGER NOT NULL,
                planning_age INTEGER NOT NULL DEFAULT 85,
                current_corpus REAL NOT NULL DEFAULT 0.0,
                monthly_contribution REAL NOT NULL DEFAULT 0.0,
                monthly_expenses_today REAL NOT NULL DEFAULT 0.0,
                inflation_rate REAL NOT NULL DEFAULT 6.0,
                pre_retirement_return REAL NOT NULL DEFAULT 10.0,
                post_retirement_return REAL NOT NULL DEFAULT 7.0,
                withdrawal_rate REAL NOT NULL DEFAULT 4.0,
                monthly_pension REAL NOT NULL DEFAULT 0.0,
                is_pension_inflation_indexed INTEGER NOT NULL DEFAULT 0,
                target_corpus REAL NOT NULL DEFAULT 0.0,
                projected_corpus REAL NOT NULL DEFAULT 0.0,
                required_monthly REAL NOT NULL DEFAULT 0.0,
                estimated_fire_age REAL,
                years_to_fire REAL,
                plan_details_json TEXT NOT NULL,
                is_latest INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (profile_id) REFERENCES financial_profiles(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS emergency_fund_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                plan_name TEXT NOT NULL DEFAULT 'Emergency Fund Plan',
                created_at TEXT NOT NULL,
                essential_expenses REAL NOT NULL DEFAULT 0.0,
                target_months REAL NOT NULL DEFAULT 6.0,
                target_amount REAL NOT NULL DEFAULT 0.0,
                current_savings REAL NOT NULL DEFAULT 0.0,
                fund_gap REAL NOT NULL DEFAULT 0.0,
                coverage_months REAL NOT NULL DEFAULT 0.0,
                monthly_contribution REAL NOT NULL DEFAULT 0.0,
                estimated_months INTEGER,
                status TEXT NOT NULL,
                plan_details_json TEXT NOT NULL,
                is_latest INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS insurance_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                assessment_name TEXT NOT NULL DEFAULT 'Insurance Assessment',
                created_at TEXT NOT NULL,
                health_personal_cover REAL NOT NULL DEFAULT 0.0,
                health_employer_cover REAL NOT NULL DEFAULT 0.0,
                health_target_cover REAL NOT NULL DEFAULT 0.0,
                health_gap REAL NOT NULL DEFAULT 0.0,
                life_existing_cover REAL NOT NULL DEFAULT 0.0,
                life_income_multiplier_years REAL NOT NULL DEFAULT 10.0,
                life_liabilities REAL NOT NULL DEFAULT 0.0,
                life_future_obligations REAL NOT NULL DEFAULT 0.0,
                life_eligible_assets REAL NOT NULL DEFAULT 0.0,
                life_estimated_need REAL NOT NULL DEFAULT 0.0,
                life_gap REAL NOT NULL DEFAULT 0.0,
                has_accident_disability_cover INTEGER NOT NULL DEFAULT 0,
                accident_cover_amount REAL NOT NULL DEFAULT 0.0,
                assessment_details_json TEXT NOT NULL,
                is_latest INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS tax_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                financial_year TEXT NOT NULL DEFAULT '2024-25',
                age INTEGER NOT NULL DEFAULT 30,
                salary_gross REAL NOT NULL DEFAULT 0.0,
                house_property_net REAL NOT NULL DEFAULT 0.0,
                other_sources_interest REAL NOT NULL DEFAULT 0.0,
                other_sources_other REAL NOT NULL DEFAULT 0.0,
                business_profession_net REAL NOT NULL DEFAULT 0.0,
                deductions_json TEXT NOT NULL,
                taxes_paid REAL NOT NULL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, financial_year)
            );

            CREATE TABLE IF NOT EXISTS tax_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                financial_year TEXT NOT NULL DEFAULT '2024-25',
                recommended_regime TEXT NOT NULL,
                tax_difference REAL NOT NULL DEFAULT 0.0,
                old_taxable_income REAL NOT NULL DEFAULT 0.0,
                old_total_tax REAL NOT NULL DEFAULT 0.0,
                new_taxable_income REAL NOT NULL DEFAULT 0.0,
                new_total_tax REAL NOT NULL DEFAULT 0.0,
                assessment_details_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_latest INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS tax_scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                scenario_name TEXT NOT NULL,
                financial_year TEXT NOT NULL DEFAULT '2024-25',
                total_outflow REAL NOT NULL DEFAULT 0.0,
                tax_saved REAL NOT NULL DEFAULT 0.0,
                scenario_details_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_goals_profile_id ON financial_goals(profile_id);
            CREATE INDEX IF NOT EXISTS idx_risk_user_id ON risk_assessments(user_id, is_latest);
            CREATE INDEX IF NOT EXISTS idx_health_user_id ON money_health_scores(user_id, is_latest);
            CREATE INDEX IF NOT EXISTS idx_plans_user_id ON financial_plans(user_id, is_latest);
            CREATE INDEX IF NOT EXISTS idx_retire_user_id ON retirement_plans(user_id, is_latest);
            CREATE INDEX IF NOT EXISTS idx_ef_user_id ON emergency_fund_plans(user_id, is_latest);
            CREATE INDEX IF NOT EXISTS idx_ins_user_id ON insurance_assessments(user_id, is_latest);
            CREATE INDEX IF NOT EXISTS idx_tax_prof_user_id ON tax_profiles(user_id, financial_year);
            CREATE INDEX IF NOT EXISTS idx_tax_assess_user_id ON tax_assessments(user_id, is_latest);
            CREATE INDEX IF NOT EXISTS idx_tax_scen_user_id ON tax_scenarios(user_id);
            """
        )

        # Idempotent schema migration for existing financial_goals tables
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(financial_goals);")
        existing_cols = {row["name"] for row in cursor.fetchall()}
        if "category" not in existing_cols:
            cursor.execute("ALTER TABLE financial_goals ADD COLUMN category TEXT NOT NULL DEFAULT 'Other';")
        if "priority" not in existing_cols:
            cursor.execute("ALTER TABLE financial_goals ADD COLUMN priority TEXT NOT NULL DEFAULT 'Medium';")
        if "monthly_contribution" not in existing_cols:
            cursor.execute("ALTER TABLE financial_goals ADD COLUMN monthly_contribution REAL NOT NULL DEFAULT 0.0;")
        if "is_completed" not in existing_cols:
            cursor.execute("ALTER TABLE financial_goals ADD COLUMN is_completed INTEGER NOT NULL DEFAULT 0;")

        conn.commit()
