from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from bank_customer_segmentation.dashboard import (
    add_segment_labels,
    dataframe_to_csv_bytes,
    execute_query,
    format_compact_currency,
    format_currency,
    format_integer,
    format_percentage,
    list_sql_report_files,
    read_json,
    resolve_project_paths,
    sample_frame,
    segment_description,
    segment_name,
)


def test_formatting_helpers() -> None:
    assert format_integer(1234.4) == "1,234"
    assert format_currency(1234.5, decimals=1) == "₹1,234.5"
    assert format_percentage(0.1234, decimals=1) == "12.3%"
    assert format_compact_currency(1_650_000_000) == "₹1.65B"
    assert format_compact_currency(2_500_000) == "₹2.50M"


def test_segment_names_are_short_and_descriptive() -> None:
    assert segment_name(0) == "Limited History"
    assert segment_name(1) == "Repeat Activity"
    assert segment_description(0) == "Low-observed-activity customers"
    assert "Repeat" in segment_description(1)
    assert segment_name(7) == "Segment 7"


def test_add_segment_labels() -> None:
    frame = pd.DataFrame({"cluster": [0, 1]})
    labelled = add_segment_labels(frame)
    assert labelled["segment_name"].tolist() == [
        "Limited History",
        "Repeat Activity",
    ]
    assert "segment_description" in labelled.columns


def test_execute_query_reads_sqlite(tmp_path: Path) -> None:
    database = tmp_path / "test.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE metrics (name TEXT, value INTEGER)")
        connection.execute("INSERT INTO metrics VALUES ('customers', 12)")
        connection.commit()

    result = execute_query(
        database,
        "SELECT * FROM metrics WHERE value > ?",
        (5,),
    )
    assert result.to_dict(orient="records") == [
        {"name": "customers", "value": 12}
    ]


def test_list_sql_report_files(tmp_path: Path) -> None:
    pd.DataFrame({"value": [1]}).to_csv(
        tmp_path / "01_portfolio_overview.csv",
        index=False,
    )
    pd.DataFrame({"value": [2]}).to_csv(
        tmp_path / "query_catalog.csv",
        index=False,
    )

    result = list_sql_report_files(tmp_path)
    assert result["filename"].tolist() == ["01_portfolio_overview.csv"]


def test_read_json_and_path_resolution(tmp_path: Path) -> None:
    json_path = tmp_path / "summary.json"
    json_path.write_text(json.dumps({"clusters": 2}), encoding="utf-8")
    assert read_json(json_path)["clusters"] == 2

    paths = resolve_project_paths(tmp_path)
    assert paths["database"].name == "bank_customer_analytics.sqlite"
    assert paths["exports"] == tmp_path / "data" / "exports"


def test_sample_and_csv_serialization() -> None:
    frame = pd.DataFrame({"value": range(100)})
    sampled = sample_frame(frame, max_rows=10, random_state=42)
    assert len(sampled) == 10
    assert dataframe_to_csv_bytes(sampled).startswith(b"value\n")
