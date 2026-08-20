-- Recency: days since last transaction at or before cutoff (NULL if none).
-- Tenure: days since signup. No-history is not recency zero.

SELECT
    p.prediction_id,
    p.customer_id,
    p.cutoff_ts,
    julianday(p.cutoff_ts) - julianday(c.signup_ts) AS tenure_days,
    CASE
        WHEN last_txn.last_ts IS NULL THEN NULL
        ELSE julianday(p.cutoff_ts) - julianday(last_txn.last_ts)
    END AS recency_days
FROM predictions AS p
INNER JOIN customers AS c
    ON c.customer_id = p.customer_id
LEFT JOIN (
    SELECT
        p2.prediction_id,
        MAX(t.txn_ts) AS last_ts
    FROM predictions AS p2
    LEFT JOIN transactions AS t
        ON t.customer_id = p2.customer_id
       AND t.txn_ts <= p2.cutoff_ts
    GROUP BY p2.prediction_id
) AS last_txn
    ON last_txn.prediction_id = p.prediction_id
ORDER BY p.prediction_id;
