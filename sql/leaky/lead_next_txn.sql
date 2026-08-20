-- LEAD looks at the next transaction after the current row.
-- At a prediction cutoff this is a future amount unless the next row
-- is still <= cutoff. This query does not enforce that, and is joined
-- back to predictions by customer only.

WITH ordered AS (
    SELECT
        t.customer_id,
        t.txn_id,
        t.txn_ts,
        t.amount,
        t.is_sentinel,
        LEAD(t.amount) OVER (
            PARTITION BY t.customer_id
            ORDER BY t.txn_ts, t.txn_id
        ) AS next_amount,
        LEAD(t.txn_ts) OVER (
            PARTITION BY t.customer_id
            ORDER BY t.txn_ts, t.txn_id
        ) AS next_txn_ts,
        LEAD(t.is_sentinel) OVER (
            PARTITION BY t.customer_id
            ORDER BY t.txn_ts, t.txn_id
        ) AS next_is_sentinel
    FROM transactions AS t
),
at_cutoff AS (
    SELECT
        p.prediction_id,
        p.customer_id,
        p.cutoff_ts,
        o.next_amount,
        o.next_txn_ts,
        o.next_is_sentinel,
        ROW_NUMBER() OVER (
            PARTITION BY p.prediction_id
            ORDER BY o.txn_ts DESC, o.txn_id DESC
        ) AS rn
    FROM predictions AS p
    LEFT JOIN ordered AS o
        ON o.customer_id = p.customer_id
       AND o.txn_ts <= p.cutoff_ts
)
SELECT
    prediction_id,
    customer_id,
    cutoff_ts,
    next_amount AS lead_amount,
    next_txn_ts AS lead_txn_ts,
    COALESCE(next_is_sentinel, 0) AS lead_is_sentinel
FROM at_cutoff
WHERE rn = 1
ORDER BY prediction_id;
