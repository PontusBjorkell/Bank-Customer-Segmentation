#!/usr/bin/env python3
"""Run the complete Phase 1 data-preparation pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Allows direct execution before the package is installed in editable mode.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bank_customer_segmentation.config import get_project_paths
from bank_customer_segmentation.data import (
    clean_transactions,
    export_dataframe,
    load_raw_transactions,
)
from bank_customer_segmentation.features import build_customer_features
from bank_customer_segmentation.utils import configure_logging, write_json
from bank_customer_segmentation.validation import build_quality_report

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean bank transactions and build customer-level features."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Optional raw CSV path. Defaults to data/raw/bank_transactions.csv.",
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=None,
        help="Load only the first N rows for a quick development run.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable debug logging."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    paths = get_project_paths(PROJECT_ROOT)
    paths.ensure_output_directories()
    input_path = args.input.resolve() if args.input else paths.raw_transactions

    LOGGER.info("Loading raw transactions from %s", input_path)
    raw = load_raw_transactions(input_path, nrows=args.sample_rows)
    LOGGER.info("Loaded %s rows", f"{len(raw):,}")

    LOGGER.info("Cleaning and enriching transaction records")
    clean = clean_transactions(raw)

    LOGGER.info("Building customer-level segmentation features")
    customer_features = build_customer_features(clean)

    LOGGER.info("Creating data-quality report")
    quality_report = build_quality_report(raw, clean)

    LOGGER.info("Exporting processed datasets")
    export_dataframe(clean, paths.clean_transactions)
    export_dataframe(customer_features, paths.customer_features)
    export_dataframe(quality_report, paths.quality_report)

    summary = {
        "input_path": str(input_path),
        "raw_rows": int(len(raw)),
        "clean_rows": int(len(clean)),
        "unique_customers": int(customer_features["customer_id"].nunique()),
        "clean_transaction_columns": int(clean.shape[1]),
        "customer_feature_columns": int(customer_features.shape[1]),
        "quality_warnings": int((quality_report["status"] == "WARN").sum()),
        "outputs": {
            "transactions_clean": str(paths.clean_transactions),
            "customer_features": str(paths.customer_features),
            "data_quality_report": str(paths.quality_report),
        },
    }
    write_json(summary, paths.preparation_summary)

    LOGGER.info(
        "Complete: %s transactions and %s customers exported",
        f"{len(clean):,}",
        f"{len(customer_features):,}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
