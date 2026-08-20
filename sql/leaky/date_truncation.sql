-- Date-truncated join: date(txn_ts) <= date(cutoff_ts) includes afternoon
-- transactions on the cutoff calendar day when cutoff is midnight.

SELECT
    p.prediction_id,
    p.customer_id,
    p.cutoff_ts,
    COUNT(t.txn_id) AS txn_count_date_truncated,
    COALESCE(SUM(CASE WHEN t.is_sentinel = 1 THEN t.amount ELSE 0 END), 0.0) AS sentinel_spend,
    SUM(CASE WHEN t.txn_ts > p.cutoff_ts THEN 1 ELSE 0 END) AS n_after_cutoff_included
FROM predictions AS p
LEFT JOIN transactions AS t
    ON t.customer_id = p.customer_id
   AND date(t.txn_ts) <= date(p.cutoff_ts)
GROUP BY p.prediction_id, p.customer_id, p.cutoff_ts
ORDER BY p.prediction_id;
