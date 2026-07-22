"""Business interpretation and recommendations page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from bank_customer_segmentation.dashboard import (
    add_segment_labels,
    format_percentage,
)
from utils import (
    cached_segmentation_outputs,
    configure_page,
    render_insight,
    sidebar_project_note,
)


configure_page("Business Insights", "💡")
sidebar_project_note()

st.title("💡 Business Insights")
st.caption(
    "Translate the analytical results into transparent, operationally useful "
    "recommendations"
)

outputs = cached_segmentation_outputs()
profile = add_segment_labels(outputs["cluster_profile"])
summary = outputs["summary"]

if profile.empty:
    st.warning("Cluster profiles are unavailable.")
    st.stop()

st.subheader("Segment interpretation")

for _, row in profile.sort_values("cluster").iterrows():
    short_name = row["segment_name"]
    long_name = row["segment_description"]
    share = format_percentage(row.get("customer_share"))
    count = f"{int(row.get('customer_count', 0)):,}"
    transactions = row.get("transaction_count")
    active_days = row.get("active_days")
    confidence = row.get("average_assignment_confidence")

    with st.container(border=True):
        st.markdown(
            f"### Segment {int(row['cluster'])}: {short_name}"
        )
        st.caption(long_name)
        cols = st.columns(4)
        cols[0].metric("Customers", count)
        cols[1].metric("Portfolio share", share)
        cols[2].metric(
            "Typical transaction count",
            f"{float(transactions):.1f}" if pd.notna(transactions) else "—",
        )
        cols[3].metric(
            "Typical active days",
            f"{float(active_days):.1f}" if pd.notna(active_days) else "—",
        )
        st.caption(
            "Average assignment confidence: "
            f"{float(confidence):.3f}"
            if pd.notna(confidence)
            else "Average assignment confidence unavailable"
        )

        if int(row["cluster"]) == 0:
            st.markdown(
                """
                **Observed pattern:** predominantly customers represented by a
                single transaction and one observed active day.

                **Recommended use:**
                - Treat this group as a data-depth and early-engagement cohort.
                - Use onboarding, second-transaction, and channel-activation
                  campaigns rather than assuming these are inherently
                  low-value customers.
                - Collect longer behavioral histories before making strong
                  retention or lifetime-value decisions.
                """
            )
        elif int(row["cluster"]) == 1:
            st.markdown(
                """
                **Observed pattern:** more repeat activity, longer observed
                activity windows, and greater transaction and balance
                variability.

                **Recommended use:**
                - Prioritize this cohort for richer behavioral profiling.
                - Test personalized service, engagement, and value-development
                  strategies.
                - Monitor variability and high-value behavior for both
                  opportunity identification and responsible risk review.
                """
            )

st.divider()
st.subheader("Cross-portfolio recommendations")

render_insight(
    "Do not equate limited observation with low customer value",
    (
        "More than nine-tenths of customers fall into the limited-history "
        "segment. The dataset may contain only a narrow observation window, so "
        "the bank should avoid treating missing longitudinal behavior as proof "
        "of low engagement or low lifetime value."
    ),
)
render_insight(
    "Use segmentation as a prioritization layer",
    (
        "The repeat-activity segment is the best starting point for deeper "
        "sub-segmentation, propensity modeling, and campaign testing because "
        "its customers have enough recorded behavior to support richer features."
    ),
)
render_insight(
    "Validate stability before operational deployment",
    (
        "Recalculate segments across later time windows and compare migration, "
        "size, feature profiles, and business outcomes before embedding them in "
        "customer treatment rules."
    ),
)
render_insight(
    "Connect clusters to measurable outcomes",
    (
        "Future work should test whether the segments predict retention, product "
        "adoption, transaction growth, service needs, or profitability. Internal "
        "clustering metrics alone do not establish business value."
    ),
)

st.divider()
st.subheader("Suggested measurement framework")

framework = pd.DataFrame(
    [
        {
            "objective": "Second-transaction activation",
            "target_cohort": "Limited History",
            "primary_kpi": "Share completing another transaction",
            "design": "Randomized onboarding or reminder experiment",
        },
        {
            "objective": "Engagement development",
            "target_cohort": "Repeat Activity",
            "primary_kpi": "Transaction frequency and value growth",
            "design": "Controlled personalized offer test",
        },
        {
            "objective": "Segment validation",
            "target_cohort": "All customers",
            "primary_kpi": "Profile and assignment stability over time",
            "design": "Monthly or quarterly cohort tracking",
        },
        {
            "objective": "Commercial validation",
            "target_cohort": "All customers",
            "primary_kpi": "Retention, adoption, and profitability differences",
            "design": "Outcome linkage and holdout evaluation",
        },
    ]
)

st.dataframe(framework, hide_index=True, use_container_width=True)

with st.expander("Interpretation caveats", expanded=True):
    for caveat in summary.get("caveats", []):
        st.markdown(f"- {caveat}")
