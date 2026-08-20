-- Consecutive transactions via LAG (prior row only).
-- LEAD would look at a later timestamp and is not a valid contemporaneous feature
-- unless that later row is still <= cutoff, which this query does not enforce.

SELECT
    t.txn_id,
    t.customer_id,
    t.txn_ts,
    t.amount,
    LAG(t.amount) OVER (
        PARTITION BY t.customer_id
        ORDER BY t.txn_ts, t.txn_id
    ) AS prev_amount,
    LAG(t.txn_ts) OVER (
        PARTITION BY t.customer_id
        ORDER BY t.txn_ts, t.txn_id
    ) AS prev_txn_ts
FROM transactions AS t
ORDER BY t.customer_id, t.txn_ts, t.txn_id;
