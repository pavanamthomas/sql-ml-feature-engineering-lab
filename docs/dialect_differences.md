# Dialect differences

The executable dialect is **SQLite** (Python stdlib) so CI needs no
server. Queries are written in a PostgreSQL-like style where SQLite
allows it. DuckDB is a reasonable local third engine and is **not**
required in CI.

## FILTER clause

PostgreSQL and SQLite \(\ge\) 3.30:

```sql
SUM(amount) FILTER (WHERE txn_ts > datetime(cutoff_ts, '-7 days'))
```

Portable equivalent:

```sql
SUM(CASE WHEN txn_ts > datetime(cutoff_ts, '-7 days') THEN amount END)
```

This laboratory uses both. Older SQLite without `FILTER` would need the
`CASE` form.

## DISTINCT ON

PostgreSQL:

```sql
SELECT DISTINCT ON (txn_id) *
FROM transactions_raw
ORDER BY txn_id, ingested_ts DESC, raw_id DESC;
```

SQLite has no `DISTINCT ON`. The equivalent is `ROW_NUMBER()` plus
`WHERE rn = 1` (`sql/correct/dedup.sql`). DuckDB supports `DISTINCT ON`.

## date_trunc vs strftime vs datetime

| Intent | PostgreSQL | SQLite (this repo) |
| --- | --- | --- |
| Month bucket | `date_trunc('month', ts)` | `strftime('%Y-%m', ts)` |
| Calendar date | `ts::date` | `date(ts)` |
| Minus 7 days | `ts - interval '7 days'` | `datetime(ts, '-7 days')` |
| Day difference | `extract(epoch from (a-b))/86400` | `julianday(a) - julianday(b)` |

`date(ts)` is a truncation. Using it as a cutoff predicate is a leak at
midnight cutoffs (`sql/leaky/date_truncation.sql`).

## Timestamps

PostgreSQL would use `timestamptz`. Here timestamps are ISO-8601 TEXT at
second precision. That is a laboratory choice, not a recommendation for
a bank warehouse.

## Recursive CTE

Supported in both engines. Depth is capped in `referral_depth.sql`.
The DGP guarantees `referred_by < customer_id`, so there are no cycles.

## Window frames

`ROWS` frames are portable. Time-based `RANGE` with intervals is not
used; SQLite does not match PostgreSQL interval `RANGE`. Calendar
windows are explicit timestamp predicates.
