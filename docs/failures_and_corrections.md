# Failures and corrections

Leakage and grain mistakes I keep around. A passing test often means the
wrong query still misbehaves on a known DGP.

**20 Aug — join on `customer_id` only.** Planted post-cutoff sentinels
enter `spend_30`. The check is `sentinel_spend > 0` on the leaky table,
not AUC. Fix is `txn_ts <= cutoff_ts` on the join. `tests/test_sentinel.py`.
Late-arriving rows with old event times are still not modelled.

**LEAD of amount at the last history row.** Next timestamp is after cutoff
for active customers (`lead_txn_ts > cutoff_ts`). Do not use LEAD as a
contemporaneous feature.
`tests/test_cases.py::test_case_e_lead_sees_future_timestamps`.
LEAD inside a pre-filtered history is still future *within the window*.

**Date truncation at a midnight cutoff.** `date(txn_ts) <= date(cutoff_ts)`
lets afternoon same-day txns leak. Compare timestamps, not dates.
`tests/test_sentinel.py::test_date_truncation_includes_same_day_after_midnight_cutoff`.
Time zone conversions are not in the DGP.

**Rolling window `txn_ts < cutoff + 1 day`.** Label-day rows enter spend.
Close the window at `cutoff_ts`.
`tests/test_sentinel.py::test_label_day_window_includes_afternoon_same_day`.

**GROUP BY customer totals as a “feature table” at txn grain.** One row
per customer; txn amount is gone. Window or join back to the grain you
need. `tests/test_cases.py::test_case_a_window_keeps_txn_grain`.

**RANK on tied scores treated as a unique key.** Ties share RANK;
ROW_NUMBER does not. Choose the ranking that matches the estimand.
`tests/test_ranking.py`. Business tie-break rules are not specified here.

**INNER JOIN `segment_lookup`.** NULL segment and unmatched `C` drop.
LEFT keeps n_customers; INNER is smaller. LEFT JOIN + explicit NULL
status. `tests/test_null_joins.py`. Dropping unmatched might be intended
in some product; it is not the PIT object here.

**Leaky training table (flagship).** Fit logistic on the leaky table and
in-sample AUC rises. Fit on the PIT table; treat leaky AUC as a bug.
`tests/test_flagship.py`. Out-of-sample behaviour on a real population is
not a result of this lab.

**24 Aug — DuckDB on the compact fixture.** Matching SQL text across
SQLite and DuckDB is not enough if both engines are given the same invalid
information set. The independent Pandas route and the `99999.0` sentinel
are retained for that reason. Postgres is still not in CI.

Process: `docs/lab_process.md`. Flagship: `FLAGSHIP_POINT_IN_TIME_FAILURE.md`.
