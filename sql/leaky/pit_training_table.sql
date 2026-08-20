-- Leaky training table: same column names as the correct query, different
-- information set. Transactions are joined without a cutoff predicate, so
-- post-cutoff spend, sentinels, and the label window enter the covariates.
-- LEAD(y) is included as a named feature. That is target leakage for any
-- customer with a later prediction.

WITH hist_txn AS (
    SELECT
        p.prediction_id,
        p.customer_id,
        p.cutoff_ts,
        t.txn_id,
        t.txn_ts,
        t.amount,
        t.product_id,
        t.is_sentinel
    FROM predictions AS p
    LEFT JOIN transactions AS t
        ON t.customer_id = p.customer_id
),
txn_feat AS (
    SELECT
        prediction_id,
        customer_id,
        cutoff_ts,
        SUM(CASE WHEN txn_id IS NOT NULL AND txn_ts > datetime(cutoff_ts, '-7 days') THEN 1 ELSE 0 END) AS txn_count_7,
        SUM(CASE WHEN txn_id IS NOT NULL AND txn_ts > datetime(cutoff_ts, '-30 days') THEN 1 ELSE 0 END) AS txn_count_30,
        SUM(CASE WHEN txn_id IS NOT NULL AND txn_ts > datetime(cutoff_ts, '-90 days') THEN 1 ELSE 0 END) AS txn_count_90,
        COALESCE(SUM(amount) FILTER (WHERE txn_ts > datetime(cutoff_ts, '-7 days')), 0.0) AS spend_7,
        COALESCE(SUM(amount) FILTER (WHERE txn_ts > datetime(cutoff_ts, '-30 days')), 0.0) AS spend_30,
        COALESCE(SUM(amount) FILTER (WHERE txn_ts > datetime(cutoff_ts, '-90 days')), 0.0) AS spend_90,
        COALESCE(SUM(CASE WHEN is_sentinel = 1 THEN amount ELSE 0 END), 0.0) AS sentinel_spend,
        SUM(CASE WHEN is_sentinel = 1 THEN 1 ELSE 0 END) AS sentinel_txn_count,
        MAX(txn_ts) AS last_txn_ts
    FROM hist_txn
    GROUP BY prediction_id, customer_id, cutoff_ts
),
sess_feat AS (
    SELECT
        p.prediction_id,
        COUNT(s.session_id) AS n_sessions_30
    FROM predictions AS p
    LEFT JOIN sessions AS s
        ON s.customer_id = p.customer_id
       AND s.session_ts > datetime(p.cutoff_ts, '-30 days')
    GROUP BY p.prediction_id
),
lead_feat AS (
    SELECT
        p.prediction_id,
        LEAD(o.y) OVER (
            PARTITION BY p.customer_id
            ORDER BY p.cutoff_ts
        ) AS lead_y
    FROM predictions AS p
    INNER JOIN outcomes AS o
        ON o.prediction_id = p.prediction_id
)
SELECT
    p.prediction_id,
    p.customer_id,
    p.cutoff_ts,
    o.y,
    julianday(p.cutoff_ts) - julianday(c.signup_ts) AS tenure_days,
    tf.txn_count_7,
    tf.txn_count_30,
    tf.txn_count_90,
    tf.spend_7,
    tf.spend_30,
    tf.spend_90,
    CASE
        WHEN tf.last_txn_ts IS NULL THEN NULL
        ELSE julianday(p.cutoff_ts) - julianday(tf.last_txn_ts)
    END AS recency_days,
    tf.sentinel_spend,
    tf.sentinel_txn_count,
    COALESCE(sf.n_sessions_30, 0) AS n_sessions_30,
    lf.lead_y
FROM predictions AS p
INNER JOIN customers AS c
    ON c.customer_id = p.customer_id
INNER JOIN outcomes AS o
    ON o.prediction_id = p.prediction_id
INNER JOIN txn_feat AS tf
    ON tf.prediction_id = p.prediction_id
LEFT JOIN sess_feat AS sf
    ON sf.prediction_id = p.prediction_id
LEFT JOIN lead_feat AS lf
    ON lf.prediction_id = p.prediction_id
ORDER BY p.prediction_id;
