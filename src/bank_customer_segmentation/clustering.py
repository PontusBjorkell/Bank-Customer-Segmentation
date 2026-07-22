"""Scalable customer-segmentation utilities.

The dataset contains hundreds of thousands of customer profiles. Algorithms
with quadratic memory or runtime are therefore evaluated on reproducible
samples, while the final production model uses MiniBatchKMeans on the complete
customer feature table.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, DBSCAN, MiniBatchKMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

DEFAULT_SEGMENTATION_FEATURES: tuple[str, ...] = (
    "customer_age",
    "log_total_transaction_amount",
    "log_average_transaction_amount",
    "log_average_account_balance",
    "transaction_count",
    "transaction_amount_cv",
    "account_balance_cv",
    "active_days",
    "average_transaction_hour",
    "weekend_transaction_share",
    "night_transaction_share",
    "morning_transaction_share",
    "afternoon_transaction_share",
    "evening_transaction_share",
    "late_evening_transaction_share",
)


@dataclass(frozen=True)
class PreparedSegmentationData:
    """Prepared feature matrix and fitted preprocessing objects."""

    customer_ids: pd.Series
    raw_features: pd.DataFrame
    matrix: np.ndarray
    preprocessor: Pipeline
    feature_names: tuple[str, ...]
    clipping_bounds: dict[str, tuple[float, float]]


@dataclass(frozen=True)
class CandidateResult:
    """Evaluation metrics for one clustering candidate."""

    algorithm: str
    parameters: str
    sample_size: int
    cluster_count: int
    noise_share: float
    silhouette_score: float | None
    davies_bouldin_score: float | None
    calinski_harabasz_score: float | None
    status: str
    error: str | None = None


def load_customer_features(path: Path) -> pd.DataFrame:
    """Load the customer-level feature mart and validate its identifier."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Customer feature file not found: {path}")

    frame = pd.read_csv(path, low_memory=False)
    if "customer_id" not in frame.columns:
        raise ValueError("Customer feature file must contain 'customer_id'")
    if frame["customer_id"].isna().any():
        raise ValueError("customer_id contains missing values")
    if frame["customer_id"].duplicated().any():
        raise ValueError("customer_id must be unique in the feature mart")
    return frame


def _validate_feature_columns(frame: pd.DataFrame, features: tuple[str, ...]) -> None:
    missing = sorted(set(features) - set(frame.columns))
    if missing:
        raise ValueError(f"Missing segmentation features: {missing}")


def _calculate_clipping_bounds(
    frame: pd.DataFrame,
    features: tuple[str, ...],
    lower_quantile: float,
    upper_quantile: float,
) -> dict[str, tuple[float, float]]:
    bounds: dict[str, tuple[float, float]] = {}
    for feature in features:
        values = pd.to_numeric(frame[feature], errors="coerce")
        lower = float(values.quantile(lower_quantile))
        upper = float(values.quantile(upper_quantile))
        if not np.isfinite(lower):
            lower = 0.0
        if not np.isfinite(upper):
            upper = lower
        if upper < lower:
            lower, upper = upper, lower
        bounds[feature] = (lower, upper)
    return bounds


def apply_clipping_bounds(
    frame: pd.DataFrame,
    bounds: dict[str, tuple[float, float]],
) -> pd.DataFrame:
    """Coerce numeric features and winsorize them using fitted bounds."""
    clipped = pd.DataFrame(index=frame.index)
    for feature, (lower, upper) in bounds.items():
        clipped[feature] = pd.to_numeric(frame[feature], errors="coerce").clip(
            lower=lower,
            upper=upper,
        )
    return clipped


