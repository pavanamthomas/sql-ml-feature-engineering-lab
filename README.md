# sql-ml-feature-engineering-lab

[![CI](https://github.com/pavanamthomas/sql-ml-feature-engineering-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/pavanamthomas/sql-ml-feature-engineering-lab/actions)

Point-in-time SQL feature engineering for relational event data, with
deliberate leaky queries and planted future-only sentinels.

This repository is a laboratory. It answers a single question: **how do
we create analytical and ML features from relational event data without
leakage or temporal inconsistencies?** It is not a set of beginner JOIN
exercises. It is not a feature-store product. It is not an empirical
study of real customers.

Author: Dr. Pavanam Thomas ([GitHub](https://github.com/pavanamthomas), thomaspavanam@gmail.com).

**Problem → formalization → assumptions → computation → validation → interpretation → limitations.**

## Recruiter 90-Second Audit

1. [`FLAGSHIP_POINT_IN_TIME_FAILURE.md`](FLAGSHIP_POINT_IN_TIME_FAILURE.md) — two pipelines, similar column names; one includes the future; in-sample logistic AUC inflates; a sentinel test catches the leak without the model.
2. [`sql/correct/`](sql/correct/) versus [`sql/leaky/`](sql/leaky/) — read the time predicates, not the SELECT lists.
3. [`docs/failures_and_corrections.md`](docs/failures_and_corrections.md) — failures the tests are required to keep visible.
4. [`tests/test_sentinel.py`](tests/test_sentinel.py), [`tests/test_pit.py`](tests/test_pit.py), [`tests/test_flagship.py`](tests/test_flagship.py), [`tests/test_sql_pandas_equality.py`](tests/test_sql_pandas_equality.py) — properties, not smoke tests.
5. [`docs/point_in_time_correctness.md`](docs/point_in_time_correctness.md) and [`docs/sql_leakage.md`](docs/sql_leakage.md) — information set, date truncation, `LEAD`.
6. [`ROADMAP.md`](ROADMAP.md) — bounds. Process: [`docs/lab_process.md`](docs/lab_process.md).

Reproduce:

```bash
python -m pip install -e .
python -m pytest
python scripts/run_all.py
```

Python 3.11 or newer. SQLite is the stdlib dialect. DuckDB is optional and is not in CI.

## Technical Decisions I Can Defend

- **Event time \(\le\) cutoff as the information set.** Checkable on a known DGP. Not a full CDC story (ingest time is out of scope; see ROADMAP).
- **SQL files as the artefact.** Tests execute `sql/correct/*.sql` and `sql/leaky/*.sql`. The query text is what a reviewer should argue with.
- **SQLite in CI.** No server. PostgreSQL-style `FILTER`, windows, and CTEs where SQLite supports them. Gaps (`DISTINCT ON`, `date_trunc`) are documented in [`docs/dialect_differences.md`](docs/dialect_differences.md), not papered over.
- **Sentinels instead of code review alone.** A planted post-cutoff amount of `99999.0` must be absent from correct features and present in leaky ones.
- **Pandas as a second engine** for counts, spend, recency, tenure, sessions — not a second copy of the SQL parser. Fillna: counts 0, spend 0, recency NULL.
- **In-sample logistic on the flagship.** If leakage inflates fit for a linear model, a more flexible model is not needed to see the artefact. The AUC is a diagnostic, not a leaderboard.
- **EXPLAIN QUERY PLAN, not milliseconds.** [`docs/query_performance.md`](docs/query_performance.md).

## Deliberate Failure Cases

| Case | What goes wrong |
| --- | --- |
| A. GROUP BY vs window | Customer totals destroy txn-level amount |
| B. Dedup | `ROW_NUMBER` on ingest time; the later amount is the one that must survive |
| C. Cohort table | Month buckets via `strftime`; not a causal retention estimate |
| D. Ranking ties | `ROW_NUMBER` / `RANK` / `DENSE_RANK` disagree on a known score list |
| E. LAG vs LEAD | `LEAD` of the next transaction is often after cutoff |
| F. Full PIT table | Correct join predicate `ts <= cutoff` |
| G. Pandas parity | Same estimand, second implementation |
| H. Indexes | Plan text mentions `idx_txn_customer_ts` after `CREATE INDEX` |

Leaky SQL: join without time, label-window `+30 days`, label-day `+1 day`, date truncation at midnight, `LEAD`. Details: [`docs/failures_and_corrections.md`](docs/failures_and_corrections.md).

## Independent Validation

Tests check properties:

- Primary keys unique; row counts in band; generator identical under seed 2026.
- Dedup cardinality equals `transactions`; later ingest wins.
- Correct features: `sentinel_spend = 0`; leaky features: known ids show `99999.0`.
- Date truncation includes same-day-after-midnight rows planted for that purpose.
- SQL vs pandas after sort on `prediction_id`; recency NULL stays NULL.
- LEFT JOIN keeps NULL segments; INNER JOIN drops them; `NULL = NULL` does not match.
- Ranking identities on `rank_demo`.
- Leaky in-sample AUC exceeds correct AUC on this DGP.

## Reproduce Everything

```bash
python -m pip install -e .
python -m pytest
python scripts/run_all.py
python scripts/generate_data.py   # optional: data/lab.sqlite
```

`scripts/run_all.py` writes `outputs/figures/flagship_auc.png`,
`outputs/tables/run_summary.csv`, cohort and rank CSVs, and
`outputs/tables/explain_plans.txt`. Those files are regenerable. The
source of truth is the SQL plus the tests.

## Limitations and Non-Claims

- The DGP is stylised. It is a tool for checking queries, not a model of a bank.
- Point-in-time on **event** timestamps is not point-in-time on **ingest** time.
- Time zones are not modelled.
- In-sample AUC is not out-of-sample skill and not a causal effect.
- SQLite plans are not PostgreSQL plans.
- No result here is an empirical finding about real customers.

Data policy: [`docs/data_policy.md`](docs/data_policy.md).

## Interview Questions This Repository Naturally Raises

- If a cutoff is `2025-07-01 00:00:00`, what is the difference between `txn_ts <= cutoff_ts` and `date(txn_ts) <= date(cutoff_ts)`?
- When is `LAG(y)` a valid feature and when is it target leakage?
- Why is `LEAD` of the next transaction a problem even if you never select the label column?
- How would you test a Spark or dbt pipeline for the same information-set claim without a planted sentinel?
- `LAST_VALUE` under the default window frame: what value do you actually get?
- A customer has no transactions before cutoff. Should recency be 0 or NULL? What does each choice tell a linear model?
- You index `(customer_id, txn_ts)`. What would you look for in `EXPLAIN QUERY PLAN`, and what would you refuse to claim?
- GROUP BY customer spend vs `SUM(amount) OVER (PARTITION BY customer_id)`: which grain does a txn-level fraud rule need?
- `RANK` vs `ROW_NUMBER` for “top 1 session per day” when two sessions share a timestamp.
- Event time vs processing time: which failure in this repository is still untested?
- If leaky AUC is 0.95 and correct AUC is 0.62, what sentence belongs in a model review, and what sentence does not?
- How would `FILTER (WHERE ...)` and a `CASE` aggregate diverge on NULL amounts?
- Recursive referral depth: what breaks if `referred_by` can point at a descendant?
- You must port `DISTINCT ON (txn_id)` to SQLite. What is the exact window equivalent, including the tie-break?
- Why is a 30-day **row** frame not a 30-day **calendar** feature?
- Can a query pass the sentinel test and still leak the label? Give a construction.
- What changes if labels are observed at `label_ts` but features were built at `cutoff_ts` with delayed events that carry old timestamps?

## Repository structure

```text
sql-ml-feature-engineering-lab/
├── FLAGSHIP_POINT_IN_TIME_FAILURE.md
├── sql/correct/          # PIT queries
├── sql/leaky/            # intentional information-set bugs
├── src/sqlfeat/
├── scripts/run_all.py
├── scripts/generate_data.py
├── tests/
├── docs/
└── outputs/              # regenerable
```

Package: `sqlfeat`. Related laboratories: [statistical-reasoning-validation](https://github.com/pavanamthomas/statistical-reasoning-validation), [time-series-forecasting-lab](https://github.com/pavanamthomas/time-series-forecasting-lab).

## Citation

See [`CITATION.cff`](CITATION.cff). Licence: MIT, Copyright 2026 Dr. Pavanam Thomas.
