# Failures and corrections

The laboratory keeps leakage and grain mistakes visible. A “successful”
test here often means the **wrong query still misbehaves** under a known DGP.

| What was tried | How it failed | Diagnostic | Correction | Locked by | What remains unknown |
| --- | --- | --- | --- | --- | --- |
| Join `transactions` on `customer_id` only | Planted post-cutoff sentinels enter `spend_30` | `sentinel_spend > 0` on leaky table | `txn_ts <= cutoff_ts` on the join | `tests/test_sentinel.py` | Late-arriving rows with old event times |
| `LEAD(amount)` at last history row | Next timestamp is after cutoff for active customers | `lead_txn_ts > cutoff_ts` | Do not use LEAD as a contemporaneous feature | `tests/test_cases.py::test_case_e_lead_sees_future_timestamps` | LEAD inside a pre-filtered history is still future *within the window* |
| `date(txn_ts) <= date(cutoff_ts)` at midnight cutoff | Afternoon same-day txns leak | `n_after_cutoff_included > 0` | Compare timestamps, not dates | `tests/test_sentinel.py::test_date_truncation_includes_same_day_after_midnight_cutoff` | Time zone conversions |
| Rolling window `txn_ts < cutoff + 1 day` | Label-day rows enter spend | `n_same_day_after_cutoff > 0` | Close the window at `cutoff_ts` | `tests/test_sentinel.py::test_label_day_window_includes_afternoon_same_day` | Event time vs decision time |
| GROUP BY customer totals as a “feature table” at txn grain | One row per customer; txn amount is gone | window rows = n_txn; group rows = n_customers | Window or join back to the grain you need | `tests/test_cases.py::test_case_a_window_keeps_txn_grain` | Whether the model wanted customer grain |
| RANK on tied scores treated as a unique key | Ties share RANK; ROW_NUMBER does not | known `rank_demo` table | Choose the ranking that matches the estimand | `tests/test_ranking.py` | Business tie-break rules |
| INNER JOIN `segment_lookup` | NULL segment and unmatched `C` drop | LEFT keeps n_customers; INNER smaller | LEFT JOIN + explicit NULL status | `tests/test_null_joins.py` | Whether dropping unmatched is intended |
| Fit logistic on the leaky table | In-sample AUC rises | flagship gap | Fit on the PIT table; treat leaky AUC as a bug | `tests/test_flagship.py` | Out-of-sample behaviour on a real population |

Process: `docs/lab_process.md`. Flagship narrative: `FLAGSHIP_POINT_IN_TIME_FAILURE.md`.
