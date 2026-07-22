"""Data loading, parsing, cleaning, and export functions."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

RAW_COLUMNS = [
    "TransactionID",
    "CustomerID",
    "CustomerDOB",
    "CustGender",
    "CustLocation",
    "CustAccountBalance",
    "TransactionDate",
    "TransactionTime",
    "TransactionAmount (INR)",
]

COLUMN_MAP = {
    "TransactionID": "transaction_id",
    "CustomerID": "customer_id",
    "CustomerDOB": "customer_dob_raw",
    "CustGender": "gender",
    "CustLocation": "customer_location",
    "CustAccountBalance": "account_balance_inr",
    "TransactionDate": "transaction_date_raw",
    "TransactionTime": "transaction_time_raw",
    "TransactionAmount (INR)": "transaction_amount_inr",
}

READ_DTYPES = {
    "TransactionID": "string",
    "CustomerID": "string",
    "CustomerDOB": "string",
    "CustGender": "string",
    "CustLocation": "string",
    "CustAccountBalance": "float64",
    "TransactionDate": "string",
    "TransactionTime": "Int64",
    "TransactionAmount (INR)": "float64",
}


def load_raw_transactions(path: Path, nrows: int | None = None) -> pd.DataFrame:
    """Load the raw CSV with explicit column types and schema checks."""
    if not path.exists():
        raise FileNotFoundError(
            f"Raw dataset not found at {path}. Place bank_transactions.csv in data/raw/."
        )

    frame = pd.read_csv(
        path,
        dtype=READ_DTYPES,
        usecols=RAW_COLUMNS,
        nrows=nrows,
        low_memory=False,
    )
    missing = sorted(set(RAW_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Raw dataset is missing required columns: {missing}")
    return frame


def _strip_string(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().replace("", pd.NA)


def normalize_location(series: pd.Series) -> pd.Series:
    """Standardize location strings without making risky geographic corrections."""
    cleaned = _strip_string(series).str.upper()
    cleaned = cleaned.str.replace(r"\s+", " ", regex=True)
    cleaned = cleaned.str.replace(r"\s*,\s*", ", ", regex=True)
    cleaned = cleaned.str.replace(r"[^A-Z0-9,()&/ .'-]", "", regex=True)
    return cleaned.replace("", pd.NA)


def parse_transaction_date(series: pd.Series) -> pd.Series:
    """Parse transaction dates stored in day/month/two-digit-year format."""
    return pd.to_datetime(_strip_string(series), format="%d/%m/%y", errors="coerce")


def parse_customer_dob(series: pd.Series, reference_date: pd.Timestamp) -> pd.Series:
    """Parse DOB values and resolve two-digit years using plausible ages.

    Pandas interprets two-digit years using a fixed pivot that is unsuitable for
    customer data. We parse day/month/year manually, initially map years to the
    1900s, and move future dates back by 100 years.
    """
    text = _strip_string(series)
    parts = text.str.extract(r"^(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})$")
    day = pd.to_numeric(parts[0], errors="coerce")
    month = pd.to_numeric(parts[1], errors="coerce")
    year_raw = pd.to_numeric(parts[2], errors="coerce")

    year = year_raw.where(year_raw >= 100, year_raw + 1900)
    date_text = (
        year.astype("Int64").astype("string")
        + "-"
        + month.astype("Int64").astype("string").str.zfill(2)
        + "-"
        + day.astype("Int64").astype("string").str.zfill(2)
    )
    candidate = pd.to_datetime(date_text, format="%Y-%m-%d", errors="coerce")
    future_mask = candidate > reference_date
    candidate.loc[future_mask] = candidate.loc[future_mask] - pd.DateOffset(years=100)

    # Known placeholder and implausible birth dates are not usable demographics.
    candidate = candidate.mask(candidate.dt.year <= 1900)
    return candidate


def parse_transaction_time(series: pd.Series) -> pd.DataFrame:
    """Parse HHMMSS-style values and return validated time components."""
    numeric = pd.to_numeric(series, errors="coerce").astype("Int64")
    text = numeric.astype("string").str.zfill(6)
    hour = pd.to_numeric(text.str.slice(0, 2), errors="coerce").astype("Int64")
    minute = pd.to_numeric(text.str.slice(2, 4), errors="coerce").astype("Int64")
    second = pd.to_numeric(text.str.slice(4, 6), errors="coerce").astype("Int64")

    valid = hour.between(0, 23) & minute.between(0, 59) & second.between(0, 59)
    hour = hour.where(valid)
    minute = minute.where(valid)
    second = second.where(valid)

    time_string = (
        hour.astype("string").str.zfill(2)
        + ":"
        + minute.astype("string").str.zfill(2)
        + ":"
        + second.astype("string").str.zfill(2)
    ).where(valid)

    return pd.DataFrame(
        {
            "transaction_hour": hour,
            "transaction_minute": minute,
            "transaction_second": second,
            "transaction_time": time_string,
            "valid_transaction_time": valid.fillna(False),
        },
        index=series.index,
    )


def clean_transactions(raw: pd.DataFrame) -> pd.DataFrame:
    """Create a validated, analysis-ready transaction table."""
    missing = sorted(set(RAW_COLUMNS) - set(raw.columns))
    if missing:
        raise ValueError(f"Cannot clean data; required columns missing: {missing}")

    frame = raw.rename(columns=COLUMN_MAP).copy()
    frame["transaction_id"] = _strip_string(frame["transaction_id"])
    frame["customer_id"] = _strip_string(frame["customer_id"])
    frame["gender"] = _strip_string(frame["gender"]).str.upper()
    frame["gender"] = frame["gender"].where(frame["gender"].isin(["M", "F"]), pd.NA)
    frame["customer_location"] = normalize_location(frame["customer_location"])

    frame["account_balance_inr"] = pd.to_numeric(
        frame["account_balance_inr"], errors="coerce"
    )
    frame["transaction_amount_inr"] = pd.to_numeric(
        frame["transaction_amount_inr"], errors="coerce"
    )

    frame["transaction_date"] = parse_transaction_date(frame["transaction_date_raw"])
    reference_date = frame["transaction_date"].max()
    if pd.isna(reference_date):
        reference_date = pd.Timestamp("2016-12-31")

    frame["customer_dob"] = parse_customer_dob(frame["customer_dob_raw"], reference_date)
    age = (frame["transaction_date"] - frame["customer_dob"]).dt.days / 365.2425
    frame["customer_age"] = np.floor(age).astype("Float64")
    frame["customer_age"] = frame["customer_age"].where(
        frame["customer_age"].between(18, 100)
    )

    time_parts = parse_transaction_time(frame["transaction_time_raw"])
    frame = pd.concat([frame, time_parts], axis=1)

    date_text = frame["transaction_date"].dt.strftime("%Y-%m-%d")
    frame["transaction_datetime"] = pd.to_datetime(
        date_text + " " + frame["transaction_time"], errors="coerce"
    )

    frame["transaction_weekday"] = frame["transaction_date"].dt.day_name()
    frame["is_weekend"] = frame["transaction_date"].dt.dayofweek.ge(5).astype("boolean")
    frame["transaction_month"] = frame["transaction_date"].dt.to_period("M").astype("string")

    hour = frame["transaction_hour"].astype("Float64")
    frame["daypart"] = pd.cut(
        hour,
        bins=[-1, 5, 11, 16, 20, 23],
        labels=["night", "morning", "afternoon", "evening", "late_evening"],
    ).astype("string")

    positive_amount = frame["transaction_amount_inr"].where(
        frame["transaction_amount_inr"] > 0
    )
    frame["balance_to_transaction_ratio"] = (
        frame["account_balance_inr"] / positive_amount
    ).replace([np.inf, -np.inf], np.nan)

    frame["log_transaction_amount"] = np.log1p(
        frame["transaction_amount_inr"].clip(lower=0)
    )
    frame["log_account_balance"] = np.log1p(frame["account_balance_inr"].clip(lower=0))

    output_columns = [
        "transaction_id",
        "customer_id",
        "customer_dob",
        "customer_age",
        "gender",
        "customer_location",
        "account_balance_inr",
        "transaction_date",
        "transaction_time",
        "transaction_datetime",
        "transaction_hour",
        "transaction_weekday",
        "transaction_month",
        "daypart",
        "is_weekend",
        "transaction_amount_inr",
        "balance_to_transaction_ratio",
        "log_transaction_amount",
        "log_account_balance",
    ]
    return frame[output_columns].sort_values(
        ["transaction_date", "transaction_time", "transaction_id"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)


def export_dataframe(frame: pd.DataFrame, path: Path) -> None:
    """Export a DataFrame to CSV using stable settings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, date_format="%Y-%m-%d")
