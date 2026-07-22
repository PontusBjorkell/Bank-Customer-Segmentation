"""Statistical diagnostics page."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from utils import (
    cached_segmentation_outputs,
    configure_page,
    dataframe_download,
    sidebar_project_note,
)


configure_page("Statistical Analysis", "📐")
sidebar_project_note()

st.title("📐 Statistical Analysis")
st.caption(
    "Clustering comparison, non-parametric tests, effect ranges, and "
    "post-hoc distinguishability"
)

outputs = cached_segmentation_outputs()
summary = outputs["summary"]
comparison = outputs["model_comparison"]
tests = outputs["kruskal_tests"]
effects = outputs["effect_ranges"]

if not summary:
    st.warning("Statistical outputs are missing.")
    st.code("python scripts/run_statistical_analysis.py", language="bash")
    st.stop()

st.subheader("🏆 Final selected model")
selected = summary.get("selected_candidate_metrics", {})
cols = st.columns(5)
cols[0].metric("Algorithm", summary.get("selected_algorithm", "—"))
cols[1].metric("Clusters", summary.get("selected_cluster_count", "—"))
cols[2].metric("Silhouette", f"{selected.get('silhouette_score', np.nan):.3f}")
cols[3].metric(
    "Davies–Bouldin",
    f"{selected.get('davies_bouldin_score', np.nan):.3f}",
)
cols[4].metric(
    "Calinski–Harabasz",
    f"{selected.get('calinski_harabasz_score', np.nan):,.0f}",
)

st.caption(summary.get("selection_method", ""))

st.divider()
st.subheader("Algorithm comparison")

if not comparison.empty:
    successful = comparison.loc[
        comparison["status"].eq("success")
        & comparison["silhouette_score"].notna()
    ].copy()

    algorithm_filter = st.multiselect(
        "Algorithms",
        options=sorted(successful["algorithm"].unique()),
        default=sorted(successful["algorithm"].unique()),
    )
    successful = successful.loc[
        successful["algorithm"].isin(algorithm_filter)
    ]

    chart = px.scatter(
        successful,
        x="davies_bouldin_score",
        y="silhouette_score",
        size="sample_size",
        color="algorithm",
        hover_data=[
            "parameters",
            "cluster_count",
            "noise_share",
            "calinski_harabasz_score",
        ],
        labels={
            "davies_bouldin_score": "Davies–Bouldin score (lower is better)",
            "silhouette_score": "Silhouette score (higher is better)",
            "algorithm": "Algorithm",
        },
    )
    chart.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(chart, use_container_width=True)
    st.dataframe(
        successful.sort_values("silhouette_score", ascending=False),
        hide_index=True,
        use_container_width=True,
    )
    dataframe_download(
        comparison,
        label="Download model comparison",
        filename="clustering_model_comparison.csv",
        key="statistics-comparison-download",
    )

st.divider()
st.subheader("Kruskal–Wallis feature tests")

if not tests.empty:
    p_column = next(
        (
            column
            for column in tests.columns
            if "p" in column.lower() and "value" in column.lower()
        ),
        None,
    )
    feature_column = (
        "feature"
        if "feature" in tests.columns
        else tests.select_dtypes(exclude="number").columns[0]
    )

    tests_display = tests.copy()
    if p_column:
        raw_p = pd.to_numeric(tests_display[p_column], errors="coerce")
        clipped_p = raw_p.clip(lower=np.finfo(float).tiny)
        tests_display["negative_log10_p"] = -np.log10(clipped_p)

        test_chart = px.bar(
            tests_display.sort_values("negative_log10_p").tail(20),
            x="negative_log10_p",
            y=feature_column,
            orientation="h",
            labels={
                "negative_log10_p": "−log10(p-value)",
                feature_column: "Feature",
            },
        )
        test_chart.update_layout(margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(test_chart, use_container_width=True)

    st.dataframe(tests_display, hide_index=True, use_container_width=True)
    st.caption(
        "Values near 307 indicate p-values below floating-point precision and "
        "are capped by numerical underflow. With this sample size, practical "
        "importance should be judged primarily from effect sizes rather than "
        "statistical significance alone."
    )

st.divider()
st.subheader("Observed feature effect ranges")

if not effects.empty:
    numeric_columns = effects.select_dtypes(include="number").columns.tolist()
    effect_column = next(
        (
            column
            for column in numeric_columns
            if "standardized" in column.lower()
        ),
        next(
            (
                column
                for column in numeric_columns
                if "effect" in column.lower() or "range" in column.lower()
            ),
            numeric_columns[-1] if numeric_columns else None,
        ),
    )
    feature_column = (
        "feature"
        if "feature" in effects.columns
        else effects.select_dtypes(exclude="number").columns[0]
    )

    if effect_column:
        top_effects = (
            effects.loc[pd.to_numeric(effects[effect_column], errors="coerce") > 0]
            .sort_values(effect_column)
            .tail(12)
        )
        effect_chart = px.bar(
            top_effects,
            x=effect_column,
            y=feature_column,
            orientation="h",
            log_x=True,
            labels={
                effect_column: "Standardized effect range (log scale)",
                feature_column: "Feature",
            },
        )
        effect_chart.update_layout(margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(effect_chart, use_container_width=True)
        st.caption(
            "A logarithmic x-axis is used because active days has a much larger "
            "standardized range than the remaining features."
        )

    st.dataframe(effects, hide_index=True, use_container_width=True)

st.divider()
st.subheader("Post-hoc classifier diagnostic")

surrogate = summary.get("surrogate_classifier", {})
accuracy = surrogate.get("accuracy")
if accuracy is not None:
    st.metric("Assignment reproduction accuracy", f"{accuracy:.3f}")
st.write(surrogate.get("interpretation", ""))
st.info(
    "This classifier reproduces the clustering assignments. It is not an "
    "independent predictive model and does not provide external validation of "
    "the customer segments."
)

with st.expander("Methodological caveats", expanded=True):
    for caveat in summary.get("caveats", []):
        st.markdown(f"- {caveat}")
