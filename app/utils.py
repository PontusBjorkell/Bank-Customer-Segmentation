"""Streamlit-specific utilities shared across dashboard pages."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from bank_customer_segmentation.dashboard import (
    execute_query,
    load_segmentation_outputs,
    project_root_from_file,
    read_csv,
    read_json,
    resolve_project_paths,
)


PROJECT_ROOT = project_root_from_file(__file__)
PATHS = resolve_project_paths(PROJECT_ROOT)


def configure_page(
    title: str,
    icon: str,
    *,
    layout: str = "wide",
) -> None:
    """Apply consistent Streamlit page configuration and project styling."""
    st.set_page_config(
        page_title=f"{title} | Bank Customer Segmentation",
        page_icon=icon,
        layout=layout,
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 3rem;
        }
        [data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.22);
            border-radius: 0.75rem;
            padding: 0.8rem 1rem;
        }
        .insight-card {
            border: 1px solid rgba(128, 128, 128, 0.22);
            border-radius: 0.8rem;
            padding: 1rem 1.1rem;
            margin-bottom: 0.75rem;
        }
        .muted {
            color: rgba(128, 128, 128, 0.95);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_project_note() -> None:
    """Render a consistent description in the sidebar."""
    with st.sidebar:
        st.markdown("## Bank Customer Segmentation")
        st.caption(
            "An end-to-end analytics project combining reusable Python, "
            "SQLite, analytical SQL, statistical reporting, clustering, "
            "and an interactive dashboard."
        )
        st.divider()
        st.caption("Use the page navigation above to explore the project.")


@st.cache_data(show_spinner=False)
def cached_csv(path: str, nrows: int | None = None) -> pd.DataFrame:
    return read_csv(path, nrows=nrows)


@st.cache_data(show_spinner=False)
def cached_json(path: str) -> Any:
    return read_json(path, default={})


@st.cache_data(show_spinner=False)
def cached_query(query: str, params: tuple[Any, ...] | None = None) -> pd.DataFrame:
    return execute_query(PATHS["database"], query, params)


@st.cache_data(show_spinner=False)
def cached_segmentation_outputs() -> dict[str, Any]:
    return load_segmentation_outputs(PATHS)


def show_missing_artifact(
    label: str,
    path: str | Path,
    command: str | None = None,
) -> None:
    """Display a helpful dashboard message for a missing pipeline artifact."""
    st.warning(f"{label} is not available at `{path}`.")
    if command:
        st.code(command, language="bash")


def render_insight(title: str, body: str) -> None:
    """Render a compact business-insight card."""
    st.markdown(
        (
            '<div class="insight-card">'
            f"<strong>{html.escape(title)}</strong><br>"
            f'<span class="muted">{html.escape(body)}</span>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def dataframe_download(
    frame: pd.DataFrame,
    *,
    label: str,
    filename: str,
    key: str,
) -> None:
    """Render a CSV download button for a DataFrame."""
    st.download_button(
        label=label,
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        key=key,
    )
