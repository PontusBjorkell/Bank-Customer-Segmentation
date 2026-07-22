from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from bank_customer_segmentation.analysis import (
    export_query_catalog,
    parse_query_catalog,
)


def test_parse_query_catalog(tmp_path: Path) -> None:
    sql_path = tmp_path / "queries.sql"
    sql_path.write_text(
        """
-- name: 01_count_rows
-- description: Count records.
SELECT COUNT(*) AS row_count FROM sample;

-- name: 02_sum_values
-- description: Sum values.
SELECT SUM(value) AS total_value FROM sample;
""".strip(),
        encoding="utf-8",
    )

    queries = parse_query_catalog(sql_path)

    assert [query.name for query in queries] == ["01_count_rows", "02_sum_values"]
    assert queries[0].description == "Count records."
    assert queries[1].sql.startswith("SELECT SUM")


def test_export_query_catalog(tmp_path: Path) -> None:
    database_path = tmp_path / "test.sqlite"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE sample (value INTEGER NOT NULL)")
    connection.executemany("INSERT INTO sample(value) VALUES (?)", [(1,), (2,), (3,)])
    connection.commit()
    connection.close()

    sql_path = tmp_path / "queries.sql"
    sql_path.write_text(
        """
-- name: 01_count_rows
-- description: Count records.
SELECT COUNT(*) AS row_count FROM sample;

-- name: 02_values
-- description: Return ordered values.
SELECT value FROM sample ORDER BY value;
""".strip(),
        encoding="utf-8",
    )

    output_directory = tmp_path / "reports"
    results = export_query_catalog(database_path, sql_path, output_directory)

    assert len(results) == 2
    assert all(result.status == "success" for result in results)
    assert (output_directory / "01_count_rows.csv").exists()
    assert (output_directory / "02_values.csv").exists()
    assert (output_directory / "query_catalog.csv").exists()

    manifest = json.loads(
        (output_directory / "query_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["query_count"] == 2
    assert manifest["successful_queries"] == 2
    assert manifest["failed_queries"] == 0