def prepare_segmentation_data(
    frame: pd.DataFrame,
    *,
    features: tuple[str, ...] = DEFAULT_SEGMENTATION_FEATURES,
    lower_quantile: float = 0.005,
    upper_quantile: float = 0.995,
) -> PreparedSegmentationData:
    """Winsorize, impute, and robustly scale segmentation features."""
    if not 0 <= lower_quantile < upper_quantile <= 1:
        raise ValueError("Clipping quantiles must satisfy 0 <= lower < upper <= 1")

    _validate_feature_columns(frame, features)
    bounds = _calculate_clipping_bounds(
        frame,
        features,
        lower_quantile,
        upper_quantile,
    )
    raw_features = apply_clipping_bounds(frame, bounds)

    preprocessor = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", RobustScaler()),
        ]
    )
    matrix = preprocessor.fit_transform(raw_features)
    matrix = np.asarray(matrix, dtype=np.float64)

    if not np.isfinite(matrix).all():
        raise ValueError("Prepared segmentation matrix contains non-finite values")

    return PreparedSegmentationData(
        customer_ids=frame["customer_id"].reset_index(drop=True),
        raw_features=raw_features.reset_index(drop=True),
        matrix=matrix,
        preprocessor=preprocessor,
        feature_names=features,
        clipping_bounds=bounds,
    )


def reproducible_sample_indices(
    row_count: int,
    sample_size: int,
    random_state: int,
) -> np.ndarray:
    """Return sorted random indices without replacement."""
    if row_count <= 0:
        raise ValueError("row_count must be positive")
    actual_size = min(row_count, max(2, sample_size))
    rng = np.random.default_rng(random_state)
    return np.sort(rng.choice(row_count, size=actual_size, replace=False))


def _safe_metrics(matrix: np.ndarray, labels: np.ndarray) -> dict[str, float | None]:
    labels = np.asarray(labels)
    non_noise = labels != -1
    evaluated_matrix = matrix[non_noise]
    evaluated_labels = labels[non_noise]
    unique_labels = np.unique(evaluated_labels)

    if len(unique_labels) < 2 or len(evaluated_labels) <= len(unique_labels):
        return {
            "silhouette_score": None,
            "davies_bouldin_score": None,
            "calinski_harabasz_score": None,
        }

    silhouette_sample = min(10_000, len(evaluated_labels))
    return {
        "silhouette_score": float(
            silhouette_score(
                evaluated_matrix,
                evaluated_labels,
                sample_size=silhouette_sample,
                random_state=42,
            )
        ),
        "davies_bouldin_score": float(
            davies_bouldin_score(evaluated_matrix, evaluated_labels)
        ),
        "calinski_harabasz_score": float(
            calinski_harabasz_score(evaluated_matrix, evaluated_labels)
        ),
    }


def _candidate_result(
    algorithm: str,
    parameters: str,
    matrix: np.ndarray,
    labels: np.ndarray,
) -> CandidateResult:
    unique_non_noise = np.unique(labels[labels != -1])
    metrics = _safe_metrics(matrix, labels)
    return CandidateResult(
        algorithm=algorithm,
        parameters=parameters,
        sample_size=len(matrix),
        cluster_count=len(unique_non_noise),
        noise_share=float(np.mean(labels == -1)),
        silhouette_score=metrics["silhouette_score"],
        davies_bouldin_score=metrics["davies_bouldin_score"],
        calinski_harabasz_score=metrics["calinski_harabasz_score"],
        status="success",
    )


def compare_kmeans_candidates(
    matrix: np.ndarray,
    *,
    cluster_range: range = range(2, 9),
    sample_size: int = 50_000,
    random_state: int = 42,
) -> list[CandidateResult]:
    """Compare MiniBatchKMeans candidates on a reproducible sample."""
    indices = reproducible_sample_indices(len(matrix), sample_size, random_state)
    sample = matrix[indices]
    results: list[CandidateResult] = []

    for clusters in cluster_range:
        model = MiniBatchKMeans(
            n_clusters=clusters,
            random_state=random_state,
            batch_size=4096,
            n_init=10,
            max_iter=300,
            reassignment_ratio=0.01,
        )
        labels = model.fit_predict(sample)
        results.append(
            _candidate_result(
                "MiniBatchKMeans",
                f"n_clusters={clusters}",
                sample,
                labels,
            )
        )
    return results


