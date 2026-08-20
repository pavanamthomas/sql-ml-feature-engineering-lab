-- Collapsed customer totals. Compare row counts to groupby_vs_window.sql.

SELECT
    customer_id,
    COUNT(*) AS n_txn,
    SUM(amount) AS customer_total
FROM transactions
GROUP BY customer_id
HAVING COUNT(*) >= 1
ORDER BY customer_id;
