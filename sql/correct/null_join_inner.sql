-- INNER JOIN counterpart of null_join.sql. Drops NULL and unmatched segments.

SELECT
    c.customer_id,
    c.segment,
    s.risk_bucket
FROM customers AS c
INNER JOIN segment_lookup AS s
    ON s.segment = c.segment
ORDER BY c.customer_id;
