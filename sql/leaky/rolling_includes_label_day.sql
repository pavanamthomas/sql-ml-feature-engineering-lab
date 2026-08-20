-- Rolling window that includes the label day / label horizon.
-- Using datetime(cutoff, '+1 day') pulls in same-calendar-day rows after
-- a midnight cutoff and the first day of the outcome window.

SELECT
    p.prediction_id,
    p.customer_id,
    p.cutoff_ts,
    COALESCE(SUM(t.amount) FILTER (
        WHERE t.txn_ts > datetime(p.cutoff_ts, '-30 days')
          AND t.txn_ts < datetime(p.cutoff_ts, '+1 day')
    ), 0.0) AS spend_30_including_label_day,
    COALESCE(SUM(t.amount) FILTER (WHERE t.is_sentinel = 1), 0.0) AS sentinel_spend,
    SUM(CASE WHEN date(t.txn_ts) = date(p.cutoff_ts) AND t.txn_ts > p.cutoff_ts THEN 1 ELSE 0 END) AS n_same_day_after_cutoff
FROM predictions AS p
LEFT JOIN transactions AS t
    ON t.customer_id = p.customer_id
   AND t.txn_ts < datetime(p.cutoff_ts, '+1 day')
GROUP BY p.prediction_id, p.customer_id, p.cutoff_ts
ORDER BY p.prediction_id;
