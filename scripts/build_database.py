#!/usr/bin/env python3
"""Build the Phase 2 SQLite analytical warehouse."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bank_customer_segmentation.config import get_project_paths
from bank_customer_segmentation.database import build_database
from bank_customer_segmentation.utils import configure_logging, write_json

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the SQLite warehouse from Phase 1 processed datasets."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="Optional output database path.",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=100_000,
        help="Rows loaded per CSV chunk (default: 100000).",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Fail instead of replacing an existing database.",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    paths = get_project_paths(PROJECT_ROOT)
    paths.ensure_output_directories()

    database_path = (
        args.database.resolve()
        if args.database
        else paths.data_database / "bank_customer_analytics.sqlite"
    )

    LOGGER.info("Building SQLite warehouse at %s", database_path)
    summary = build_database(
        database_path=database_path,
        schema_path=paths.sql / "create_schema.sql",
        views_path=paths.sql / "create_views.sql",
        transactions_path=paths.clean_transactions,
        customer_features_path=paths.customer_features,
        chunksize=args.chunksize,
        overwrite=not args.no_overwrite,
    )

    summary_path = paths.data_database / "database_build_summary.json"
    write_json(summary, summary_path)

    LOGGER.info("Database build complete")
    for table, count in summary["table_counts"].items():
        LOGGER.info("%s: %s rows", table, f"{count:,}")
    LOGGER.info("Summary written to %s", summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
