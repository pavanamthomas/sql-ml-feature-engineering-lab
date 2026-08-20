# NULL semantics

SQLite and PostgreSQL agree on the facts that matter here.

## Predicates

`NULL = NULL` is unknown, not true. A join `ON a.x = b.x` never matches
NULL keys. `WHERE x = NULL` filters every row out. Use `IS NULL`.

## LEFT vs INNER

`customers.segment` is NULL for about 10% of the DGP. `segment_lookup`
has rows for `A` and `B` only, not `C`.

- `LEFT JOIN` keeps every customer. `risk_bucket` is NULL for NULL
  segments and for unmatched `C`.
- `INNER JOIN` drops both groups.

Tests: `tests/test_null_joins.py`.

## Aggregates

`COUNT(*)` counts rows. `COUNT(col)` skips NULL `col`. `AVG(duration_sec)`
skips NULL durations. `SUM` of an empty set is NULL; the feature SQL
uses `COALESCE(..., 0)` for spend and counts after LEFT JOIN.

## Recency

No prior transaction is not recency zero. Recency is NULL. Filling zero
would tell a model “the last event was just now.” The logistic flagship
fills recency with the **column median on the model matrix only**. That
is a classifier convention, not the feature-store policy.

## COALESCE vs IFNULL

SQLite `IFNULL` is two-argument. `COALESCE` is the portable form used
here.
