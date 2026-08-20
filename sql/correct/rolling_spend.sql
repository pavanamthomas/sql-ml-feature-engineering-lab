-- Calendar rolling spend in 7 / 30 / 90 day windows ending at cutoff.
-- This is not a ROWS window: a three-row frame is not 30 days.

SELECT
    p.prediction_id,
    p.customer_id,
    p.cutoff_ts,
    COALESCE(SUM(t.amount) FILTER (
        WHERE t.txn_ts > datetime(p.cutoff_ts, '-7 days')
    ), 0.0) AS spend_7,
    COALESCE(SUM(t.amount) FILTER (
        WHERE t.txn_ts > datetime(p.cutoff_ts, '-30 days')
    ), 0.0) AS spend_30,
    COALESCE(SUM(t.amount) FILTER (
        WHERE t.txn_ts > datetime(p.cutoff_ts, '-90 days')
    ), 0.0) AS spend_90,
    COALESCE(SUM(t.amount) FILTER (WHERE t.is_sentinel = 1), 0.0) AS sentinel_spend
FROM predictions AS p
LEFT JOIN transactions AS t
    ON t.customer_id = p.customer_id
   AND t.txn_ts <= p.cutoff_ts
GROUP BY p.prediction_id, p.customer_id, p.cutoff_ts
ORDER BY p.prediction_id;
