# sql-ml-feature-engineering-lab

[![CI](https://github.com/pavanamthomas/sql-ml-feature-engineering-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/pavanamthomas/sql-ml-feature-engineering-lab/actions)

I care whether a feature uses only information that existed at the prediction cutoff. Not a JOIN tutorial, not a feature store, not a study of real customers.

Two pipelines with similar columns, one of which admits future information: [`FLAGSHIP_POINT_IN_TIME_FAILURE.md`](FLAGSHIP_POINT_IN_TIME_FAILURE.md). A planted post-cutoff amount of `99999.0` has to be absent from the correct historical features. I do not use AUC as the leak detector.

Correct vs leaky SQL: [`sql/correct/`](sql/correct/) and [`sql/leaky/`](sql/leaky/). Look at the time predicates, not only the SELECT lists. Pandas recomputes counts, spend, recency, tenure without parsing the SQL. DuckDB is a second engine on a compact fixture — not a badge. [`docs/cross_engine_parity.md`](docs/cross_engine_parity.md), [`docs/failures_and_corrections.md`](docs/failures_and_corrections.md).

```bash
python -m pip install -e ".[duckdb]"
python -m pytest
python scripts/run_all.py
```

Python 3.11+. SQLite is the stdlib path and the tests that do not need DuckDB run after `pip install -e .`. The DuckDB comparisons need the extra; they are skipped if it is not installed. CI installs `.[duckdb]`.

## Query design

Event time at or before cutoff is the information set I actually check. That is not a CDC or late-arriving-data story. SQL files are artefacts: tests execute the correct and the deliberately leaky ones.

In-sample AUC is only a leakage diagnostic. I do not report it as out-of-sample skill. Query plans are plans, not timing claims — SQLite `EXPLAIN QUERY PLAN` is documented separately; no PostgreSQL optimizer claim.

| Case | What goes wrong |
| --- | --- |
| GROUP BY vs window | Customer totals destroy transaction-level amount |
| Deduplication | Wrong ordering keeps the wrong version of a duplicate |
| Cohort buckets | Calendar grouping is not a causal retention estimate |
| Ranking ties | `ROW_NUMBER`, `RANK`, and `DENSE_RANK` encode different tie semantics |
| LAG vs LEAD | `LEAD` can expose a transaction after prediction time |
| Missing cutoff predicate | Joining only on customer admits future rows |
| Date truncation | Same-day events after the cutoff clock time can slip in |
| Cross-engine parity | Matching syntax is insufficient; the computed object must agree |

Sentinel, PIT, Pandas equality, and engine checks: [`tests/test_sentinel.py`](tests/test_sentinel.py), [`tests/test_pit.py`](tests/test_pit.py), [`tests/test_sql_pandas_equality.py`](tests/test_sql_pandas_equality.py), [`tests/test_cross_engine_parity.py`](tests/test_cross_engine_parity.py).

The compact fixture has prediction cutoffs, historical transactions, a no-history customer, and a post-cutoff sentinel. SQLite has to equal DuckDB; both have to equal Pandas; customer 1 excludes `99999.0`; zero-history rows keep zero aggregates and NULL recency; the three ranking functions keep the expected tie pattern. Narrower than database equivalence. Postgres, time zones, late-arriving facts, and optimizer semantics are outside.

`scripts/run_all.py` regenerates the flagship AUC figure, summary table, cohort and ranking outputs, and SQLite plan text. Optional: `python scripts/generate_data.py` writes `data/lab.sqlite`.

## Limits

Stylised DGP. Event-time PIT is not ingest-time PIT. Time zones are not modelled. DuckDB parity is a deterministic subset, not every SQL file. In-sample AUC is not skill and not a causal effect. Data policy: [`docs/data_policy.md`](docs/data_policy.md). Open list: [`ROADMAP.md`](ROADMAP.md).

Independent-check discipline I reuse on the sentinels: [computational-ml-stem-problem-forge](https://github.com/pavanamthomas/computational-ml-stem-problem-forge).

Pavanam Thomas
