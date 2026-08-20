# Flagship: two pipelines, one leak, inflated fit

**Estimand.** For each prediction at cutoff \(t\), \(X(t)\) is a function of
events with timestamp \(\le t\). The label \(y\) is a completed order in
\((t, t+30\text{ days}]\).

**DGP.** Synthetic customers and events, seed 2026. Primary cutoff
`2025-07-01 00:00:00`. After cutoff, the generator plants sentinel
transactions (`is_sentinel = 1`, amount `99999.0`) for known customer
ids and for primary-cutoff positives. Those rows do not exist in
\(\mathcal{H}(t)\).

This note is a laboratory record. It is not a model-validation report
for a real book of customers.

## Two tables that look alike

`sql/correct/pit_training_table.sql` joins history with
`txn_ts <= cutoff_ts` (and the same for sessions and events). Columns
include `txn_count_30`, `spend_30`, `recency_days`, `tenure_days`,
`n_sessions_30`.

`sql/leaky/pit_training_table.sql` uses the same column names. The
transaction join has **no cutoff predicate**. Any transaction for the
customer, including the label window and the sentinels, can enter
`spend_30` because that column is “amount in the last 30 days relative
to cutoff” computed on the unfiltered join — which includes dates
**after** cutoff.

A reviewer who diffs column lists will see almost the same schema. A
reviewer who diffs row counts will see one row per `prediction_id` in
both files. The information sets are not the same.

## Apparent performance

On each table I fit an in-sample logistic regression (standardised
features, `sklearn.linear_model.LogisticRegression`) using the shared
column list. Scoring uses the same rows as the fit. That is deliberate.
The quantity is leakage-driven separability, not generalisation.

Run `python scripts/run_all.py` for the numbers on your machine. This
file does not paste an AUC. The test
`tests/test_flagship.py::test_leaky_auc_exceeds_correct_auc` requires
the leaky in-sample AUC to exceed the correct AUC by more than 0.02 on
this DGP.

That gap is not skill. The leaky `spend_30` can see purchases that
define \(y\), and can see sentinel amounts planted on positives. A
flexible model is not required to harvest that. Logistic regression is
enough.

## How the sentinel test catches it without the classifier

Independently of AUC:

1. Every sentinel row has `txn_ts` strictly after the primary cutoff.
2. On the correct table **at the primary cutoff**, `sentinel_spend = 0`.
   The same planted row is legitimate history at a later cutoff
   (`2025-10-01`). That is point-in-time, not a leak.
3. On the leaky table, known sentinel customers (`1, 2, 3, 7, 11`) have
   `sentinel_spend = 99999.0` at the primary cutoff.

If (2) fails, the “correct” SQL is not correct. If (3) fails, the leaky
SQL is not the leak we intended to study. Neither check inspects
coefficients.

## What I am not claiming

- That the correct AUC is a production number, or that 0.5-plus is
  “good.”
- That sentinels exist in real warehouses. They are canaries.
- That excluding post-cutoff rows is sufficient for a live system with
  late-arriving facts, clock skew, or corrections.
- A causal effect of spending or sessions on orders.

Related: `docs/sql_leakage.md`, `docs/point_in_time_correctness.md`,
`docs/failures_and_corrections.md`.
