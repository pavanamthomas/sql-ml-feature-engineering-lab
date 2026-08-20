# SQL leakage

Leakage here means: a covariate at cutoff \(t\) is a function of rows
with timestamp \(> t\), or a function of the label that is only
observed after \(t\).

The leaky files are intentional. They are not a style guide.

## Patterns in `sql/leaky/`

| File | Subtlety |
| --- | --- |
| `join_all_transactions.sql` | No time predicate. The most common warehouse mistake. |
| `pit_training_table.sql` | Same column names as the correct table; join omits `txn_ts <= cutoff`. Includes `LEAD(y)`. |
| `txn_counts.sql` | `txn_ts <= datetime(cutoff, '+30 days')` — the label horizon. |
| `rolling_includes_label_day.sql` | `txn_ts < cutoff + 1 day` after a midnight cutoff. |
| `date_truncation.sql` | `date(txn_ts) <= date(cutoff)` includes afternoon activity. |
| `lead_next_txn.sql` | `LEAD` from the last history row looks at a later txn. |

## Why it fools a reviewer

Column names match: `txn_count_30`, `spend_30`, `recency_days`. Row
counts match (one row per prediction). `NULL` handling looks careful.
The model is the same logistic regression. Only the information set
changed.

## Sentinel

A row with `is_sentinel = 1` and amount `99999.0` is inserted seven days
after the primary cutoff. It cannot appear in a correct feature. If it
appears, the query is leaky. This check does not use the classifier.

## What leakage is not

- Using `LAG(y)` when the previous label timestamp is already \(\le t\).
  That is a lagged outcome, documented in `lagged_outcomes.sql`.
- Computing a running sum on **pre-filtered** history. The last value of
  that running sum is still a function of \(\mathcal{H}(t)\).

## Related

`docs/point_in_time_correctness.md`, `FLAGSHIP_POINT_IN_TIME_FAILURE.md`.
