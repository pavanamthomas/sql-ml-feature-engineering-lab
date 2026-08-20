-- Representative point-in-time probe used for EXPLAIN QUERY PLAN.
-- Predicate: customer_id equality and txn_ts <= cutoff.

SELECT
    p.prediction_id,
    p.customer_id,
    COUNT(t.txn_id) AS txn_count_30,
    COALESCE(SUM(t.amount), 0.0) AS spend_30
FROM predictions AS p
LEFT JOIN transactions AS t
    ON t.customer_id = p.customer_id
   AND t.txn_ts <= p.cutoff_ts
   AND t.txn_ts > datetime(p.cutoff_ts, '-30 days')
GROUP BY p.prediction_id, p.customer_id
ORDER BY p.prediction_id;
