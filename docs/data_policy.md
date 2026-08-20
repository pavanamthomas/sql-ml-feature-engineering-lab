# Data policy

This repository is a SQL feature-engineering laboratory. It does not ship
observational microdata, bank extracts, or proprietary files.

## What is used

All tables are **simulated**. The data-generating process is
`src/sqlfeat/generate.py`, seed **2026**. `scripts/generate_data.py` writes
`data/lab.sqlite` for inspection. Tests build an in-memory copy of the same
DGP. Randomness is a `numpy.random.Generator`.

Tables: customers, accounts, transactions, `transactions_raw`, sessions,
events, products, orders, predictions, outcomes, plus small lookup tables
for ranking ties and NULL-join semantics.

Planted **sentinels** (`is_sentinel = 1`, amount `99999.0`, event type
`SENTINEL_FUTURE`) exist only after the primary cutoff. They are canaries,
not a model of fraud.

## What is not claimed

Row counts, AUCs, and EXPLAIN plans describe this DGP and this SQLite
build. They are not estimates for a real customer base, a published study,
or a deployed model.

## Regeneration

`data/*.sqlite` and files under `outputs/` are disposable. Git ignores them
except for `.gitkeep` and `data/README.md`. A clean clone plus the README
commands regenerates them.

## Third-party code

The package depends on NumPy, pandas, scikit-learn, matplotlib, and pytest
under their licences. DuckDB is optional and is not required in CI. This
repository does not copy textbook exercises or copyrighted course SQL into
`sql/` or `docs/`.
