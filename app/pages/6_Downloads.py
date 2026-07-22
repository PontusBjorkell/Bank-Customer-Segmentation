"""Central download page for generated reports and model outputs."""

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


configure_page("Downloads", "⬇️")
sidebar_project_note()

st.title("⬇️ Downloads")
st.caption("Export SQL reports, statistical tables, and customer assignments")

with st.container(border=True):
    st.subheader("SQL reports")
    st.caption(
        "Download any report generated from the version-controlled analytical "
        "SQL catalogue."
    )
    sql_files = list_sql_report_files(PATHS["sql_reports"])

    if sql_files.empty:
        st.info("No SQL report CSV files are available.")
    else:
        selected_sql = st.selectbox(
            "Choose a SQL report",
            sql_files["report_name"].tolist(),
        )
        row = sql_files.loc[
            sql_files["report_name"].eq(selected_sql)
        ].iloc[0]
        frame = cached_csv(row["path"])
        st.caption(
            f"{len(frame):,} rows · {len(frame.columns):,} columns · "
            f"{row['size_kb']:,.1f} KB"
        )
        st.dataframe(frame.head(100), hide_index=True, use_container_width=True)
        dataframe_download(
            frame,
            label="Download selected SQL report",
            filename=row["filename"],
            key=f"downloads-sql-{row['filename']}",
        )

with st.container(border=True):
    st.subheader("Statistical and segmentation tables")
    st.caption(
        "Download model comparisons, profiles, feature tests, and other "
        "generated statistical outputs."
    )
    statistical_files = sorted(PATHS["statistical_reports"].glob("*.csv"))
    if statistical_files:
        selected_stat = st.selectbox(
            "Choose a statistical table",
            [path.name for path in statistical_files],
        )
        selected_path = PATHS["statistical_reports"] / selected_stat
        stat_frame = cached_csv(str(selected_path))
        st.caption(
            f"{len(stat_frame):,} rows · {len(stat_frame.columns):,} columns · "
            f"{selected_path.stat().st_size / 1024:,.1f} KB"
        )
        st.dataframe(
            stat_frame.head(100),
            hide_index=True,
            use_container_width=True,
        )
        dataframe_download(
            stat_frame,
            label="Download selected statistical table",
            filename=selected_path.name,
            key=f"downloads-stat-{selected_path.name}",
        )
    else:
        st.info("No statistical CSV outputs are available.")

with st.container(border=True):
    st.subheader("Customer segment assignments")
    assignment_path = PATHS["exports"] / "customer_segment_assignments.csv"
    if assignment_path.exists():
        st.caption(
            f"File size: {assignment_path.stat().st_size / (1024 ** 2):,.1f} MB"
        )
        st.warning(
            "This file contains all customer IDs and segment assignments and "
            "may be large. It remains a local generated artifact and is not "
            "committed to Git."
        )
        with assignment_path.open("rb") as handle:
            st.download_button(
                label="Download all customer assignments",
                data=handle.read(),
                file_name=assignment_path.name,
                mime="text/csv",
                key="downloads-assignments",
            )
    else:
        st.info("The customer assignment export is not available.")

with st.container(border=True):
    st.subheader("Generated figures")
    st.caption(
        "Preview and download static figures produced by the statistical "
        "analysis pipeline."
    )
    figure_files = sorted(PATHS["figures"].glob("*.png"))
    if not figure_files:
        st.info("No generated PNG figures are available.")
    else:
        selected_figure = st.selectbox(
            "Preview generated figure",
            [path.name for path in figure_files],
        )
        figure_path = PATHS["figures"] / selected_figure
        st.image(str(figure_path), use_container_width=True)
        with figure_path.open("rb") as handle:
            st.download_button(
                label="Download figure",
                data=handle.read(),
                file_name=figure_path.name,
                mime="image/png",
                key=f"downloads-figure-{figure_path.name}",
            )
