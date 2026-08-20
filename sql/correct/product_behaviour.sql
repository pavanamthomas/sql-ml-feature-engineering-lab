-- Product / category behaviour at or before cutoff.
-- Multi-join: predictions, transactions, products.

SELECT
    p.prediction_id,
    p.customer_id,
    COUNT(DISTINCT pr.category) AS n_distinct_categories,
    COUNT(t.txn_id) AS n_txn_with_product_join
FROM predictions AS p
LEFT JOIN transactions AS t
    ON t.customer_id = p.customer_id
   AND t.txn_ts <= p.cutoff_ts
LEFT JOIN products AS pr
    ON pr.product_id = t.product_id
GROUP BY p.prediction_id, p.customer_id
ORDER BY p.prediction_id;
