# Roadmap

Current as of August 2026.

## In scope now

- Synthetic relational DGP (customers, accounts, transactions, sessions, events, products, orders, predictions, outcomes) with seed 2026.
- Point-in-time SQL features and leaky counterparts under `sql/correct/` and `sql/leaky/`.
- Sentinel tests, SQL/pandas parity, ranking ties, NULL joins, EXPLAIN QUERY PLAN.
- Flagship in-sample logistic comparison on leaky versus correct training tables.
- CI: `python -m pytest` and `python scripts/run_all.py`.

## Failures that are part of the design

- Joining transactions on `customer_id` without `txn_ts <= cutoff_ts` admits planted sentinels.
- `LEAD` of the next transaction timestamp is often after cutoff.
- Date truncation at a midnight cutoff includes same-calendar-day events after the cutoff clock time.
- GROUP BY customer totals cannot recover txn-level amounts.

Details: `docs/failures_and_corrections.md`.

## Open (issues)

1. DuckDB is not in CI. A second engine would be an independent check of the same SQL text where the dialect overlaps.
2. Late-arriving facts (a row with `txn_ts <= cutoff` inserted after cutoff) are not modelled. Point-in-time on event time is not the same as point-in-time on ingest time.
3. Time zones are not modelled. All timestamps are naive UTC strings.

## Explicitly not in scope

- Treating simulated AUC as a production model result.
- A feature store product, Spark jobs, or a warehouse migration.
- Invented empirical findings about real customers.
- Causal claims from predictive features.

Close an issue only with a test or a limitation sentence.
