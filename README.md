# sql-ml-feature-engineering-lab

[![CI](https://github.com/pavanamthomas/sql-ml-feature-engineering-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/pavanamthomas/sql-ml-feature-engineering-lab/actions)

Point-in-time SQL feature engineering for relational event data, with deliberate leaky queries, future-only sentinels, and independent cross-engine checks.

This repository asks one question: **does a feature use only information that was available at the prediction cutoff?** It is not a beginner JOIN catalogue, a feature-store product, or an empirical study of real customers.

Author: Dr. Pavanam Thomas ([GitHub](https://github.com/pavanamthomas), thomaspavanam@gmail.com).

The object is the information set at a cutoff. Model performance is secondary to whether the feature was legally computable at that time.

## Start here

1. [`FLAGSHIP_POINT_IN_TIME_FAILURE.md`](FLAGSHIP_POINT_IN_TIME_FAILURE.md) — two pipelines with similar columns; one admits future information. A sentinel catches the problem without relying on AUC.
2. [`sql/correct/`](sql/correct/) versus [`sql/leaky/`](sql/leaky/) — inspect the time predicates, not only the SELECT lists.
3. [`docs/cross_engine_parity.md`](docs/cross_engine_parity.md) — deterministic SQLite/DuckDB/Pandas checks on the same point-in-time object.
4. [`docs/failures_and_corrections.md`](docs/failures_and_corrections.md) — failures that tests are required to keep visible.
5. [`tests/test_sentinel.py`](tests/test_sentinel.py), [`tests/test_pit.py`](tests/test_pit.py), [`tests/test_sql_pandas_equality.py`](tests/test_sql_pandas_equality.py), and [`tests/test_cross_engine_parity.py`](tests/test_cross_engine_parity.py) — property checks rather than smoke tests.
6. [`ROADMAP.md`](ROADMAP.md) — remaining bounds, including event time versus ingest time.

Reproduce:

```bash
python -m pip install -e ".[duckdb]"
python -m pytest
python scripts/run_all.py
```

Python 3.11 or newer. SQLite remains the stdlib execution path for the main laboratory. DuckDB now runs in CI as a second engine on a compact deterministic parity fixture.

## Query design

- **Event time at or before cutoff defines the implemented information set.** That is checkable on a known DGP. It is not a full CDC or late-arriving-data story.
- **SQL text is an artefact.** Tests execute the correct and deliberately leaky query files; a reviewer can point to the exact predicate that changes the information set.
- **Future-only sentinels instead of code review alone.** A planted post-cutoff amount of `99999.0` must be absent from correct historical features.
- **Pandas is an independent calculation.** Counts, spend, recency, tenure, and other features are recomputed without parsing the SQL.
- **DuckDB is a second SQL engine, not a badge.** On the parity fixture, SQLite and DuckDB must agree with the independent Pandas result on count, spend, recency, NULL/no-history behavior, and the tested ranking-window semantics.
- **In-sample AUC is only a leakage diagnostic.** It is not reported as out-of-sample skill or as a production benchmark.
- **Query plans are interpreted as plans, not timing claims.** SQLite `EXPLAIN QUERY PLAN` is documented separately; no PostgreSQL optimizer claim is made.

## Designed failures

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

The deliberately leaky paths include joins without time restrictions, post-cutoff label windows, midnight truncation, and future-looking window logic. Details: [`docs/failures_and_corrections.md`](docs/failures_and_corrections.md).

## Three-way parity check

The compact cross-engine fixture contains prediction cutoffs, historical transactions, a no-history customer, and a post-cutoff sentinel transaction. Tests require:

- SQLite result equals DuckDB result for the tested point-in-time features;
- both SQL results equal an independently computed Pandas table;
- customer 1 excludes the `99999.0` future sentinel;
- zero-history rows retain zero aggregates and NULL recency;
- `ROW_NUMBER`, `RANK`, and `DENSE_RANK` preserve the expected tie pattern across engines.

This is intentionally narrower than claiming database equivalence. PostgreSQL-specific behavior, time zones, late-arriving facts, and optimizer semantics remain outside the tested object.

## Reproducibility

```bash
python -m pip install -e ".[duckdb]"
python -m pytest
python scripts/run_all.py
python scripts/generate_data.py   # optional: data/lab.sqlite
```

`scripts/run_all.py` regenerates the flagship AUC figure, summary table, cohort and ranking outputs, and SQLite plan text. The source of truth is the query code plus the tests, not checked-in output files.

CI installs the DuckDB validation extra, runs the full test suite, and runs the reproduction script.

## Known limitations

- The DGP is stylised; it is a procedural test bed, not a model of a real customer system.
- Point-in-time correctness on **event time** is not point-in-time correctness on **ingest time**.
- Time zones are not modelled.
- DuckDB parity covers a deterministic subset, not every SQL file or every dialect feature.
- PostgreSQL-specific execution and query plans are not tested.
- In-sample AUC is not out-of-sample skill and not a causal effect.
- No result here is an empirical finding about real customers.

Data policy: [`docs/data_policy.md`](docs/data_policy.md).

## Repository structure

```text
sql-ml-feature-engineering-lab/
├── FLAGSHIP_POINT_IN_TIME_FAILURE.md
├── sql/correct/
├── sql/leaky/
├── src/sqlfeat/
├── scripts/
├── tests/
├── docs/
└── outputs/
```

Related laboratories: [computational-ml-stem-problem-forge](https://github.com/pavanamthomas/computational-ml-stem-problem-forge), [statistical-reasoning-validation](https://github.com/pavanamthomas/statistical-reasoning-validation), and [time-series-forecasting-lab](https://github.com/pavanamthomas/time-series-forecasting-lab).

## Citation

See [`CITATION.cff`](CITATION.cff). Licence: MIT, Copyright 2026 Dr. Pavanam Thomas.
