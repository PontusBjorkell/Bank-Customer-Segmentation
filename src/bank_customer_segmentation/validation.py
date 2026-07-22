"""Data-quality checks and validation reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .data import RAW_COLUMNS


@dataclass(frozen=True)
class ValidationResult:
    """Single validation metric suitable for tabular reporting."""

    check: str
    status: str
    value: Any
    threshold: str
    description: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "status": self.status,
            "value": self.value,
            "threshold": self.threshold,
            "description": self.description,
        }


def validate_raw_schema(frame: pd.DataFrame) -> None:
    """Raise an actionable error when the raw schema is incomplete."""
    missing = sorted(set(RAW_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Missing required raw columns: {missing}")


def build_quality_report(raw: pd.DataFrame, clean: pd.DataFrame) -> pd.DataFrame:
    """Build a compact report of raw and cleaned data-quality metrics."""
    validate_raw_schema(raw)

    results: list[ValidationResult] = []

    def add(
        check: str,
        value: Any,
        threshold: str,
        description: str,
        passed: bool,
    ) -> None:
        results.append(
            ValidationResult(
                check=check,
                status="PASS" if passed else "WARN",
                value=value,
                threshold=threshold,
                description=description,
            )
        )

    add("raw_row_count", len(raw), "> 0", "Number of raw transactions.", len(raw) > 0)
    add(
        "clean_row_count",
        len(clean),
        "equal raw_row_count",
        "Cleaning should not silently discard rows.",
        len(clean) == len(raw),
    )
    duplicate_ids = int(raw["TransactionID"].duplicated().sum())
    add(
        "duplicate_transaction_ids",
        duplicate_ids,
        "0",
        "Transaction identifiers should be unique.",
        duplicate_ids == 0,
    )
    missing_customer_ids = int(clean["customer_id"].isna().sum())
    add(
        "missing_customer_ids",
        missing_customer_ids,
        "0",
        "Rows without customer identifiers cannot support segmentation.",
        missing_customer_ids == 0,
    )
    invalid_dates = int(clean["transaction_date"].isna().sum())
    add(
        "invalid_transaction_dates",
        invalid_dates,
        "0",
        "Transaction dates should parse successfully.",
        invalid_dates == 0,
    )
    invalid_times = int(clean["transaction_time"].isna().sum())
    add(
        "invalid_transaction_times",
        invalid_times,
        "0",
        "Transaction times should be valid HHMMSS values.",
        invalid_times == 0,
    )
    invalid_gender = int(raw["CustGender"].notna().sum() - clean["gender"].notna().sum())
    add(
        "missing_or_invalid_gender",
        invalid_gender,
        "reported",
        "Missing and non-M/F values are standardized to null.",
        invalid_gender == 0,
    )
    missing_dob = int(clean["customer_dob"].isna().sum())
    add(
        "missing_or_invalid_dob",
        missing_dob,
        "reported",
        "Includes missing, placeholder, and unparseable dates of birth.",
        missing_dob == 0,
    )
    implausible_age = int((
        clean["customer_age"].notna()
        & ~clean["customer_age"].between(18, 100)
    ).sum())
    add(
        "implausible_clean_age",
        implausible_age,
        "0",
        "Clean ages must lie between 18 and 100.",
        implausible_age == 0,
    )
    negative_amounts = int(clean["transaction_amount_inr"].lt(0).sum())
    add(
        "negative_transaction_amounts",
        negative_amounts,
        "0",
        "Negative amounts require domain investigation.",
        negative_amounts == 0,
    )
    negative_balances = int(clean["account_balance_inr"].lt(0).sum())
    add(
        "negative_account_balances",
        negative_balances,
        "reported",
        "Negative balances are retained but explicitly reported.",
        negative_balances == 0,
    )

    for raw_column in RAW_COLUMNS:
        missing = int(raw[raw_column].isna().sum())
        add(
            f"raw_missing__{raw_column}",
            missing,
            "reported",
            f"Missing values in raw column {raw_column}.",
            missing == 0,
        )

    return pd.DataFrame([result.as_dict() for result in results])
