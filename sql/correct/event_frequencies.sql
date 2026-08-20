-- Prior event frequencies in the 30 days ending at cutoff.
-- Conditional aggregation, not a pivot operator.

SELECT
    p.prediction_id,
    p.customer_id,
    SUM(CASE WHEN e.event_type = 'login' THEN 1 ELSE 0 END) AS n_login_30,
    SUM(CASE WHEN e.event_type = 'view' THEN 1 ELSE 0 END) AS n_view_30,
    SUM(CASE WHEN e.event_type = 'add_to_cart' THEN 1 ELSE 0 END) AS n_cart_30,
    SUM(CASE WHEN e.event_type = 'purchase' THEN 1 ELSE 0 END) AS n_purchase_event_30,
    SUM(CASE WHEN e.is_sentinel = 1 THEN 1 ELSE 0 END) AS sentinel_event_count
FROM predictions AS p
LEFT JOIN events AS e
    ON e.customer_id = p.customer_id
   AND e.event_ts <= p.cutoff_ts
   AND e.event_ts > datetime(p.cutoff_ts, '-30 days')
GROUP BY p.prediction_id, p.customer_id
ORDER BY p.prediction_id;
