"""Database module - now using repository pattern.

This module provides high-level database operations using repositories.
Direct SQL queries have been moved to repository classes.
"""

from modules.repositories import WeeklyStatusRepository, DailyInfoRepository
from modules.db_connection import db_query, db_transaction


# Initialize repositories
weekly_status_repo = WeeklyStatusRepository()
daily_info_repo = DailyInfoRepository()


def save_weekly_status(*, customer_id: int, start_date, end_date, report_text: str) -> None:
    """Save or update weekly status report."""
    weekly_status_repo.save_weekly_status(customer_id, start_date, end_date, report_text)


def load_weekly_status(*, customer_id: int, start_date, end_date) -> str | None:
    """Load weekly status report for a specific period."""
    return weekly_status_repo.load_weekly_status(customer_id, start_date, end_date)


def save_parsed_data(records):
    """Save parsed data to database."""
    return daily_info_repo.save_parsed_data(records)


# Legacy functions kept for backward compatibility
# These will be removed in future versions
def get_db_connection():
    """Legacy function - use repositories instead."""
    import streamlit as st
    import mysql.connector
    return mysql.connector.connect(**st.secrets["mysql"])


def get_or_create_customer(cursor, record):
    """Legacy function - use CustomerRepository instead."""
    # This is now handled in DailyInfoRepository.save_parsed_data
    pass


def _find_existing_record_id(cursor, customer_id, record_date):
    """Legacy function - use DailyInfoRepository instead."""
    return daily_info_repo.find_existing_record_id(customer_id, record_date)


def _delete_daily_record(cursor, record_id):
    """Legacy function - use DailyInfoRepository instead."""
    daily_info_repo.delete_daily_record(record_id)


def _insert_daily_info(cursor, customer_id, record):
    """Legacy function - use DailyInfoRepository instead."""
    return daily_info_repo.insert_daily_info(customer_id, record)


def _replace_daily_physicals(cursor, record_id, record):
    """Legacy function - use DailyInfoRepository instead."""
    daily_info_repo.replace_daily_physicals(record_id, record)


def _replace_daily_cognitives(cursor, record_id, record):
    """Legacy function - use DailyInfoRepository instead."""
    daily_info_repo.replace_daily_cognitives(record_id, record)


def _replace_daily_nursings(cursor, record_id, record):
    """Legacy function - use DailyInfoRepository instead."""
    daily_info_repo.replace_daily_nursings(record_id, record)


def _replace_daily_recoveries(cursor, record_id, record):
    """Legacy function - use DailyInfoRepository instead."""
    daily_info_repo.replace_daily_recoveries(record_id, record)
