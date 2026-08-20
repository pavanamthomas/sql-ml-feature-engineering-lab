# Query performance

The object of interest is **SQLite `EXPLAIN QUERY PLAN` text**, not a
latency number. Wall-clock times depend on the machine, the cache, and
the SQLite build. They are not recorded here and must not be invented.

## Probe query

`sql/correct/pit_explain_probe.sql` is a point-in-time 30-day aggregate:
`predictions` LEFT JOIN `transactions` on `customer_id` and
`txn_ts` in `(cutoff - 30 days, cutoff]`.

## Indexes

`sql/indexes.sql` creates, among others:

```sql
CREATE INDEX idx_txn_customer_ts ON transactions (customer_id, txn_ts);
```

`sqlfeat.explain.explain_pit_probe` drops laboratory indexes, explains,
creates them, and explains again. `scripts/run_all.py` writes
`outputs/tables/explain_plans.txt`.

## How to read the plan

SQLite prints steps such as `SCAN`, `SEARCH`, `USING INDEX`,
`COVERING INDEX`, and sometimes `AUTOMATIC COVERING INDEX` (an ephemeral
index SQLite builds for that statement). After `sql/indexes.sql` is
applied, the probe plan should mention the named index
`idx_txn_customer_ts`. Tests assert that string. They do not assert a
millisecond budget.

One observation on SQLite 3.45.3 (regenerate with `python scripts/run_all.py`):

Without laboratory indexes:

```text
SCAN p
BLOOM FILTER ON t (customer_id=?)
SEARCH t USING AUTOMATIC COVERING INDEX (customer_id=?) LEFT-JOIN
```

With `idx_txn_customer_ts`:

```text
SCAN p
SEARCH t USING INDEX idx_txn_customer_ts (customer_id=? AND txn_ts>? AND txn_ts<?) LEFT-JOIN
```

The named index is used for both `customer_id` and the timestamp range.
The automatic index in the first plan is not a laboratory artefact we
control. Plan text can change across SQLite versions. The version is
printed next to the plan.

## What this does not show

- PostgreSQL `EXPLAIN ANALYZE` (actual times, buffers).
- Join-order stability under `ANALYZE` statistics.
- Production SLAs.

Dialect notes: `docs/dialect_differences.md`.
