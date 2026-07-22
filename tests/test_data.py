from __future__ import annotations

import pandas as pd

from bank_customer_segmentation.data import clean_transactions, parse_transaction_time


def test_clean_transactions_preserves_rows(raw_sample: pd.DataFrame) -> None:
    clean = clean_transactions(raw_sample)
    assert len(clean) == len(raw_sample)
    assert clean["transaction_id"].tolist() == ["T4", "T1", "T3", "T2"]


def test_cleaning_standardizes_categories_and_placeholders(raw_sample: pd.DataFrame) -> None:
    clean = clean_transactions(raw_sample)
    c2 = clean.loc[clean["customer_id"] == "C2"].iloc[0]
    assert pd.isna(c2["gender"])
    assert pd.isna(c2["customer_dob"])
    assert pd.isna(c2["transaction_time"])


def test_location_is_normalized(raw_sample: pd.DataFrame) -> None:
    clean = clean_transactions(raw_sample)
    locations = clean.loc[clean["customer_id"] == "C1", "customer_location"]
    assert set(locations.dropna()) == {"MUMBAI"}


def test_transaction_time_parser_rejects_invalid_values() -> None:
    parsed = parse_transaction_time(pd.Series([0, 93015, 235959, 240000, None]))
    assert parsed["valid_transaction_time"].tolist() == [True, True, True, False, False]
    assert parsed.loc[1, "transaction_time"] == "09:30:15"