def compare_extended_candidates(
    matrix: np.ndarray,
    *,
    random_state: int = 42,
    gmm_sample_size: int = 30_000,
    hierarchical_sample_size: int = 5_000,
    dbscan_sample_size: int = 15_000,
) -> list[CandidateResult]:
    """Evaluate heavier algorithms on bounded samples.

    These results are diagnostic comparisons, not direct full-population model
    benchmarks, because each algorithm has different scalability constraints.
    """
    results: list[CandidateResult] = []

    gmm_indices = reproducible_sample_indices(
        len(matrix), gmm_sample_size, random_state
    )
    gmm_sample = matrix[gmm_indices]
    for clusters in range(2, 7):
        try:
            model = GaussianMixture(
                n_components=clusters,
                covariance_type="diag",
                random_state=random_state,
                n_init=2,
                max_iter=200,
                reg_covar=1e-6,
            )
            labels = model.fit_predict(gmm_sample)
            results.append(
                _candidate_result(
                    "GaussianMixture",
                    f"n_components={clusters};covariance_type=diag",
                    gmm_sample,
                    labels,
                )
            )
        except Exception as exc:  # noqa: BLE001 - recorded for reporting
            results.append(
                CandidateResult(
                    algorithm="GaussianMixture",
                    parameters=f"n_components={clusters};covariance_type=diag",
                    sample_size=len(gmm_sample),
                    cluster_count=0,
                    noise_share=0.0,
                    silhouette_score=None,
                    davies_bouldin_score=None,
                    calinski_harabasz_score=None,
                    status="failed",
                    error=str(exc),
                )
            )

    hierarchical_indices = reproducible_sample_indices(
        len(matrix), hierarchical_sample_size, random_state + 1
    )
    hierarchical_sample = matrix[hierarchical_indices]
    for clusters in range(2, 7):
        model = AgglomerativeClustering(n_clusters=clusters, linkage="ward")
        labels = model.fit_predict(hierarchical_sample)
        results.append(
            _candidate_result(
                "AgglomerativeClustering",
                f"n_clusters={clusters};linkage=ward",
                hierarchical_sample,
                labels,
            )
        )

    dbscan_indices = reproducible_sample_indices(
        len(matrix), dbscan_sample_size, random_state + 2
    )
    dbscan_sample = matrix[dbscan_indices]
    for eps in (0.5, 0.8, 1.1, 1.4):
        model = DBSCAN(eps=eps, min_samples=25, n_jobs=-1)
        labels = model.fit_predict(dbscan_sample)
        results.append(
            _candidate_result(
                "DBSCAN",
                f"eps={eps};min_samples=25",
                dbscan_sample,
                labels,
            )
        )

    return results


def candidate_results_frame(results: list[CandidateResult]) -> pd.DataFrame:
    """Convert candidate metrics to a consistently ordered DataFrame."""
    return pd.DataFrame([result.__dict__ for result in results])


def choose_kmeans_cluster_count(results: pd.DataFrame) -> int:
    """Choose K using rank aggregation across three internal metrics."""
    required = {
        "algorithm",
        "parameters",
        "silhouette_score",
        "davies_bouldin_score",
        "calinski_harabasz_score",
        "status",
    }
    missing = sorted(required - set(results.columns))
    if missing:
        raise ValueError(f"Candidate results are missing columns: {missing}")

    candidates = results.loc[
        (results["algorithm"] == "MiniBatchKMeans")
        & (results["status"] == "success")
    ].dropna(
        subset=[
            "silhouette_score",
            "davies_bouldin_score",
            "calinski_harabasz_score",
        ]
    )
    if candidates.empty:
        raise ValueError("No successful MiniBatchKMeans candidates are available")

    ranked = candidates.copy()
    ranked["silhouette_rank"] = ranked["silhouette_score"].rank(
        ascending=False, method="min"
    )
    ranked["davies_bouldin_rank"] = ranked["davies_bouldin_score"].rank(
        ascending=True, method="min"
    )
    ranked["calinski_harabasz_rank"] = ranked["calinski_harabasz_score"].rank(
        ascending=False, method="min"
    )
    ranked["combined_rank"] = ranked[
        ["silhouette_rank", "davies_bouldin_rank", "calinski_harabasz_rank"]
    ].mean(axis=1)
    best = ranked.sort_values(
        ["combined_rank", "silhouette_score"],
        ascending=[True, False],
    ).iloc[0]
    return int(str(best["parameters"]).split("=")[-1])


