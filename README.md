# Bank Customer Segmentation

Phase 1 scaffold for an end-to-end bank customer analytics and segmentation project.

## Phase 1 setup

1. Place the source file at `data/raw/bank_transactions.csv`.
2. Create and activate a virtual environment.
3. Install the project and development dependencies:

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

4. Run a quick sample pipeline:

```bash
python scripts/prepare_data.py --sample-rows 10000
```

5. Run the complete preparation pipeline:

```bash
python scripts/prepare_data.py
```

6. Run the tests:

```bash
pytest
```

## Generated Phase 1 outputs

- `data/processed/transactions_clean.csv`
- `data/processed/customer_features.csv`
- `data/processed/data_quality_report.csv`
- `data/processed/preparation_summary.json`

The full README will be completed only after the database, SQL analytics, clustering, dashboard, and test phases are finished.
