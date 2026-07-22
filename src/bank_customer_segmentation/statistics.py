"""Statistical summaries and diagnostics for customer segments."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import kruskal
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split


def cluster_distribution(assignments: pd.DataFrame) -> pd.DataFrame:
    """Return customer counts and shares by cluster."""
    if not {"cluster", "customer_id"}.issubset(assignments.columns):
        raise ValueError("Assignments require customer_id and cluster columns")
    result = (
        assignments.groupby("cluster", observed=True)
        .agg(customer_count=("customer_id", "size"))
        .reset_index()
    )
    result["customer_share"] = result["customer_count"] / result["customer_count"].sum()
    return result.sort_values("cluster").reset_index(drop=True)


def kruskal_wallis_by_cluster(
    frame: pd.DataFrame,
    features: tuple[str, ...],
    *,
    cluster_column: str = "cluster",
) -> pd.DataFrame:
    """Test whether feature distributions differ across clusters.

    Kruskal-Wallis is used because transaction and balance variables are
    strongly skewed and normality is implausible at this scale.
    """
    if cluster_column not in frame:
        raise ValueError(f"Missing cluster column: {cluster_column}")

    rows: list[dict[str, float | str | int]] = []
    grouped = list(frame.groupby(cluster_column, observed=True))
    for feature in features:
        if feature not in frame:
            continue
        samples = [
            pd.to_numeric(group[feature], errors="coerce").dropna().to_numpy()
            for _, group in grouped
        ]
        samples = [sample for sample in samples if len(sample) > 0]
        if len(samples) < 2:
            continue
        statistic, p_value = kruskal(*samples)
        rows.append(
            {
                "feature": feature,
                "cluster_count": len(samples),
                "test": "Kruskal-Wallis",
                "statistic": float(statistic),
                "p_value": float(p_value),
                "significant_at_0_05": bool(p_value < 0.05),
            }
        )
    return pd.DataFrame(rows).sort_values("p_value").reset_index(drop=True)


def standardized_effect_range(
    standardized_profile: pd.DataFrame,
) -> pd.DataFrame:
    """Rank features by their range across standardized cluster means."""
    if "cluster" not in standardized_profile:
        raise ValueError("Standardized profile must contain a cluster column")
    rows = []
    for feature in standardized_profile.columns:
        if feature == "cluster":
            continue
        values = pd.to_numeric(standardized_profile[feature], errors="coerce")
        rows.append(
            {
                "feature": feature,
                "minimum_cluster_mean": float(values.min()),
                "maximum_cluster_mean": float(values.max()),
                "standardized_range": float(values.max() - values.min()),
            }
        )
    return pd.DataFrame(rows).sort_values(
        "standardized_range", ascending=False
    ).reset_index(drop=True)


def cluster_distinguishability_importance(
    matrix: np.ndarray,
    labels: np.ndarray,
    feature_names: tuple[str, ...],
    *,
    sample_size: int = 100_000,
    random_state: int = 42,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Train an interpretable surrogate classifier to distinguish clusters."""
    if len(matrix) != len(labels):
        raise ValueError("matrix and labels must have equal length")
    if matrix.shape[1] != len(feature_names):
        raise ValueError("feature_names does not match matrix width")

    rng = np.random.default_rng(random_state)
    actual_size = min(len(matrix), sample_size)
    indices = rng.choice(len(matrix), size=actual_size, replace=False)
    x_sample = matrix[indices]
    y_sample = labels[indices]

    x_train, x_test, y_train, y_test = train_test_split(
        x_sample,
        y_sample,
        test_size=0.25,
        random_state=random_state,
        stratify=y_sample,
    )
    classifier = RandomForestClassifier(
        n_estimators=250,
        max_depth=14,
        min_samples_leaf=10,
        n_jobs=-1,
        random_state=random_state,
        class_weight="balanced_subsample",
    )
    classifier.fit(x_train, y_train)
    predictions = classifier.predict(x_test)

    importance = pd.DataFrame(
        {
            "feature": feature_names,
            "importance": classifier.feature_importances_,
        }
    ).sort_values("importance", ascending=False, ignore_index=True)

    report = classification_report(
        y_test,
        predictions,
        output_dict=True,
        zero_division=0,
    )
    diagnostics: dict[str, object] = {
        "sample_size": int(actual_size),
        "test_size": int(len(y_test)),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "classification_report": report,
        "interpretation": (
            "This supervised model is a post-hoc segment distinguishability "
            "diagnostic. It does not validate that the clusters are causal or "
            "represent naturally occurring customer types."
        ),
    }
    return importance, diagnostics
