"""General utility helpers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any


def configure_logging(verbose: bool = False) -> None:
    """Configure consistent console logging for command-line scripts."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )


def write_json(payload: dict[str, Any], path: Path) -> None:
    """Write JSON with deterministic, human-readable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str, sort_keys=True)
