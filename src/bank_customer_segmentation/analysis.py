"""Execution and export utilities for the analytical SQL catalogue."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

LOGGER = logging.getLogger(__name__)
QUERY_MARKER = re.compile(r"^\s*--\s*name\s*:\s*([A-Za-z0-9_-]+)\s*$", re.IGNORECASE)
DESCRIPTION_MARKER = re.compile(
    r"^\s*--\s*description\s*:\s*(.+?)\s*$", re.IGNORECASE
)


@dataclass(frozen=True)
class SQLQuery:
    """A named analytical SQL query."""

    name: str
    description: str
    sql: str


@dataclass(frozen=True)
class QueryRunResult:
    """Metadata describing one exported query result."""

    name: str
    description: str
    output_file: str
    row_count: int
    column_count: int
    duration_seconds: float
    status: str
    error: str | None = None


def parse_query_catalog(sql_path: Path) -> list[SQLQuery]:
    """Parse a SQL catalogue separated by ``-- name:`` markers."""
    sql_path = Path(sql_path)
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL catalogue not found: {sql_path}")

    queries: list[SQLQuery] = []
    current_name: str | None = None
    current_description = ""
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_name, current_description, current_lines
        if current_name is None:
            return
        statement = "\n".join(current_lines).strip()
        if not statement:
            raise ValueError(f"Query {current_name!r} has no SQL statement")
        queries.append(
            SQLQuery(
                name=current_name,
                description=current_description.strip(),
                sql=statement,
            )
        )
        current_name = None
        current_description = ""
        current_lines = []

    for line in sql_path.read_text(encoding="utf-8").splitlines():
        name_match = QUERY_MARKER.match(line)
        if name_match:
            flush()
            current_name = name_match.group(1)
            continue

        description_match = DESCRIPTION_MARKER.match(line)
        if description_match and current_name is not None and not current_lines:
            current_description = description_match.group(1)
            continue

        if current_name is not None:
            current_lines.append(line)

    flush()

    if not queries:
        raise ValueError(f"No named SQL queries found in {sql_path}")

    names = [query.name for query in queries]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"Duplicate SQL query names: {duplicates}")

    return queries


def execute_query(
    connection: sqlite3.Connection,
    query: SQLQuery,
) -> pd.DataFrame:
    """Execute one read-only analytical query and return a DataFrame."""
    first_token = query.sql.lstrip().split(maxsplit=1)[0].upper()
    if first_token not in {"SELECT", "WITH", "PRAGMA"}:
        raise ValueError(
            f"Analytical query {query.name!r} must be read-only; found {first_token!r}"
        )
    return pd.read_sql_query(query.sql, connection)


def export_query_catalog(
    database_path: Path,
    sql_path: Path,
    output_directory: Path,
    *,
    manifest_path: Path | None = None,
    continue_on_error: bool = False,
) -> list[QueryRunResult]:
    """Execute every named query and export each result as a CSV file."""
    database_path = Path(database_path)
    output_directory = Path(output_directory)
    if not database_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {database_path}")

    output_directory.mkdir(parents=True, exist_ok=True)
    queries = parse_query_catalog(sql_path)
    results: list[QueryRunResult] = []

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA query_only = ON;")
        connection.execute("PRAGMA temp_store = MEMORY;")
        connection.execute("PRAGMA cache_size = -100000;")

        for position, query in enumerate(queries, start=1):
            LOGGER.info(
                "Running SQL analysis %d/%d: %s",
                position,
                len(queries),
                query.name,
            )
            started = time.perf_counter()
            output_path = output_directory / f"{query.name}.csv"

            try:
                frame = execute_query(connection, query)
                frame.to_csv(output_path, index=False)
                duration = time.perf_counter() - started
                result = QueryRunResult(
                    name=query.name,
                    description=query.description,
                    output_file=str(output_path),
                    row_count=len(frame),
                    column_count=len(frame.columns),
                    duration_seconds=round(duration, 4),
                    status="success",
                )
                LOGGER.info(
                    "Exported %s rows to %s in %.2fs",
                    f"{len(frame):,}",
                    output_path,
                    duration,
                )
            except Exception as exc:  # noqa: BLE001 - recorded in manifest
                duration = time.perf_counter() - started
                result = QueryRunResult(
                    name=query.name,
                    description=query.description,
                    output_file=str(output_path),
                    row_count=0,
                    column_count=0,
                    duration_seconds=round(duration, 4),
                    status="failed",
                    error=str(exc),
                )
                LOGGER.exception("SQL analysis failed: %s", query.name)
                results.append(result)
                if not continue_on_error:
                    _write_manifest(results, manifest_path or output_directory / "query_manifest.json")
                    raise
                continue

            results.append(result)
    finally:
        connection.close()

    manifest = manifest_path or output_directory / "query_manifest.json"
    _write_manifest(results, manifest)
    _write_catalog_csv(results, output_directory / "query_catalog.csv")
    return results


def _write_manifest(results: list[QueryRunResult], path: Path) -> None:
    """Write machine-readable execution metadata."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "query_count": len(results),
        "successful_queries": sum(item.status == "success" for item in results),
        "failed_queries": sum(item.status == "failed" for item in results),
        "total_duration_seconds": round(
            sum(item.duration_seconds for item in results), 4
        ),
        "queries": [asdict(item) for item in results],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_catalog_csv(results: list[QueryRunResult], path: Path) -> None:
    """Write a compact tabular catalogue for dashboard and documentation use."""
    pd.DataFrame([asdict(item) for item in results]).to_csv(path, index=False)
