-- Referral depth via a recursive CTE.
-- The generator guarantees referred_by < customer_id, so the graph is a DAG.
-- Depth 0 is a root (no referrer). This is the one recursive example.

WITH RECURSIVE referral_tree AS (
    SELECT
        customer_id,
        referred_by,
        0 AS depth,
        customer_id AS root_id
    FROM customers
    WHERE referred_by IS NULL
    UNION ALL
    SELECT
        c.customer_id,
        c.referred_by,
        t.depth + 1 AS depth,
        t.root_id
    FROM customers AS c
    INNER JOIN referral_tree AS t
        ON c.referred_by = t.customer_id
    WHERE t.depth < 12
)
SELECT
    customer_id,
    referred_by,
    depth,
    root_id
FROM referral_tree
ORDER BY customer_id;