def fit_final_kmeans(
    matrix: np.ndarray,
    n_clusters: int,
    *,
    random_state: int = 42,
) -> tuple[MiniBatchKMeans, np.ndarray]:
    """Fit the scalable final model on every customer profile."""
    model = MiniBatchKMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        batch_size=8192,
        n_init=20,
        max_iter=500,
        reassignment_ratio=0.01,
    )
    labels = model.fit_predict(matrix)
    return model, labels


def build_cluster_assignments(
    customer_ids: pd.Series,
    labels: np.ndarray,
    matrix: np.ndarray,
    model: MiniBatchKMeans,
) -> pd.DataFrame:
    """Create one assignment row per customer with distance-based confidence."""
    distances = model.transform(matrix)
    nearest = np.min(distances, axis=1)
    if distances.shape[1] > 1:
        second_nearest = np.partition(distances, kth=1, axis=1)[:, 1]
        confidence = 1.0 - np.divide(
            nearest,
            second_nearest,
            out=np.zeros_like(nearest),
            where=second_nearest > 0,
        )
    else:
        confidence = np.ones(len(nearest))

    return pd.DataFrame(
        {
            "customer_id": customer_ids.astype(str).to_numpy(),
            "cluster": labels.astype(int),
            "distance_to_centroid": nearest,
            "assignment_confidence": np.clip(confidence, 0.0, 1.0),
        }
    )


def build_cluster_profile(
    customer_features: pd.DataFrame,
    assignments: pd.DataFrame,
    *,
    profile_features: tuple[str, ...] = DEFAULT_SEGMENTATION_FEATURES,
) -> pd.DataFrame:
    """Summarize size and median feature values for each cluster."""
    merged = customer_features.merge(
        assignments[["customer_id", "cluster", "assignment_confidence"]],
        on="customer_id",
        how="inner",
        validate="one_to_one",
    )
    numeric_features = [feature for feature in profile_features if feature in merged]

    profile = merged.groupby("cluster", observed=True).agg(
        customer_count=("customer_id", "size"),
        average_assignment_confidence=("assignment_confidence", "mean"),
    )
    medians = merged.groupby("cluster", observed=True)[numeric_features].median()
    profile = profile.join(medians).reset_index()
    profile["customer_share"] = profile["customer_count"] / len(merged)
    return profile.sort_values("cluster").reset_index(drop=True)


def build_standardized_cluster_profile(
    matrix: np.ndarray,
    labels: np.ndarray,
    feature_names: tuple[str, ...],
) -> pd.DataFrame:
    """Return cluster means in preprocessing-scaled feature space."""
    frame = pd.DataFrame(matrix, columns=feature_names)
    frame["cluster"] = labels
    return frame.groupby("cluster", observed=True).mean().reset_index()


def build_pca_projection(
    matrix: np.ndarray,
    customer_ids: pd.Series,
    labels: np.ndarray,
    *,
    sample_size: int = 50_000,
    random_state: int = 42,
) -> tuple[PCA, pd.DataFrame]:
    """Fit two-component PCA and return a dashboard-friendly sample."""
    pca = PCA(n_components=2, random_state=random_state)
    coordinates = pca.fit_transform(matrix)
    indices = reproducible_sample_indices(len(matrix), sample_size, random_state)
    projection = pd.DataFrame(
        {
            "customer_id": customer_ids.iloc[indices].astype(str).to_numpy(),
            "cluster": labels[indices].astype(int),
            "pca_1": coordinates[indices, 0],
            "pca_2": coordinates[indices, 1],
        }
    )
    return pca, projection


def save_segmentation_bundle(
    path: Path,
    *,
    preprocessor: Pipeline,
    model: MiniBatchKMeans,
    pca: PCA,
    feature_names: tuple[str, ...],
    clipping_bounds: dict[str, tuple[float, float]],
    metadata: dict[str, Any],
) -> None:
    """Persist all objects required to reproduce customer assignments."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "preprocessor": preprocessor,
            "model": model,
            "pca": pca,
            "feature_names": feature_names,
            "clipping_bounds": clipping_bounds,
            "metadata": metadata,
        },
        path,
    )
