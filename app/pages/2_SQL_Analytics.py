"""Interactive browser for the exported analytical SQL catalogue."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from bank_customer_segmentation.dashboard import list_sql_report_files
from utils import (
    PATHS,
    cached_csv,
    configure_page,
    dataframe_download,
    sidebar_project_note,
)


configure_page("SQL Analytics", "🗄️")
sidebar_project_note()

st.title("🗄️ SQL Analytics")
st.caption("Browse and download the automatically generated SQL report catalogue")

catalog_path = PATHS["sql_reports"] / "query_catalog.csv"
catalog = cached_csv(str(catalog_path))
files = list_sql_report_files(PATHS["sql_reports"])

if files.empty:
    st.warning("No exported SQL reports were found.")
    st.code("python scripts/run_analysis.py", language="bash")
    st.stop()

st.metric("Available analytical reports", len(files))

if not catalog.empty:
    with st.expander("View query catalogue", expanded=False):
        st.dataframe(catalog, hide_index=True, use_container_width=True)

search = st.text_input(
    "Search reports",
    placeholder="Examples: location, balance, monthly, customer value",
)

filtered = files.copy()
if search.strip():
    filtered = filtered.loc[
        filtered["report_name"].str.contains(
            search.strip(),
            case=False,
            na=False,
        )
    ]

if filtered.empty:
    st.info("No report names match the current search.")
    st.stop()

selected_name = st.selectbox(
    "Select an analytical report",
    filtered["report_name"].tolist(),
)
selected_row = filtered.loc[
    filtered["report_name"].eq(selected_name)
].iloc[0]
selected_path = Path(selected_row["path"])
report = cached_csv(str(selected_path))

left, right = st.columns([0.7, 0.3])
with left:
    st.subheader(selected_name)
    st.caption(
        f"{len(report):,} rows · {len(report.columns):,} columns · "
        f"{selected_row['size_kb']:,.1f} KB"
    )
with right:
    dataframe_download(
        report,
        label="Download this report",
        filename=selected_path.name,
        key=f"sql-download-{selected_path.stem}",
    )

if report.empty:
    st.info("This report returned no rows.")
else:
    upper_bound = min(len(report), 500)

    if upper_bound <= 10:
        rows_to_show = upper_bound
        st.caption(f"Displaying all {rows_to_show:,} available rows.")
    else:
        default_rows = min(100, upper_bound)
        rows_to_show = st.slider(
            "Rows displayed",
            min_value=10,
            max_value=upper_bound,
            value=default_rows,
            step=10,
        )

    st.dataframe(
        report.head(rows_to_show),
        hide_index=True,
        use_container_width=True,
    )

st.divider()
st.markdown("### Why this matters")
st.markdown(
    """
    The SQL layer is version controlled and executed automatically from Python.
    Each named query is exported as a reproducible CSV, making the warehouse
    useful for dashboarding, validation, ad hoc review, and downstream delivery.
    """
)
