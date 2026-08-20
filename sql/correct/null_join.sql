-- NULL join semantics.
-- customers.segment may be NULL. segment_lookup has no row for 'C'.
-- INNER JOIN drops NULL keys and unmatched 'C'.
-- LEFT JOIN keeps every customer; risk_bucket is NULL when there is no match.
-- SQLite and PostgreSQL both treat NULL = NULL as unknown, not true.

SELECT
    c.customer_id,
    c.segment,
    s.risk_bucket,
    CASE
        WHEN c.segment IS NULL THEN 'null_segment'
        WHEN s.risk_bucket IS NULL THEN 'unmatched_segment'
        ELSE 'matched'
    END AS join_status
FROM customers AS c
LEFT JOIN segment_lookup AS s
    ON s.segment = c.segment
ORDER BY c.customer_id;
