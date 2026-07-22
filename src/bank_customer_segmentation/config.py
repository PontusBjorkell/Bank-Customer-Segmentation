"""Project configuration and filesystem paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    """Resolved filesystem paths used throughout the project."""

    root: Path
    data_raw: Path
    data_processed: Path
    data_database: Path
    data_exports: Path
    reports: Path
    reports_figures: Path
    reports_sql: Path
    reports_statistical: Path
    sql: Path
    images: Path

    raw_transactions: Path
    clean_transactions: Path
    customer_features: Path
    quality_report: Path
    preparation_summary: Path

    def ensure_output_directories(self) -> None:
        """Create all directories written to by the Phase 1 pipeline."""
        for directory in (
            self.data_processed,
            self.data_database,
            self.data_exports,
            self.reports_figures,
            self.reports_sql,
            self.reports_statistical,
            self.images,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def find_project_root(start: Path | None = None) -> Path:
    """Find the repository root by searching for ``pyproject.toml``."""
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate

    # Safe fallback for an editable src-layout installation.
    return Path(__file__).resolve().parents[2]


def get_project_paths(root: Path | None = None) -> ProjectPaths:
    """Return canonical paths for the repository."""
    project_root = Path(root).resolve() if root else find_project_root()
    data = project_root / "data"
    reports = project_root / "reports"

    return ProjectPaths(
        root=project_root,
        data_raw=data / "raw",
        data_processed=data / "processed",
        data_database=data / "database",
        data_exports=data / "exports",
        reports=reports,
        reports_figures=reports / "figures",
        reports_sql=reports / "sql",
        reports_statistical=reports / "statistical",
        sql=project_root / "sql",
        images=project_root / "images",
        raw_transactions=data / "raw" / "bank_transactions.csv",
        clean_transactions=data / "processed" / "transactions_clean.csv",
        customer_features=data / "processed" / "customer_features.csv",
        quality_report=data / "processed" / "data_quality_report.csv",
        preparation_summary=data / "processed" / "preparation_summary.json",
    )
