"""SQLite warehouse construction and validation utilities."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pandas as pd

LOGGER = logging.getLogger(__name__)

TRANSACTION_DATE_COLUMNS = [
    "customer_dob",
    "transaction_date",
    "transaction_datetime",
]

CUSTOMER_DATE_COLUMNS = [
    "first_transaction_date",
    "last_transaction_date",
]

BOOLEAN_COLUMNS = {
    "is_weekend",
    "is_single_transaction_customer",
}


def connect_database(database_path: Path) -> sqlite3.Connection:
    """Open a configured SQLite connection."""
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = WAL;")
    connection.execute("PRAGMA synchronous = NORMAL;")
    connection.execute("PRAGMA temp_store = MEMORY;")
    connection.execute("PRAGMA cache_size = -100000;")
    return connection


def execute_sql_file(connection: sqlite3.Connection, sql_path: Path) -> None:
    """Execute all statements from a SQL file in one transaction."""
    sql_path = Path(sql_path)
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    sql = sql_path.read_text(encoding="utf-8")
    with connection:
        connection.executescript(sql)


def _iter_csv(path: Path, chunksize: int) -> Iterator[pd.DataFrame]:
    """Yield CSV chunks while preserving identifier columns as strings."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Processed dataset not found: {path}")

    yield from pd.read_csv(
        path,
        chunksize=chunksize,
        dtype={"transaction_id": "string", "customer_id": "string"},
        low_memory=False,
    )


def _normalise_sql_values(frame: pd.DataFrame) -> pd.DataFrame:
    """Convert pandas extension values into SQLite-friendly scalar values."""
    result = frame.copy()

    for column in BOOLEAN_COLUMNS.intersection(result.columns):
        result[column] = result[column].map(
            {True: 1, False: 0, "True": 1, "False": 0, "true": 1, "false": 0}
        )

    result = result.where(pd.notna(result), None)
    return result


def collect_locations(
    transactions_path: Path,
    customer_features_path: Path,
    chunksize: int = 100_000,
) -> pd.DataFrame:
    """Collect unique locations from transaction and customer datasets."""
    locations: set[str] = set()

    for chunk in _iter_csv(transactions_path, chunksize):
        if "customer_location" in chunk:
            locations.update(
                chunk["customer_location"].dropna().astype(str).str.strip().loc[lambda s: s.ne("")]
            )

    for chunk in _iter_csv(customer_features_path, chunksize):
        if "primary_location" in chunk:
            locations.update(
                chunk["primary_location"].dropna().astype(str).str.strip().loc[lambda s: s.ne("")]
            )

    ordered = sorted(locations)
    return pd.DataFrame(
        {
            "location_id": range(1, len(ordered) + 1),
            "location_name": ordered,
        }
    )


def load_locations(
    connection: sqlite3.Connection,
    transactions_path: Path,
    customer_features_path: Path,
    chunksize: int = 100_000,
) -> dict[str, int]:
    """Populate the location dimension and return its lookup mapping."""
    locations = collect_locations(
        transactions_path=transactions_path,
        customer_features_path=customer_features_path,
        chunksize=chunksize,
    )
    locations.to_sql("dim_location", connection, if_exists="append", index=False)
    return dict(zip(locations["location_name"], locations["location_id"], strict=True))


def load_customers(
    connection: sqlite3.Connection,
    customer_features_path: Path,
    location_lookup: dict[str, int],
    chunksize: int = 100_000,
) -> int:
    """Populate customer dimension and customer feature mart in chunks."""
    loaded = 0

    dimension_columns = [
        "customer_id",
        "gender",
        "customer_age",
        "primary_location_id",
        "first_transaction_date",
        "last_transaction_date",
    ]

    for chunk in _iter_csv(customer_features_path, chunksize):
        chunk["primary_location_id"] = chunk["primary_location"].map(location_lookup)

        dimension = _normalise_sql_values(chunk[dimension_columns])
        dimension.to_sql("dim_customer", connection, if_exists="append", index=False)

        mart = chunk.drop(columns=["gender", "primary_location"], errors="ignore")
        mart["primary_location_id"] = chunk["primary_location_id"]
        mart = _normalise_sql_values(mart)
        mart.to_sql("customer_feature_mart", connection, if_exists="append", index=False)

        loaded += len(chunk)
        LOGGER.info("Loaded %s customer records", f"{loaded:,}")

    return loaded


