"""Customer-level feature engineering for segmentation."""

from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_CLEAN_COLUMNS = {
    "transaction_id",
    "customer_id",
    "customer_age",
    "gender",
    "customer_location",
    "account_balance_inr",
    "transaction_date",
    "transaction_hour",
    "daypart",
    "is_weekend",
    "transaction_amount_inr",
}


def _build_primary_value_table(
    frame: pd.DataFrame,
    value_column: str,
    output_column: str,
) -> pd.DataFrame:
    """Return the most frequent non-null value for each customer.

    Ties are resolved deterministically by sorting the value column.
    """
    usable = frame.loc[
        frame["customer_id"].notna() & frame[value_column].notna(),
        ["customer_id", value_column],
    ]

    if usable.empty:
        return pd.DataFrame(columns=["customer_id", output_column])

    counts = (
        usable.groupby(["customer_id", value_column], observed=True, sort=False)
        .size()
        .rename("value_count")
        .reset_index()
    )

    primary = (
        counts.sort_values(
            ["customer_id", "value_count", value_column],
            ascending=[True, False, True],
            kind="stable",
        )
        .drop_duplicates("customer_id")
        .rename(columns={value_column: output_column})
        [["customer_id", output_column]]
    )

    return primary


def build_customer_features(clean: pd.DataFrame) -> pd.DataFrame:
    """Aggregate cleaned transactions into one row per customer.

    The implementation uses vectorized pandas aggregations and avoids
    Python-level ``groupby.apply`` operations, which are prohibitively slow
    when the dataset contains hundreds of thousands of customer groups.
    """
    missing = sorted(REQUIRED_CLEAN_COLUMNS - set(clean.columns))
    if missing:
        raise ValueError(
            f"Clean transaction table is missing columns: {missing}"
        )

    usable = clean.loc[clean["customer_id"].notna()].copy()

    if usable.empty:
        return pd.DataFrame(columns=["customer_id"])

    grouped = usable.groupby(
        "customer_id",
        sort=False,
        observed=True,
        dropna=False,
    )

    customer = grouped.agg(
        customer_age=("customer_age", "median"),
        distinct_locations=("customer_location", "nunique"),
        transaction_count=("transaction_id", "count"),
        total_transaction_amount=("transaction_amount_inr", "sum"),
        average_transaction_amount=("transaction_amount_inr", "mean"),
        median_transaction_amount=("transaction_amount_inr", "median"),
        minimum_transaction_amount=("transaction_amount_inr", "min"),
        maximum_transaction_amount=("transaction_amount_inr", "max"),
        transaction_amount_std=("transaction_amount_inr", "std"),
        average_account_balance=("account_balance_inr", "mean"),
        median_account_balance=("account_balance_inr", "median"),
        minimum_account_balance=("account_balance_inr", "min"),
        maximum_account_balance=("account_balance_inr", "max"),
        account_balance_std=("account_balance_inr", "std"),
        first_transaction_date=("transaction_date", "min"),
        last_transaction_date=("transaction_date", "max"),
        average_transaction_hour=("transaction_hour", "mean"),
        weekend_transaction_share=("is_weekend", "mean"),
    ).reset_index()

    primary_gender = _build_primary_value_table(
        usable,
        value_column="gender",
        output_column="gender",
    )
    primary_location = _build_primary_value_table(
        usable,
        value_column="customer_location",
        output_column="primary_location",
    )

    customer = customer.merge(
        primary_gender,
        on="customer_id",
        how="left",
        validate="one_to_one",
    )
    customer = customer.merge(
        primary_location,
        on="customer_id",
        how="left",
        validate="one_to_one",
    )

    customer["transaction_amount_std"] = (
        customer["transaction_amount_std"].fillna(0.0)
    )
    customer["account_balance_std"] = (
        customer["account_balance_std"].fillna(0.0)
    )

    customer["transaction_amount_cv"] = np.where(
        customer["average_transaction_amount"].abs() > 0,
        customer["transaction_amount_std"]
        / customer["average_transaction_amount"].abs(),
        np.nan,
    )

    customer["account_balance_cv"] = np.where(
        customer["average_account_balance"].abs() > 0,
        customer["account_balance_std"]
        / customer["average_account_balance"].abs(),
        np.nan,
    )

    daypart_counts = (
        usable.assign(daypart=usable["daypart"].fillna("unknown"))
        .groupby(
            ["customer_id", "daypart"],
            observed=True,
            sort=False,
        )
        .size()
        .unstack(fill_value=0)
    )

    expected_dayparts = [
        "night",
        "morning",
        "afternoon",
        "evening",
        "late_evening",
    ]

    daypart_counts = daypart_counts.reindex(
        columns=expected_dayparts,
        fill_value=0,
    )

    daypart_shares = daypart_counts.div(
        daypart_counts.sum(axis=1).replace(0, np.nan),
        axis=0,
    )

    daypart_shares.columns = [
        f"{column}_transaction_share"
        for column in daypart_shares.columns
    ]

    customer = customer.merge(
        daypart_shares.reset_index(),
        on="customer_id",
        how="left",
        validate="one_to_one",
    )

    customer["active_days"] = (
        customer["last_transaction_date"]
        - customer["first_transaction_date"]
    ).dt.days.add(1).astype("Int64")

    customer["transactions_per_active_day"] = (
        customer["transaction_count"]
        / customer["active_days"].replace(0, pd.NA)
    )

    customer["balance_to_total_spend_ratio"] = np.where(
        customer["total_transaction_amount"] > 0,
        customer["average_account_balance"]
        / customer["total_transaction_amount"],
        np.nan,
    )

    customer["is_single_transaction_customer"] = (
        customer["transaction_count"].eq(1)
    )

    customer["transaction_amount_cv"] = (
        customer["transaction_amount_cv"]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
    )

    customer["account_balance_cv"] = (
        customer["account_balance_cv"]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
    )

    customer["log_total_transaction_amount"] = np.log1p(
        customer["total_transaction_amount"].clip(lower=0)
    )

    customer["log_average_transaction_amount"] = np.log1p(
        customer["average_transaction_amount"].clip(lower=0)
    )

    customer["log_average_account_balance"] = np.log1p(
        customer["average_account_balance"].clip(lower=0)
    )

    preferred_order = [
        "customer_id",
        "gender",
        "customer_age",
        "primary_location",
        "distinct_locations",
        "transaction_count",
        "total_transaction_amount",
        "average_transaction_amount",
        "median_transaction_amount",
        "minimum_transaction_amount",
        "maximum_transaction_amount",
        "transaction_amount_std",
        "transaction_amount_cv",
        "average_account_balance",
        "median_account_balance",
        "minimum_account_balance",
        "maximum_account_balance",
        "account_balance_std",
        "account_balance_cv",
        "first_transaction_date",
        "last_transaction_date",
        "active_days",
        "transactions_per_active_day",
        "average_transaction_hour",
        "weekend_transaction_share",
        "night_transaction_share",
        "morning_transaction_share",
        "afternoon_transaction_share",
        "evening_transaction_share",
        "late_evening_transaction_share",
        "balance_to_total_spend_ratio",
        "is_single_transaction_customer",
        "log_total_transaction_amount",
        "log_average_transaction_amount",
        "log_average_account_balance",
    ]

    return (
        customer[preferred_order]
        .sort_values("customer_id", kind="stable")
        .reset_index(drop=True)
    )