"""Run the complete analytical SQL catalogue and export CSV reports."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from bank_customer_segmentation.analysis import export_query_catalog
from bank_customer_segmentation.config import get_project_paths
from bank_customer_segmentation.utils import configure_logging

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="Optional SQLite database path.",
    )
    parser.add_argument(
        "--sql-file",
        type=Path,
        default=None,
        help="Optional analytical SQL catalogue path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional directory for exported CSV reports.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue running the remaining queries after a failure.",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    """Execute the SQL reporting pipeline."""
    args = parse_args()
    configure_logging(args.verbose)
    paths = get_project_paths()

    database_path = args.database or (
        paths.data_database / "bank_customer_analytics.sqlite"
    )
    sql_path = args.sql_file or (paths.sql / "analysis_queries.sql")
    output_directory = args.output_dir or paths.reports_sql

    results = export_query_catalog(
        database_path=database_path,
        sql_path=sql_path,
        output_directory=output_directory,
        continue_on_error=args.continue_on_error,
    )

    successful = sum(item.status == "success" for item in results)
    failed = len(results) - successful
    LOGGER.info(
        "SQL analytics complete: %d succeeded, %d failed, %d total",
        successful,
        failed,
        len(results),
    )


if __name__ == "__main__":
    main()
