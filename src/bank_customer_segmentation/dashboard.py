"""Reusable data-access and presentation helpers for the Streamlit dashboard."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


DEFAULT_DATABASE_NAME = "bank_customer_analytics.sqlite"


def project_root_from_file(file_path: str | Path) -> Path:
    """Resolve the repository root from a file inside ``app/`` or ``src/``."""
    path = Path(file_path).resolve()
    for parent in [path.parent, *path.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise FileNotFoundError("Could not locate project root containing pyproject.toml.")


def resolve_project_paths(project_root: str | Path) -> dict[str, Path]:
    """Return the dashboard's standard input and output paths."""
    root = Path(project_root).resolve()
    return {
        "root": root,
        "database": root / "data" / "database" / DEFAULT_DATABASE_NAME,
        "sql_reports": root / "reports" / "sql",
        "statistical_reports": root / "reports" / "statistical",
        "figures": root / "reports" / "figures",
        "exports": root / "data" / "exports",
        "processed": root / "data" / "processed",
    }


def read_json(path: str | Path, default: Any = None) -> Any:
    """Read JSON safely and return ``default`` when unavailable."""
    file_path = Path(path)
    if not file_path.exists():
        return default
    with file_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(
    path: str | Path,
    *,
    nrows: int | None = None,
    usecols: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Read a CSV safely, returning an empty frame when it does not exist."""
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    return pd.read_csv(file_path, nrows=nrows, usecols=usecols)


def execute_query(
    database_path: str | Path,
    query: str,
    params: tuple[Any, ...] | dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Execute a read-only SQLite query and return its result."""
    db_path = Path(database_path)
    if not db_path.exists():
        return pd.DataFrame()

    with sqlite3.connect(db_path) as connection:
        return pd.read_sql_query(query, connection, params=params)


def list_sql_report_files(report_directory: str | Path) -> pd.DataFrame:
    """Return metadata for generated SQL report CSV files."""
    directory = Path(report_directory)
    rows: list[dict[str, Any]] = []

    if not directory.exists():
        return pd.DataFrame(
            columns=["report_name", "filename", "path", "size_kb"]
        )

    for path in sorted(directory.glob("*.csv")):
        if path.name == "query_catalog.csv":
            continue
        rows.append(
            {
                "report_name": path.stem.replace("_", " ").title(),
                "filename": path.name,
                "path": str(path),
                "size_kb": round(path.stat().st_size / 1024, 1),
            }
        )

    return pd.DataFrame(rows)


def load_segmentation_outputs(paths: dict[str, Path]) -> dict[str, Any]:
    """Load the standard segmentation artifacts."""
    statistical = paths["statistical_reports"]
    exports = paths["exports"]

    return {
        "summary": read_json(statistical / "segmentation_summary.json", default={}),
        "cluster_profile": read_csv(statistical / "cluster_profile.csv"),
        "standardized_profile": read_csv(
            statistical / "cluster_standardized_profile.csv"
        ),
        "model_comparison": read_csv(
            statistical / "clustering_model_comparison.csv"
        ),
        "feature_importance": read_csv(
            statistical / "cluster_feature_importance.csv"
        ),
        "effect_ranges": read_csv(
            statistical / "cluster_effect_ranges.csv"
        ),
        "kruskal_tests": read_csv(
            statistical / "cluster_kruskal_wallis_tests.csv"
        ),
        "pca_projection": read_csv(
            statistical / "pca_customer_projection.csv"
        ),
        "assignments_path": exports / "customer_segment_assignments.csv",
    }


def format_integer(value: Any) -> str:
    if pd.isna(value):
        return "—"
    return f"{int(round(float(value))):,}"


def format_currency(value: Any, decimals: int = 0) -> str:
    if pd.isna(value):
        return "—"
    return f"₹{float(value):,.{decimals}f}"


def format_compact_currency(value: Any) -> str:
    """Format large rupee values compactly for narrow KPI cards."""
    if pd.isna(value):
        return "—"
    number = float(value)
    absolute = abs(number)
    if absolute >= 1_000_000_000:
        return f"₹{number / 1_000_000_000:.2f}B"
    if absolute >= 1_000_000:
        return f"₹{number / 1_000_000:.2f}M"
    if absolute >= 1_000:
        return f"₹{number / 1_000:.1f}K"
    return f"₹{number:,.0f}"


def format_percentage(value: Any, decimals: int = 1) -> str:
    if pd.isna(value):
        return "—"
    return f"{100.0 * float(value):.{decimals}f}%"


def segment_name(cluster: int | float | str) -> str:
    """Return short labels that fit cleanly in dashboard visualizations."""
    try:
        cluster_id = int(cluster)
    except (TypeError, ValueError):
        return f"Segment {cluster}"

    labels = {
        0: "Limited History",
        1: "Repeat Activity",
    }
    return labels.get(cluster_id, f"Segment {cluster_id}")


def segment_description(cluster: int | float | str) -> str:
    """Return a cautious longer interpretation for narrative text."""
    try:
        cluster_id = int(cluster)
    except (TypeError, ValueError):
        return f"Segment {cluster}"

    labels = {
        0: "Low-observed-activity customers",
        1: "Repeat and higher-observed-activity customers",
    }
    return labels.get(cluster_id, f"Segment {cluster_id}")


def add_segment_labels(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    if "cluster" in output.columns:
        output["segment_name"] = output["cluster"].map(segment_name)
        output["segment_description"] = output["cluster"].map(
            segment_description
        )
    return output


def dataframe_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8")


def sample_frame(
    frame: pd.DataFrame,
    max_rows: int,
    random_state: int = 42,
) -> pd.DataFrame:
    if len(frame) <= max_rows:
        return frame.copy()
    return frame.sample(max_rows, random_state=random_state)


def required_artifact_status(paths: dict[str, Path]) -> pd.DataFrame:
    checks = [
        ("SQLite warehouse", paths["database"]),
        ("SQL query catalogue", paths["sql_reports"] / "query_catalog.csv"),
        (
            "Segmentation summary",
            paths["statistical_reports"] / "segmentation_summary.json",
        ),
        (
            "Cluster profile",
            paths["statistical_reports"] / "cluster_profile.csv",
        ),
        (
            "Customer assignments",
            paths["exports"] / "customer_segment_assignments.csv",
        ),
    ]

    return pd.DataFrame(
        [
            {"artifact": label, "available": path.exists(), "path": str(path)}
            for label, path in checks
        ]
    )
