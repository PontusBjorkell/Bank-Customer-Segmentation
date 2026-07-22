from __future__ import annotations

import numpy as np
import pandas as pd

from bank_customer_segmentation.statistics import (
    cluster_distinguishability_importance,
    cluster_distribution,
    kruskal_wallis_by_cluster,
    standardized_effect_range,
)


def test_cluster_distribution_sums_to_one() -> None:
    assignments = pd.DataFrame(
        {
            "customer_id": ["A", "B", "C", "D"],
            "cluster": [0, 0, 1, 1],
        }
    )
    result = cluster_distribution(assignments)
    assert result["customer_count"].sum() == 4
    assert np.isclose(result["customer_share"].sum(), 1.0)


def test_kruskal_and_effect_range_outputs() -> None:
    frame = pd.DataFrame(
        {
            "cluster": [0, 0, 0, 1, 1, 1],
            "amount": [1, 2, 3, 10, 11, 12],
        }
    )
    tests = kruskal_wallis_by_cluster(frame, ("amount",))
    assert tests.loc[0, "feature"] == "amount"

    profile = pd.DataFrame(
        {"cluster": [0, 1], "feature_a": [-1.0, 2.0], "feature_b": [0.0, 0.5]}
    )
    ranges = standardized_effect_range(profile)
    assert ranges.loc[0, "feature"] == "feature_a"
    assert ranges.loc[0, "standardized_range"] == 3.0


def test_surrogate_feature_importance() -> None:
    rng = np.random.default_rng(7)
    x = rng.normal(size=(300, 3))
    labels = (x[:, 0] > 0).astype(int)
    importance, diagnostics = cluster_distinguishability_importance(
        x,
        labels,
        ("signal", "noise_1", "noise_2"),
        sample_size=300,
    )

    assert importance.iloc[0]["feature"] == "signal"
    assert diagnostics["accuracy"] > 0.8
