"""Run scalable clustering, diagnostics, profiling, and statistical reports."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from bank_customer_segmentation.clustering import (
    DEFAULT_SEGMENTATION_FEATURES,
    build_cluster_assignments,
    build_cluster_profile,
    build_pca_projection,
    build_standardized_cluster_profile,
    candidate_results_frame,
    choose_kmeans_cluster_count,
    compare_extended_candidates,
    compare_kmeans_candidates,
    fit_final_kmeans,
    load_customer_features,
    prepare_segmentation_data,
    save_segmentation_bundle,
)
from bank_customer_segmentation.config import get_project_paths
from bank_customer_segmentation.statistics import (
    cluster_distinguishability_importance,
    cluster_distribution,
    kruskal_wallis_by_cluster,
    standardized_effect_range,
)
from bank_customer_segmentation.utils import configure_logging

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--figures-dir", type=Path, default=None)
    parser.add_argument("--model-path", type=Path, default=None)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--kmeans-sample-size", type=int, default=50_000)
    parser.add_argument("--pca-sample-size", type=int, default=50_000)
    parser.add_argument("--importance-sample-size", type=int, default=100_000)
    parser.add_argument(
        "--skip-extended-comparison",
        action="store_true",
        help="Skip GMM, hierarchical, and DBSCAN sample diagnostics.",
    )
    parser.add_argument(
        "--n-clusters",
        type=int,
        default=None,
        help="Override automatic K selection for the final MiniBatchKMeans model.",
    )
    return parser.parse_args()


def _save_figures(
    comparison: pd.DataFrame,
    distribution: pd.DataFrame,
    projection: pd.DataFrame,
    importance: pd.DataFrame,
    figures_dir: Path,
) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)

    kmeans = comparison.loc[
        (comparison["algorithm"] == "MiniBatchKMeans")
        & (comparison["status"] == "success")
    ].copy()
    kmeans["cluster_count_candidate"] = kmeans["parameters"].str.extract(
        r"(\d+)$"
    ).astype(int)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(kmeans["cluster_count_candidate"], kmeans["silhouette_score"], marker="o")
    ax.set_xlabel("Number of clusters")
    ax.set_ylabel("Silhouette score")
    ax.set_title("MiniBatch K-Means model selection")
    fig.tight_layout()
    fig.savefig(figures_dir / "kmeans_silhouette_selection.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(distribution["cluster"].astype(str), distribution["customer_count"])
    ax.set_xlabel("Cluster")
    ax.set_ylabel("Customers")
    ax.set_title("Customer distribution across final segments")
    fig.tight_layout()
    fig.savefig(figures_dir / "cluster_distribution.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 7))
    scatter = ax.scatter(
        projection["pca_1"],
        projection["pca_2"],
        c=projection["cluster"],
        s=5,
        alpha=0.45,
    )
    ax.set_xlabel("PCA component 1")
    ax.set_ylabel("PCA component 2")
    ax.set_title("PCA projection of customer segments")
    fig.colorbar(scatter, ax=ax, label="Cluster")
    fig.tight_layout()
    fig.savefig(figures_dir / "customer_segments_pca.png", dpi=160)
    plt.close(fig)

    top = importance.head(12).sort_values("importance")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(top["feature"], top["importance"])
    ax.set_xlabel("Random forest importance")
    ax.set_title("Features that best distinguish assigned segments")
    fig.tight_layout()
    fig.savefig(figures_dir / "cluster_feature_importance.png", dpi=160)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    configure_logging()
    paths = get_project_paths()
    paths.ensure_output_directories()

    input_path = args.input or paths.customer_features
    output_dir = args.output_dir or paths.reports_statistical
    figures_dir = args.figures_dir or paths.reports_figures
    model_path = args.model_path or (paths.data_exports / "segmentation_bundle.joblib")
    assignments_path = paths.data_exports / "customer_segment_assignments.csv"
    output_dir.mkdir(parents=True, exist_ok=True)
    assignments_path.parent.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Loading customer feature mart from %s", input_path)
    customer_features = load_customer_features(input_path)
    LOGGER.info("Loaded %s customer profiles", f"{len(customer_features):,}")

    LOGGER.info("Preparing winsorized, imputed, and robust-scaled feature matrix")
    prepared = prepare_segmentation_data(customer_features)

    LOGGER.info("Comparing MiniBatch K-Means candidates")
    candidates = compare_kmeans_candidates(
        prepared.matrix,
        sample_size=args.kmeans_sample_size,
        random_state=args.random_state,
    )
    if not args.skip_extended_comparison:
        LOGGER.info("Running bounded-sample GMM, hierarchical, and DBSCAN diagnostics")
        candidates.extend(
            compare_extended_candidates(
                prepared.matrix,
                random_state=args.random_state,
            )
        )

    comparison = candidate_results_frame(candidates)
    comparison.to_csv(output_dir / "clustering_model_comparison.csv", index=False)

    n_clusters = args.n_clusters or choose_kmeans_cluster_count(comparison)
    LOGGER.info("Fitting final MiniBatch K-Means model with %d clusters", n_clusters)
    model, labels = fit_final_kmeans(
        prepared.matrix,
        n_clusters=n_clusters,
        random_state=args.random_state,
    )

    assignments = build_cluster_assignments(
        prepared.customer_ids,
        labels,
        prepared.matrix,
        model,
    )
    assignments.to_csv(assignments_path, index=False)

    profile = build_cluster_profile(customer_features, assignments)
    profile.to_csv(output_dir / "cluster_profile.csv", index=False)

    standardized_profile = build_standardized_cluster_profile(
        prepared.matrix,
        labels,
        prepared.feature_names,
    )
    standardized_profile.to_csv(
        output_dir / "cluster_standardized_profile.csv",
        index=False,
    )

    distribution = cluster_distribution(assignments)
    distribution.to_csv(output_dir / "cluster_distribution.csv", index=False)

    merged = customer_features.merge(
        assignments[["customer_id", "cluster"]],
        on="customer_id",
        validate="one_to_one",
    )
    tests = kruskal_wallis_by_cluster(merged, DEFAULT_SEGMENTATION_FEATURES)
    tests.to_csv(output_dir / "cluster_kruskal_wallis_tests.csv", index=False)

    effect_ranges = standardized_effect_range(standardized_profile)
    effect_ranges.to_csv(output_dir / "cluster_effect_ranges.csv", index=False)

    importance, importance_diagnostics = cluster_distinguishability_importance(
        prepared.matrix,
        labels,
        prepared.feature_names,
        sample_size=args.importance_sample_size,
        random_state=args.random_state,
    )
    importance.to_csv(output_dir / "cluster_feature_importance.csv", index=False)

    pca, projection = build_pca_projection(
        prepared.matrix,
        prepared.customer_ids,
        labels,
        sample_size=args.pca_sample_size,
        random_state=args.random_state,
    )
    projection.to_csv(output_dir / "pca_customer_projection.csv", index=False)

    successful_kmeans = comparison.loc[
        (comparison["algorithm"] == "MiniBatchKMeans")
        & (comparison["status"] == "success")
    ].copy()
    selected_row = successful_kmeans.loc[
        successful_kmeans["parameters"] == f"n_clusters={n_clusters}"
    ].iloc[0]

    summary = {
        "customer_count": int(len(customer_features)),
        "feature_count": int(len(prepared.feature_names)),
        "features": list(prepared.feature_names),
        "selected_algorithm": "MiniBatchKMeans",
        "selected_cluster_count": int(n_clusters),
        "selection_method": "Mean rank across silhouette, Davies-Bouldin, and Calinski-Harabasz metrics",
        "selected_candidate_metrics": {
            "silhouette_score": float(selected_row["silhouette_score"]),
            "davies_bouldin_score": float(selected_row["davies_bouldin_score"]),
            "calinski_harabasz_score": float(selected_row["calinski_harabasz_score"]),
        },
        "pca_explained_variance_ratio": [
            float(value) for value in pca.explained_variance_ratio_
        ],
        "surrogate_classifier": importance_diagnostics,
        "caveats": [
            "Most customers have only one observed transaction, so behavioral frequency features are limited.",
            "Internal clustering metrics assess geometric separation, not causal or commercial validity.",
            "GMM, hierarchical clustering, and DBSCAN are evaluated on bounded samples for computational feasibility.",
        ],
    }
    (output_dir / "segmentation_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    save_segmentation_bundle(
        model_path,
        preprocessor=prepared.preprocessor,
        model=model,
        pca=pca,
        feature_names=prepared.feature_names,
        clipping_bounds=prepared.clipping_bounds,
        metadata=summary,
    )

    _save_figures(comparison, distribution, projection, importance, figures_dir)

    LOGGER.info("Segmentation complete")
    LOGGER.info("Assignments: %s", assignments_path)
    LOGGER.info("Reports: %s", output_dir)
    LOGGER.info("Figures: %s", figures_dir)
    LOGGER.info("Model bundle: %s", model_path)


if __name__ == "__main__":
    main()
