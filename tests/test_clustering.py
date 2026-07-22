from __future__ import annotations

import numpy as np
import pandas as pd

from bank_customer_segmentation.clustering import (
    DEFAULT_SEGMENTATION_FEATURES,
    build_cluster_assignments,
    build_cluster_profile,
    candidate_results_frame,
    choose_kmeans_cluster_count,
    compare_kmeans_candidates,
    fit_final_kmeans,
    prepare_segmentation_data,
)


def _feature_frame(rows: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    frame = pd.DataFrame({"customer_id": [f"C{i:04d}" for i in range(rows)]})
    for feature in DEFAULT_SEGMENTATION_FEATURES:
        frame[feature] = rng.normal(size=rows)
    frame.loc[0, "customer_age"] = np.nan
    frame.loc[1, "log_average_account_balance"] = 1_000_000
    return frame


def test_prepare_segmentation_data_is_finite() -> None:
    prepared = prepare_segmentation_data(_feature_frame())

    assert prepared.matrix.shape == (120, len(DEFAULT_SEGMENTATION_FEATURES))
    assert np.isfinite(prepared.matrix).all()
    assert tuple(prepared.raw_features.columns) == DEFAULT_SEGMENTATION_FEATURES


def test_kmeans_comparison_and_final_assignments() -> None:
    prepared = prepare_segmentation_data(_feature_frame(180))
    results = compare_kmeans_candidates(
        prepared.matrix,
        cluster_range=range(2, 5),
        sample_size=150,
    )
    comparison = candidate_results_frame(results)
    selected = choose_kmeans_cluster_count(comparison)
    model, labels = fit_final_kmeans(prepared.matrix, selected)
    assignments = build_cluster_assignments(
        prepared.customer_ids,
        labels,
        prepared.matrix,
        model,
    )

    assert selected in {2, 3, 4}
    assert len(assignments) == 180
    assert assignments["cluster"].nunique() == selected
    assert assignments["assignment_confidence"].between(0, 1).all()


def test_cluster_profile_has_one_row_per_cluster() -> None:
    frame = _feature_frame(150)
    prepared = prepare_segmentation_data(frame)
    model, labels = fit_final_kmeans(prepared.matrix, 3)
    assignments = build_cluster_assignments(
        prepared.customer_ids,
        labels,
        prepared.matrix,
        model,
    )
    profile = build_cluster_profile(frame, assignments)

    assert len(profile) == 3
    assert profile["customer_count"].sum() == 150
    assert np.isclose(profile["customer_share"].sum(), 1.0)
