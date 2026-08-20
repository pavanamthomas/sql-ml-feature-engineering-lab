-- Transaction counts in the 7 / 30 / 90 day windows ending at cutoff.
-- Time predicate: txn_ts <= cutoff AND txn_ts > cutoff - N days.
-- FILTER is the PostgreSQL-style conditional aggregate; SQLite 3.30+.

SELECT
    p.prediction_id,
    p.customer_id,
    p.cutoff_ts,
    COUNT(t.txn_id) FILTER (
        WHERE t.txn_ts > datetime(p.cutoff_ts, '-7 days')
    ) AS txn_count_7,
    COUNT(t.txn_id) FILTER (
        WHERE t.txn_ts > datetime(p.cutoff_ts, '-30 days')
    ) AS txn_count_30,
    COUNT(t.txn_id) FILTER (
        WHERE t.txn_ts > datetime(p.cutoff_ts, '-90 days')
    ) AS txn_count_90,
    COALESCE(SUM(t.amount) FILTER (WHERE t.is_sentinel = 1), 0.0) AS sentinel_spend
FROM predictions AS p
LEFT JOIN transactions AS t
    ON t.customer_id = p.customer_id
   AND t.txn_ts <= p.cutoff_ts
GROUP BY p.prediction_id, p.customer_id, p.cutoff_ts
ORDER BY p.prediction_id;
