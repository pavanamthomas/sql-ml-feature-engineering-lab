-- EXISTS: at least one completed order at or before cutoff.
-- Correlated subquery: last prior transaction timestamp.

SELECT
    p.prediction_id,
    p.customer_id,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM orders AS o
            WHERE o.customer_id = p.customer_id
              AND o.order_ts <= p.cutoff_ts
              AND o.status = 'completed'
        ) THEN 1
        ELSE 0
    END AS has_prior_completed_order,
    (
        SELECT MAX(t.txn_ts)
        FROM transactions AS t
        WHERE t.customer_id = p.customer_id
          AND t.txn_ts <= p.cutoff_ts
    ) AS last_txn_ts
FROM predictions AS p
ORDER BY p.prediction_id;
