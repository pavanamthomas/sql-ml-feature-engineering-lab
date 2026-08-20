# Point-in-time correctness

A feature for a decision at time \(t\) may use information available at
\(t\). In this laboratory that is operationalised as **event timestamps
\(\le\) `cutoff_ts`**. That is a strong and checkable rule. It is not
the only rule a warehouse might need (ingest time, corrections, time
zones).

## Information set

Let \(\mathcal{H}(t) = \{ \text{rows } r : r.\text{ts} \le t \}\).
The correct training table is \(X_i = f(\mathcal{H}(t_i))\) with label
\(y_i\) from \((t_i, t_i + 30\text{d}]\).

The leaky table uses a strictly larger set: all transactions for the
customer, or all transactions with `ts < t + 30d`, or `LEAD` of a later
row.

## Filter first, then window

Window functions do not know about cutoffs. If you compute
`LAST_VALUE(amount)` on the full transaction table and then join to
predictions, the last value can be in the future. The correct pattern:

1. Restrict history with `txn_ts <= cutoff_ts` (in a JOIN or a CTE).
2. Then apply `ROW_NUMBER`, running sums, `FIRST_VALUE` / `LAST_VALUE`.

`LAST_VALUE` still needs an explicit frame
`ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`. The default
frame ends at the current row, so “last value” is the current row.

## Same calendar day

The primary cutoff is midnight. Transactions at 16:30 the same day are
after \(t\). A predicate `date(txn_ts) <= date(cutoff_ts)` includes them.
That leak is small in amount and large in principle. It is planted
deliberately for fifty customers.

## Label window

\(y = 1\) if a completed order falls in \((t, t+30\text{d}]\). A spend
feature that uses `txn_ts <= t + 30 days` is almost a restatement of the
label once orders and transactions coincide in calendar time. That is
target leakage, not “more history.”

## Independent check

Planted sentinels exist only after the primary cutoff. Correct SQL must
show `sentinel_spend = 0`. Leaky SQL must show `SENTINEL_AMOUNT` for
known customer ids. Tests: `tests/test_sentinel.py`,
`tests/test_pit.py`. Narrative: `FLAGSHIP_POINT_IN_TIME_FAILURE.md`.
