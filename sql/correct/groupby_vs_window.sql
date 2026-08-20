-- GROUP BY vs window on the same transactions.
-- GROUP BY returns one row per customer and discards txn-level amount.
-- The window keeps every transaction and repeats the customer total.

SELECT
    t.txn_id,
    t.customer_id,
    t.amount AS txn_amount,
    SUM(t.amount) OVER (PARTITION BY t.customer_id) AS customer_total_window,
    (
        SELECT SUM(t2.amount)
        FROM transactions AS t2
        WHERE t2.customer_id = t.customer_id
    ) AS customer_total_subquery
FROM transactions AS t
ORDER BY t.customer_id, t.txn_id;