def load_transactions(
    connection: sqlite3.Connection,
    transactions_path: Path,
    location_lookup: dict[str, int],
    chunksize: int = 100_000,
) -> int:
    """Populate the transaction fact table in chunks."""
    loaded = 0

    for chunk in _iter_csv(transactions_path, chunksize):
        chunk["location_id"] = chunk["customer_location"].map(location_lookup)
        fact = chunk.drop(columns=["customer_location"], errors="ignore")
        fact = _normalise_sql_values(fact)
        fact.to_sql("fact_transaction", connection, if_exists="append", index=False)

        loaded += len(chunk)
        LOGGER.info("Loaded %s transaction records", f"{loaded:,}")

    return loaded


def database_table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    """Return row counts for core warehouse tables."""
    tables = [
        "dim_location",
        "dim_customer",
        "fact_transaction",
        "customer_feature_mart",
    ]
    return {
        table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in tables
    }


def run_integrity_checks(connection: sqlite3.Connection) -> dict[str, object]:
    """Run structural and referential database checks."""
    integrity = connection.execute("PRAGMA integrity_check;").fetchone()[0]
    foreign_key_violations = connection.execute("PRAGMA foreign_key_check;").fetchall()

    orphan_transactions = connection.execute(
        """
        SELECT COUNT(*)
        FROM fact_transaction AS t
        LEFT JOIN dim_customer AS c ON c.customer_id = t.customer_id
        WHERE c.customer_id IS NULL
        """
    ).fetchone()[0]

    return {
        "integrity_check": integrity,
        "foreign_key_violations": len(foreign_key_violations),
        "orphan_transactions": int(orphan_transactions),
    }


def build_database(
    database_path: Path,
    schema_path: Path,
    views_path: Path,
    transactions_path: Path,
    customer_features_path: Path,
    chunksize: int = 100_000,
    overwrite: bool = True,
) -> dict[str, object]:
    """Build the complete SQLite warehouse from processed CSV files."""
    database_path = Path(database_path)
    if database_path.exists() and overwrite:
        database_path.unlink()
    elif database_path.exists():
        raise FileExistsError(
            f"Database already exists at {database_path}. Use overwrite=True to rebuild it."
        )

    connection = connect_database(database_path)
    try:
        execute_sql_file(connection, schema_path)

        location_lookup = load_locations(
            connection,
            transactions_path=transactions_path,
            customer_features_path=customer_features_path,
            chunksize=chunksize,
        )
        customer_rows = load_customers(
            connection,
            customer_features_path=customer_features_path,
            location_lookup=location_lookup,
            chunksize=chunksize,
        )
        transaction_rows = load_transactions(
            connection,
            transactions_path=transactions_path,
            location_lookup=location_lookup,
            chunksize=chunksize,
        )

        execute_sql_file(connection, views_path)
        connection.execute("ANALYZE;")
        connection.commit()

        counts = database_table_counts(connection)
        checks = run_integrity_checks(connection)

        if checks["integrity_check"] != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {checks}")
        if checks["foreign_key_violations"] != 0 or checks["orphan_transactions"] != 0:
            raise RuntimeError(f"Warehouse referential integrity checks failed: {checks}")

        return {
            "database_path": str(database_path),
            "customer_rows_loaded": customer_rows,
            "transaction_rows_loaded": transaction_rows,
            "table_counts": counts,
            "integrity_checks": checks,
        }
    finally:
        connection.close()
