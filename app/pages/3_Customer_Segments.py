"""Customer segment exploration page."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from bank_customer_segmentation.dashboard import (
    add_segment_labels,
    format_percentage,
    sample_frame,
)
from utils import (
    cached_segmentation_outputs,
    configure_page,
    dataframe_download,
    render_insight,
    sidebar_project_note,
)


configure_page("Customer Segments", "👥")
sidebar_project_note()

st.title("👥 Customer Segments")
st.caption(
    "MiniBatch K-Means profiles, model-selection metrics, PCA projection, "
    "and assignment diagnostics"
)

outputs = cached_segmentation_outputs()
summary = outputs["summary"]
profile = add_segment_labels(outputs["cluster_profile"])
standardized_profile = add_segment_labels(outputs["standardized_profile"])
comparison = outputs["model_comparison"]
pca = outputs["pca_projection"]
importance = outputs["feature_importance"]

if not summary or profile.empty:
    st.warning("Segmentation outputs are unavailable.")
    st.code(
        "python scripts/run_statistical_analysis.py --skip-extended-comparison",
        language="bash",
    )
    st.stop()

metrics = summary.get("selected_candidate_metrics", {})
metric_cols = st.columns(5)
metric_cols[0].metric(
    "Customers segmented",
    f"{summary.get('customer_count', 0):,}",
)
metric_cols[1].metric(
    "Selected clusters",
    summary.get("selected_cluster_count", "—"),
)
metric_cols[2].metric(
    "Silhouette",
    f"{metrics.get('silhouette_score', float('nan')):.3f}",
)
metric_cols[3].metric(
    "Davies–Bouldin",
    f"{metrics.get('davies_bouldin_score', float('nan')):.3f}",
)
metric_cols[4].metric(
    "PCA variance in PC1",
    format_percentage(summary.get("pca_explained_variance_ratio", [np.nan])[0]),
)

st.info(
    "Segment names are deliberately short for readability. They describe "
    "observed activity in this dataset and are not permanent or causal "
    "customer identities."
)

st.divider()
left, right = st.columns([0.9, 1.1])

with left:
    st.subheader("Segment distribution")
    distribution = profile[
        ["cluster", "segment_name", "customer_count", "customer_share"]
    ].copy()
    distribution_chart = px.bar(
        distribution,
        x="segment_name",
        y="customer_count",
        text="customer_count",
        hover_data={"customer_share": ":.1%"},
        labels={
            "segment_name": "Segment",
            "customer_count": "Customers",
        },
    )
    distribution_chart.update_traces(texttemplate="%{text:,}", textposition="inside")
    distribution_chart.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(distribution_chart, use_container_width=True)

with right:
    st.subheader("Standardized segment profile")
    st.caption(
        "Features are shown on a standardized scale so variables with different "
        "units can be compared meaningfully."
    )

    profile_source = (
        standardized_profile
        if not standardized_profile.empty
        else profile
    )
    numeric_candidates = [
        column
        for column in profile_source.select_dtypes(include="number").columns
        if column not in {
            "cluster",
            "customer_count",
            "customer_share",
            "average_assignment_confidence",
        }
    ]
    defaults = [
        column
        for column in [
            "transaction_count",
            "active_days",
            "log_total_transaction_amount",
            "log_average_account_balance",
        ]
        if column in numeric_candidates
    ]

    selected_measures = st.multiselect(
        "Measures",
        options=numeric_candidates,
        default=defaults,
    )

    if selected_measures:
        profile_long = profile_source.melt(
            id_vars=["cluster", "segment_name"],
            value_vars=selected_measures,
            var_name="feature",
            value_name="value",
        )
        profile_chart = px.bar(
            profile_long,
            x="feature",
            y="value",
            color="segment_name",
            barmode="group",
            labels={
                "feature": "Feature",
                "value": "Standardized profile value",
                "segment_name": "Segment",
            },
        )
        profile_chart.update_layout(
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis_tickangle=-25,
        )
        st.plotly_chart(profile_chart, use_container_width=True)

display_profile = profile.copy()
if "customer_share" in display_profile.columns:
    display_profile["customer_share_pct"] = (
        display_profile["customer_share"] * 100
    )

display_columns = [
    column
    for column in [
        "cluster",
        "segment_name",
        "segment_description",
        "customer_count",
        "customer_share_pct",
        "transaction_count",
        "active_days",
        "average_assignment_confidence",
    ]
    if column in display_profile.columns
]

st.dataframe(
    display_profile[display_columns],
    hide_index=True,
    use_container_width=True,
    column_config={
        "customer_share_pct": st.column_config.NumberColumn(
            "Customer share",
            format="%.1f%%",
        ),
        "average_assignment_confidence": st.column_config.ProgressColumn(
            "Average assignment confidence",
            min_value=0.0,
            max_value=1.0,
            format="%.3f",
        ),
    },
)
dataframe_download(
    profile,
    label="Download cluster profile",
    filename="cluster_profile.csv",
    key="segments-profile-download",
)

st.divider()
st.subheader("Model selection")

kmeans = comparison.loc[
    comparison["algorithm"].eq("MiniBatchKMeans")
    & comparison["status"].eq("success")
].copy()
if not kmeans.empty:
    kmeans["cluster_count"] = pd.to_numeric(
        kmeans["cluster_count"],
        errors="coerce",
    )
    selection_chart = px.line(
        kmeans,
        x="cluster_count",
        y="silhouette_score",
        markers=True,
        labels={
            "cluster_count": "Number of clusters",
            "silhouette_score": "Silhouette score",
        },
    )
    selected_k = summary.get("selected_cluster_count")
    if selected_k is not None:
        selected_row = kmeans.loc[kmeans["cluster_count"].eq(selected_k)]
        if not selected_row.empty:
            selection_chart.add_scatter(
                x=selected_row["cluster_count"],
                y=selected_row["silhouette_score"],
                mode="markers+text",
                text=["Selected"],
                textposition="top center",
                marker={"size": 15, "symbol": "star"},
                name="Selected model",
            )
    selection_chart.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(selection_chart, use_container_width=True)

st.divider()
st.subheader("PCA projection")

if not pca.empty:
    pca = add_segment_labels(pca)
    if "cluster" not in pca.columns:
        st.info("The PCA file does not contain cluster labels.")
    else:
        sample_size = st.slider(
            "Points displayed",
            min_value=1000,
            max_value=min(50000, len(pca)),
            value=min(15000, len(pca)),
            step=1000,
        )
        plotted = sample_frame(pca, sample_size)

        x_column = "pca_component_1"
        y_column = "pca_component_2"
        if x_column not in plotted.columns or y_column not in plotted.columns:
            candidate_columns = [
                column
                for column in plotted.select_dtypes(include="number").columns
                if column != "cluster"
            ]
            if len(candidate_columns) >= 2:
                x_column, y_column = candidate_columns[:2]

        pca_chart = px.scatter(
            plotted,
            x=x_column,
            y=y_column,
            color="segment_name",
            opacity=0.45,
            render_mode="webgl",
            labels={
                x_column: "PCA component 1",
                y_column: "PCA component 2",
                "segment_name": "Segment",
            },
        )
        pca_chart.update_traces(marker={"size": 4})
        pca_chart.update_layout(margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(pca_chart, use_container_width=True)

st.divider()
st.subheader("Features distinguishing the assigned segments")

if not importance.empty:
    importance_column = (
        "importance"
        if "importance" in importance.columns
        else importance.select_dtypes(include="number").columns[-1]
    )
    feature_column = (
        "feature"
        if "feature" in importance.columns
        else importance.select_dtypes(exclude="number").columns[0]
    )
    top_importance = importance.sort_values(
        importance_column,
        ascending=True,
    ).tail(15)
    importance_chart = px.bar(
        top_importance,
        x=importance_column,
        y=feature_column,
        orientation="h",
        labels={
            importance_column: "Random forest importance",
            feature_column: "Feature",
        },
    )
    importance_chart.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(importance_chart, use_container_width=True)

render_insight(
    "Dominant distinction",
    (
        "The solution is driven primarily by observed activity duration, "
        "transaction count, and within-customer variability."
    ),
)
render_insight(
    "Interpretation boundary",
    (
        "A high silhouette score shows geometric separation, but it does not "
        "establish causal customer types or prove that two segments are the "
        "best commercial operating model."
    ),
)
