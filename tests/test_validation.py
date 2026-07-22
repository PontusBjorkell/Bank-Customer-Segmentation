from __future__ import annotations

import pandas as pd
import pytest

from bank_customer_segmentation.data import clean_transactions
from bank_customer_segmentation.validation import build_quality_report, validate_raw_schema


def test_schema_validation_rejects_missing_columns(raw_sample: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="Missing required raw columns"):
        validate_raw_schema(raw_sample.drop(columns=["CustomerID"]))


def test_quality_report_flags_known_issues(raw_sample: pd.DataFrame) -> None:
    clean = clean_transactions(raw_sample)
    report = build_quality_report(raw_sample, clean).set_index("check")
    assert report.loc["raw_row_count", "status"] == "PASS"
    assert report.loc["invalid_transaction_times", "value"] == 1
    assert report.loc["missing_or_invalid_gender", "value"] == 1
