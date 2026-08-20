-- Session aggregates in the 30 days ending at cutoff.
-- AVG ignores NULL duration_sec (SQLite / PostgreSQL NULL semantics).

SELECT
    p.prediction_id,
    p.customer_id,
    COUNT(s.session_id) AS n_sessions_30,
    AVG(s.duration_sec) AS mean_session_duration_30,
    SUM(s.pages) AS pages_30
FROM predictions AS p
LEFT JOIN sessions AS s
    ON s.customer_id = p.customer_id
   AND s.session_ts <= p.cutoff_ts
   AND s.session_ts > datetime(p.cutoff_ts, '-30 days')
GROUP BY p.prediction_id, p.customer_id
ORDER BY p.prediction_id;
