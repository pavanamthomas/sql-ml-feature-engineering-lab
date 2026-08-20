# Feature engineering

**Estimand.** For a prediction at cutoff \(t\), the covariate vector \(X(t)\)
is a function of events with timestamp \(\le t\). The label \(y\) is a
completed order in \((t, t+30\text{ days}]\). \(y\) is a training target,
not a covariate.

**DGP.** Seed 2026. See `src/sqlfeat/generate.py`. Primary cutoff
`2025-07-01 00:00:00`. A subset of customers also has a second cutoff
`2025-10-01 00:00:00` so that lagged outcomes exist.

**Fillna policy.** Counts fill 0. Spend fills 0.0. Recency is NULL when
there is no prior transaction. Tenure is never missing. SQL and pandas
share this policy (`sqlfeat.pandas_features.FILLNA`).

## Features implemented

| Feature | Window | Notes |
| --- | --- | --- |
| `txn_count_7/30/90` | last N days ending at \(t\) | `txn_ts <= t` and `> t - N days` |
| `spend_7/30/90` | same | calendar windows, not ROWS frames |
| `recency_days` | last txn \(\le t\) | NULL if none |
| `tenure_days` | signup to \(t\) | `julianday` difference |
| `n_sessions_30`, duration, pages | sessions \(\le t\) | AVG skips NULL duration |
| login / view / cart counts | events \(\le t\) | conditional aggregation |
| `n_distinct_categories` | txns \(\le t\) | LEFT JOIN products |
| `lag_y` | previous prediction | only if previous `label_ts <= t` |
| `cohort_month` | signup month | `strftime('%Y-%m', signup_ts)` |
| `has_prior_completed_order` | EXISTS | correlated |
| `referral_depth` | recursive CTE | DAG by construction |
| `sentinel_spend` | diagnostic | must be 0 on correct queries |

## SQL constructs used

Each construct is in a query that tests execute, not a comment.

| Construct | File |
| --- | --- |
| INNER / LEFT / multi-join | `sql/correct/pit_training_table.sql`, `null_join.sql` |
| Self join | `sql/correct/self_join_referrer.sql` |
| GROUP BY / HAVING | `groupby_totals.sql`, `heavy` CTE in PIT table |
| CASE | recency, join_status, lag_y |
| CTE | almost every correct file |
| Subquery / correlated / EXISTS | `exists_prior.sql` |
| ROW_NUMBER, RANK, DENSE_RANK | `dedup.sql`, `ranking.sql` |
| LAG | `lagged_outcomes.sql`, `lag_previous_txn.sql` |
| LEAD | `sql/leaky/lead_next_txn.sql` only, as a forbidden future |
| FIRST_VALUE / LAST_VALUE | PIT table, `cohort.sql` |
| Running SUM, rolling AVG (ROWS) | PIT `txn_windows` |
| Calendar rolling | `rolling_spend.sql` |
| PARTITION BY, dedup | windows; `dedup.sql` |
| NULL handling | `null_join.sql`, COALESCE |
| Datetime | `datetime()`, `julianday()`, `strftime()` |
| Conditional aggregation / FILTER | `txn_counts.sql` |
| Recursive CTE | `referral_depth.sql` |

## What this is not

These features are predictive summaries. They do not identify a causal
effect of spending, sessions, or tenure. A high in-sample AUC on the
leaky table is not skill.
