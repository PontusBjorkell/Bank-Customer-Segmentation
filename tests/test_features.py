from __future__ import annotations

import pandas as pd

from bank_customer_segmentation.data import clean_transactions
from bank_customer_segmentation.features import build_customer_features


def test_customer_features_create_one_row_per_customer(raw_sample: pd.DataFrame) -> None:
    clean = clean_transactions(raw_sample)
    features = build_customer_features(clean)
    assert features["customer_id"].is_unique
    assert len(features) == 3


def test_customer_aggregation_is_correct(raw_sample: pd.DataFrame) -> None:
    clean = clean_transactions(raw_sample)
    features = build_customer_features(clean).set_index("customer_id")
    assert features.loc["C1", "transaction_count"] == 2
    assert features.loc["C1", "total_transaction_amount"] == 75.0
    assert features.loc["C1", "active_days"] == 2
    assert not bool(features.loc["C1", "is_single_transaction_customer"])
    assert bool(features.loc["C2", "is_single_transaction_customer"])
    assert features.loc["C2", "transaction_amount_std"] == 0.0
