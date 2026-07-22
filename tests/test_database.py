from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from bank_customer_segmentation.database import (
    build_database,
    database_table_counts,
    run_integrity_checks,
)


def _write_test_inputs(directory: Path) -> tuple[Path, Path]:
    transactions = pd.DataFrame(
        {
            "transaction_id": ["T1", "T2", "T3"],
            "customer_id": ["C1", "C1", "C2"],
            "customer_dob": ["1980-01-01", "1980-01-01", None],
            "customer_age": [36.0, 36.0, None],
            "gender": ["M", "M", "F"],
            "customer_location": ["MUMBAI", "MUMBAI", "DELHI"],
            "account_balance_inr": [10000.0, 11000.0, 5000.0],
            "transaction_date": ["2016-08-01", "2016-08-02", "2016-08-02"],
            "transaction_time": ["09:30:00", "12:30:00", "18:00:00"],
            "transaction_datetime": [
                "2016-08-01 09:30:00",
                "2016-08-02 12:30:00",
                "2016-08-02 18:00:00",
            ],
            "transaction_hour": [9, 12, 18],
            "transaction_weekday": ["Monday", "Tuesday", "Tuesday"],
            "transaction_month": ["2016-08", "2016-08", "2016-08"],
            "daypart": ["morning", "afternoon", "evening"],
            "is_weekend": [False, False, False],
            "transaction_amount_inr": [100.0, 200.0, 50.0],
            "balance_to_transaction_ratio": [100.0, 55.0, 100.0],
            "log_transaction_amount": [4.615, 5.303, 3.932],
            "log_account_balance": [9.210, 9.306, 8.517],
        }
    )

    customers = pd.DataFrame(
        {
            "customer_id": ["C1", "C2"],
            "gender": ["M", "F"],
            "customer_age": [36.0, None],
            "primary_location": ["MUMBAI", "DELHI"],
            "distinct_locations": [1, 1],
            "transaction_count": [2, 1],
            "total_transaction_amount": [300.0, 50.0],
            "average_transaction_amount": [150.0, 50.0],
            "median_transaction_amount": [150.0, 50.0],
            "minimum_transaction_amount": [100.0, 50.0],
            "maximum_transaction_amount": [200.0, 50.0],
            "transaction_amount_std": [70.71, 0.0],
            "average_account_balance": [10500.0, 5000.0],
            "median_account_balance": [10500.0, 5000.0],
            "minimum_account_balance": [10000.0, 5000.0],
            "maximum_account_balance": [11000.0, 5000.0],
            "account_balance_std": [707.1, 0.0],
            "first_transaction_date": ["2016-08-01", "2016-08-02"],
            "last_transaction_date": ["2016-08-02", "2016-08-02"],
            "average_transaction_hour": [10.5, 18.0],
            "weekend_transaction_share": [0.0, 0.0],
            "transaction_amount_cv": [0.4714, 0.0],
            "account_balance_cv": [0.0673, 0.0],
            "night_transaction_share": [0.0, 0.0],
            "morning_transaction_share": [0.5, 0.0],
            "afternoon_transaction_share": [0.5, 0.0],
            "evening_transaction_share": [0.0, 1.0],
            "late_evening_transaction_share": [0.0, 0.0],
            "active_days": [2, 1],
            "transactions_per_active_day": [1.0, 1.0],
            "balance_to_total_spend_ratio": [35.0, 100.0],
            "is_single_transaction_customer": [False, True],
            "log_total_transaction_amount": [5.707, 3.932],
            "log_average_transaction_amount": [5.017, 3.932],
            "log_average_account_balance": [9.259, 8.517],
        }
    )

    transaction_path = directory / "transactions_clean.csv"
    customer_path = directory / "customer_features.csv"
    transactions.to_csv(transaction_path, index=False)
    customers.to_csv(customer_path, index=False)
    return transaction_path, customer_path


def test_build_database_creates_tables_and_views(tmp_path: Path) -> None:
    transaction_path, customer_path = _write_test_inputs(tmp_path)
    root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "test.sqlite"

    summary = build_database(
        database_path=database_path,
        schema_path=root / "sql" / "create_schema.sql",
        views_path=root / "sql" / "create_views.sql",
        transactions_path=transaction_path,
        customer_features_path=customer_path,
        chunksize=2,
    )

    assert summary["table_counts"]["fact_transaction"] == 3
    assert summary["table_counts"]["dim_customer"] == 2

    with sqlite3.connect(database_path) as connection:
        counts = database_table_counts(connection)
        checks = run_integrity_checks(connection)
        customer_count = connection.execute(
            "SELECT COUNT(*) FROM vw_customer_360"
        ).fetchone()[0]
        monthly_total = connection.execute(
            "SELECT total_transaction_amount_inr FROM vw_monthly_kpis"
        ).fetchone()[0]

    assert counts["dim_location"] == 2
    assert checks["integrity_check"] == "ok"
    assert checks["foreign_key_violations"] == 0
    assert customer_count == 2
    assert monthly_total == 350.0
