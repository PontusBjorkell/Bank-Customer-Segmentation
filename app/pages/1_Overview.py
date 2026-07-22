"""Portfolio and transaction overview page."""

from __future__ import annotations

import altair as alt
import pandas as pd
import plotly.express as px
import streamlit as st

from bank_customer_segmentation.dashboard import (
    format_currency,
    format_integer,
    format_percentage,
)
from utils import (
    cached_query,
    configure_page,
    dataframe_download,
    sidebar_project_note,
)


configure_page("Overview", "📊")
sidebar_project_note()

st.title("📊 Portfolio Overview")
st.caption("Headline KPIs, transaction timing, location activity, and coverage")

coverage = cached_query("SELECT * FROM vw_data_coverage")
if coverage.empty:
    st.error("SQLite outputs are missing. Run `python scripts/build_database.py`.")
    st.stop()

coverage_row = coverage.iloc[0]
transactions = int(coverage_row["transaction_count"])
customers = int(coverage_row["unique_customers"])

portfolio = cached_query(
    """
    SELECT
        SUM(transaction_amount_inr) AS total_value,
        AVG(transaction_amount_inr) AS average_transaction,
        AVG(account_balance_inr) AS average_balance,
        AVG(CASE WHEN is_weekend = 1 THEN 1.0 ELSE 0.0 END) AS weekend_share
    FROM fact_transaction
    """
).iloc[0]

metric_cols = st.columns(6)
metric_cols[0].metric("Transactions", format_integer(transactions))
metric_cols[1].metric("Customers", format_integer(customers))
metric_cols[2].metric(
    "Transactions/customer",
    f"{transactions / customers:.2f}",
)
metric_cols[3].metric("Total value", format_currency(portfolio["total_value"]))
metric_cols[4].metric(
    "Average transaction",
    format_currency(portfolio["average_transaction"]),
)
metric_cols[5].metric(
    "Weekend share",
    format_percentage(portfolio["weekend_share"]),
)

st.divider()
left, right = st.columns(2)

monthly = cached_query(
    """
    SELECT *
    FROM vw_monthly_kpis
    ORDER BY transaction_month
    """
)

with left:
    st.subheader("Monthly transaction activity")
    if not monthly.empty:
        monthly["transaction_month"] = pd.to_datetime(
            monthly["transaction_month"],
            errors="coerce",
        )
        figure = px.line(
            monthly,
            x="transaction_month",
            y="transaction_count",
            markers=True,
            labels={
                "transaction_month": "Month",
                "transaction_count": "Transactions",
            },
        )
        figure.update_layout(margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(figure, use_container_width=True)
    else:
        st.info("No monthly KPI records are available.")

with right:
    st.subheader("Transaction activity by hour")
    hourly = cached_query(
        """
        SELECT
            transaction_hour,
            COUNT(*) AS transaction_count,
            AVG(transaction_amount_inr) AS average_transaction_amount
        FROM fact_transaction
        WHERE transaction_hour IS NOT NULL
        GROUP BY transaction_hour
        ORDER BY transaction_hour
        """
    )
    chart = (
        alt.Chart(hourly)
        .mark_bar()
        .encode(
            x=alt.X("transaction_hour:O", title="Hour"),
            y=alt.Y("transaction_count:Q", title="Transactions"),
            tooltip=[
                alt.Tooltip("transaction_hour:O", title="Hour"),
                alt.Tooltip(
                    "transaction_count:Q",
                    title="Transactions",
                    format=",",
                ),
                alt.Tooltip(
                    "average_transaction_amount:Q",
                    title="Average amount",
                    format=",.2f",
                ),
            ],
        )
        .properties(height=360)
    )
    st.altair_chart(chart, use_container_width=True)

st.divider()
st.subheader("Top customer locations")

minimum_customers = st.slider(
    "Minimum unique customers",
    min_value=1,
    max_value=1000,
    value=100,
    step=25,
)

locations = cached_query(
    """
    SELECT
        location_name,
        transaction_count,
        unique_customers,
        total_transaction_amount_inr,
        average_transaction_amount_inr,
        average_account_balance_inr
    FROM vw_location_performance
    WHERE unique_customers >= ?
    ORDER BY unique_customers DESC
    LIMIT 30
    """,
    (minimum_customers,),
)

if not locations.empty:
    location_chart = px.bar(
        locations.head(15).sort_values("unique_customers"),
        x="unique_customers",
        y="location_name",
        orientation="h",
        hover_data=[
            "transaction_count",
            "total_transaction_amount_inr",
            "average_transaction_amount_inr",
        ],
        labels={
            "unique_customers": "Unique customers",
            "location_name": "Location",
        },
    )
    location_chart.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(location_chart, use_container_width=True)

    st.dataframe(
        locations,
        hide_index=True,
        use_container_width=True,
        column_config={
            "total_transaction_amount_inr": st.column_config.NumberColumn(
                "Total amount",
                format="₹ %.0f",
            ),
            "average_transaction_amount_inr": st.column_config.NumberColumn(
                "Average transaction",
                format="₹ %.2f",
            ),
            "average_account_balance_inr": st.column_config.NumberColumn(
                "Average balance",
                format="₹ %.2f",
            ),
        },
    )
    dataframe_download(
        locations,
        label="Download filtered locations",
        filename="filtered_location_performance.csv",
        key="overview-locations-download",
    )

st.divider()
st.subheader("Data coverage")

coverage_long = pd.DataFrame(
    {
        "field": [
            "Age",
            "Gender",
            "Location",
            "Account balance",
            "Transaction date",
            "Transaction time",
            "Transaction amount",
        ],
        "missing_records": [
            coverage_row["missing_age_count"],
            coverage_row["missing_gender_count"],
            coverage_row["missing_location_count"],
            coverage_row["missing_balance_count"],
            coverage_row["missing_date_count"],
            coverage_row["missing_time_count"],
            coverage_row["missing_amount_count"],
        ],
    }
)
coverage_long["missing_share"] = coverage_long["missing_records"] / transactions

st.dataframe(
    coverage_long,
    hide_index=True,
    use_container_width=True,
    column_config={
        "missing_records": st.column_config.NumberColumn(
            "Missing records",
            format="%d",
        ),
        "missing_share": st.column_config.ProgressColumn(
            "Missing share",
            min_value=0.0,
            max_value=max(float(coverage_long["missing_share"].max()), 0.01),
            format="%.3f",
        ),
    },
)
