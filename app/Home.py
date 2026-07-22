"""Home page for the Bank Customer Segmentation dashboard."""

from __future__ import annotations

import streamlit as st

from bank_customer_segmentation.dashboard import (
    format_compact_currency,
    format_currency,
    format_integer,
    required_artifact_status,
)
from utils import (
    PATHS,
    cached_query,
    configure_page,
    render_insight,
    sidebar_project_note,
)


configure_page("Home", "🏦")
sidebar_project_note()

st.title("🏦 Bank Customer Segmentation")
st.subheader("End-to-end customer analytics, SQL reporting, and segmentation")

st.markdown(
    """
    This application presents a production-inspired analytics workflow built
    from more than one million bank transactions. The project includes data
    preparation, validation, a normalized SQLite warehouse, 32 analytical SQL
    reports, scalable clustering, statistical diagnostics, and downloadable
    outputs.
    """
)

overview = cached_query(
    """
    SELECT
        COUNT(*) AS transactions,
        COUNT(DISTINCT customer_id) AS customers,
        SUM(transaction_amount_inr) AS total_value,
        AVG(transaction_amount_inr) AS average_transaction,
        AVG(account_balance_inr) AS average_balance
    FROM fact_transaction
    """
)

if not overview.empty:
    row = overview.iloc[0]
    top = st.columns(2)
    top[0].metric("Transactions", format_integer(row["transactions"]))
    top[1].metric("Customers", format_integer(row["customers"]))

    bottom = st.columns(3)
    bottom[0].metric(
        "Total observed value",
        format_compact_currency(row["total_value"]),
        help=format_currency(row["total_value"], decimals=2),
    )
    bottom[1].metric(
        "Average transaction",
        format_currency(row["average_transaction"]),
    )
    bottom[2].metric(
        "Average account balance",
        format_currency(row["average_balance"]),
    )
else:
    st.warning(
        "The SQLite warehouse is not available yet. Build it before using the "
        "full dashboard."
    )
    st.code("python scripts/build_database.py", language="bash")

st.divider()
left, right = st.columns([1.15, 0.85])

with left:
    st.markdown("### Project workflow")
    st.markdown(
        """
        1. **Data preparation** — clean, validate, and enrich transaction data.
        2. **SQLite warehouse** — populate dimensions, facts, feature mart,
           indexes, and analytical views.
        3. **SQL analytics** — execute and export a catalogue of 32 reports.
        4. **Statistical analysis** — compare clustering approaches, select a
           scalable model, profile segments, and quantify feature differences.
        5. **Interactive delivery** — provide stakeholder-oriented exploration,
           filters, charts, tables, and downloads.
        """
    )

with right:
    st.markdown("### Artifact readiness")
    status = required_artifact_status(PATHS)
    status["status"] = status["available"].map(
        {True: "Available", False: "Missing"}
    )
    st.dataframe(
        status[["artifact", "status"]],
        hide_index=True,
        use_container_width=True,
    )

st.divider()
st.markdown("### Key analytical interpretation")

render_insight(
    "A statistically clear two-group structure",
    (
        "The selected MiniBatch K-Means solution separates customers into two "
        "geometrically distinct groups according to internal clustering metrics."
    ),
)
render_insight(
    "Observed activity drives the split",
    (
        "Active days, transaction count, and transaction variability are the "
        "strongest distinguishing variables. Because most customers have one "
        "recorded transaction, the segments should be interpreted as observed "
        "activity cohorts rather than permanent customer identities."
    ),
)
render_insight(
    "Business value comes from transparent caveats",
    (
        "The dashboard distinguishes statistical separation from commercial or "
        "causal validity and presents the dataset's limited longitudinal depth "
        "directly."
    ),
)

st.info(
    "Navigate to **Customer Segments** for cluster profiles and PCA, "
    "**SQL Analytics** for the 32-report catalogue, and **Business Insights** "
    "for practical recommendations."
)
