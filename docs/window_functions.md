# Window functions

Windows compute an aggregate without collapsing the grain. `GROUP BY`
collapses it. That is Case A.

## Ranking on ties

On scores 30, 20, 20, 20, 10 (desc):

| Function | Ranks |
| --- | --- |
| `ROW_NUMBER()` | 1, 2, 3, 4, 5 |
| `RANK()` | 1, 2, 2, 2, 5 |
| `DENSE_RANK()` | 1, 2, 2, 2, 3 |

`ROW_NUMBER` needs a deterministic `ORDER BY` (include a unique key) if
you will filter `rn = 1`. Dedup uses `ORDER BY ingested_ts DESC, raw_id DESC`.

## LAG and LEAD

`LAG` reads an earlier row in the partition order. `LEAD` reads a later
row. For event time, “later” is often the future. This laboratory treats
`LEAD` of transactions as forbidden for contemporaneous ML features
unless the next row is still \(\le t\), which the leaky query does not
enforce.

## Frames

Default frame in SQLite (and PostgreSQL) is
`RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`. Consequences:

- Running `SUM(amount) OVER (ORDER BY txn_ts)` is a prefix sum. Intended.
- `LAST_VALUE(x)` under the default frame is \(x\) on the current row.
  Use `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING` if you
  mean the last row of the partition, and only after history is filtered
  to \(\le t\).

`ROWS BETWEEN 2 PRECEDING AND CURRENT ROW` is three **rows**, not three
days. Calendar 7/30/90 features are joins with `datetime(cutoff, '-N days')`.

## Filter then window

See `docs/point_in_time_correctness.md`. A window on the full table is
not point-in-time.

## SQLite notes

Window functions require SQLite \(\ge\) 3.25. `FILTER` on aggregates
requires \(\ge\) 3.30. Python 3.11’s stdlib SQLite is expected to
satisfy both; CI records `sqlite_version()` via `scripts/run_all.py`.
