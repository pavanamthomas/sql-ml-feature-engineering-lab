-- Join every transaction for the customer, with no time predicate.
-- Sentinel spend is then a near-perfect canary for y=1 primary rows.

SELECT
    p.prediction_id,
    p.customer_id,
    p.cutoff_ts,
    COUNT(t.txn_id) AS txn_count_all_time,
    COALESCE(SUM(t.amount), 0.0) AS spend_all_time,
    COALESCE(SUM(CASE WHEN t.is_sentinel = 1 THEN t.amount ELSE 0 END), 0.0) AS sentinel_spend,
    SUM(CASE WHEN t.is_sentinel = 1 THEN 1 ELSE 0 END) AS sentinel_txn_count
FROM predictions AS p
LEFT JOIN transactions AS t
    ON t.customer_id = p.customer_id
GROUP BY p.prediction_id, p.customer_id, p.cutoff_ts
ORDER BY p.prediction_id;
