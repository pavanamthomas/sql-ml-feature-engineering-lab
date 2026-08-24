# Roadmap

Engine and event-time limits remaining after the compact DuckDB fixture entered CI (August 2026).

## In scope now

- Synthetic relational DGP (customers, accounts, transactions, sessions, events, products, orders, predictions, outcomes) with seed 2026.
- Point-in-time SQL features and leaky counterparts under `sql/correct/` and `sql/leaky/`.
- Sentinel tests, SQL/Pandas parity, ranking ties, NULL joins, and EXPLAIN QUERY PLAN.
- A compact SQLite/DuckDB parity fixture for point-in-time count, spend, recency, NULL behavior, and ranking-window semantics.
- Flagship in-sample logistic comparison on leaky versus correct training tables.
- CI runs `python -m pytest` and `python scripts/run_all.py`; the test suite installs DuckDB and exercises the cross-engine checks.

## Failures that are part of the design

- Joining transactions on `customer_id` without `txn_ts <= cutoff_ts` admits planted sentinels.
- `LEAD` of the next transaction timestamp can cross the prediction cutoff.
- Date truncation at a midnight cutoff can include same-calendar-day events after the cutoff clock time.
- GROUP BY customer totals cannot recover transaction-level amounts.
- A query can match across SQLite and DuckDB and still be wrong if both engines are given the same invalid information set; the independent Pandas route and sentinel are retained for that reason.

Details: `docs/failures_and_corrections.md` and `docs/cross_engine_parity.md`.

## Open (issues)

1. Late-arriving facts are not modelled. A row with event time before cutoff but ingestion after cutoff can still pass an event-time predicate. Event-time correctness is not ingestion-time correctness.
2. Time zones are not modelled. Timestamps in the main synthetic DGP are naive UTC-style strings.
3. PostgreSQL-specific behavior is not executable in CI. DuckDB provides a second SQL engine, not a guarantee of PostgreSQL equivalence.
4. Query-plan parity is not claimed. The cross-engine work checks result semantics on deterministic fixtures, not optimizer behavior.

## Explicitly not in scope

- Treating simulated AUC as a production model result.
- A feature-store product, Spark jobs, or a warehouse migration.
- Invented empirical findings about real customers.
- Causal claims from predictive features.
- Claiming broad database expertise from one cross-engine fixture.

Close an issue only with executable evidence or a limitation sentence that narrows the claim.
