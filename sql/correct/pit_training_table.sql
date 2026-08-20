-- Estimand: X(t) for each prediction row, using only events with
-- timestamp <= cutoff_ts. Label y is joined as the training target,
-- not as a covariate.
--
-- Constructs used: CTE, multi-join, LEFT JOIN, INNER JOIN, GROUP BY,
-- HAVING, CASE, correlated subquery, EXISTS, subquery, LAG (not LEAD),
-- ROW_NUMBER, FIRST_VALUE, LAST_VALUE, running SUM, rolling AVG,
-- PARTITION BY, datetime, NULL handling, conditional aggregation,
-- FILTER (SQLite 3.30+ / PostgreSQL).

WITH hist_txn AS (
    SELECT
        p.prediction_id,
        p.customer_id,
        p.cutoff_ts,
        t.txn_id,
        t.account_id,
        t.txn_ts,
        t.amount,
        t.product_id,
        t.is_sentinel,
        t.channel
    FROM predictions AS p
    LEFT JOIN transactions AS t
        ON t.customer_id = p.customer_id
       AND t.txn_ts <= p.cutoff_ts
),
txn_feat AS (
    SELECT
        prediction_id,
        customer_id,
        cutoff_ts,
        COUNT(txn_id) AS txn_count_all_prior,
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
heavy AS (
    SELECT prediction_id
    FROM hist_txn
    WHERE txn_id IS NOT NULL
    GROUP BY prediction_id
    HAVING SUM(amount) >= 200
),
txn_windows AS (
    SELECT
        prediction_id,
        FIRST_VALUE(product_id) OVER (
            PARTITION BY prediction_id
            ORDER BY txn_ts
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS first_product_id,
        LAST_VALUE(product_id) OVER (
            PARTITION BY prediction_id
            ORDER BY txn_ts
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS last_product_id,
        SUM(amount) OVER (
            PARTITION BY prediction_id
            ORDER BY txn_ts
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_spend,
        AVG(amount) OVER (
            PARTITION BY prediction_id
            ORDER BY txn_ts
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS rolling_3txn_avg,
        ROW_NUMBER() OVER (
            PARTITION BY prediction_id
            ORDER BY txn_ts DESC
        ) AS rn_desc
    FROM hist_txn
    WHERE txn_id IS NOT NULL
),
last_txn_window AS (
    SELECT
        prediction_id,
        first_product_id,
        last_product_id,
        running_spend,
        rolling_3txn_avg
    FROM txn_windows
    WHERE rn_desc = 1
),
sess_feat AS (
    SELECT
        p.prediction_id,
        COUNT(s.session_id) AS n_sessions_30,
        AVG(s.duration_sec) AS mean_session_duration_30,
        SUM(s.pages) AS pages_30
    FROM predictions AS p
    LEFT JOIN sessions AS s
        ON s.customer_id = p.customer_id
       AND s.session_ts <= p.cutoff_ts
       AND s.session_ts > datetime(p.cutoff_ts, '-30 days')
    GROUP BY p.prediction_id
),
event_feat AS (
    SELECT
        p.prediction_id,
        SUM(CASE WHEN e.event_type = 'login' THEN 1 ELSE 0 END) AS n_login_30,
        SUM(CASE WHEN e.event_type = 'view' THEN 1 ELSE 0 END) AS n_view_30,
        SUM(CASE WHEN e.event_type = 'add_to_cart' THEN 1 ELSE 0 END) AS n_cart_30,
        SUM(CASE WHEN e.is_sentinel = 1 THEN 1 ELSE 0 END) AS sentinel_event_count,
        COUNT(DISTINCT e.event_type) AS n_event_types_prior
    FROM predictions AS p
    LEFT JOIN events AS e
        ON e.customer_id = p.customer_id
       AND e.event_ts <= p.cutoff_ts
       AND e.event_ts > datetime(p.cutoff_ts, '-30 days')
    GROUP BY p.prediction_id
),
cat_feat AS (
    SELECT
        p.prediction_id,
        COUNT(DISTINCT pr.category) AS n_distinct_categories
    FROM predictions AS p
    LEFT JOIN transactions AS t
        ON t.customer_id = p.customer_id
       AND t.txn_ts <= p.cutoff_ts
    LEFT JOIN products AS pr
        ON pr.product_id = t.product_id
    GROUP BY p.prediction_id
),
lag_feat AS (
    SELECT
        p.prediction_id,
        p.customer_id,
        p.cutoff_ts,
        o.y,
        o.label_ts,
        LAG(o.y) OVER (PARTITION BY p.customer_id ORDER BY p.cutoff_ts) AS lag_y_raw,
        LAG(o.label_ts) OVER (PARTITION BY p.customer_id ORDER BY p.cutoff_ts) AS lag_label_ts
    FROM predictions AS p
    INNER JOIN outcomes AS o
        ON o.prediction_id = p.prediction_id
)
SELECT
    p.prediction_id,
    p.customer_id,
    p.cutoff_ts,
    lf.y,
    julianday(p.cutoff_ts) - julianday(c.signup_ts) AS tenure_days,
    c.cohort_month,
    c.segment,
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
    sf.mean_session_duration_30,
    COALESCE(ef.n_login_30, 0) AS n_login_30,
    COALESCE(ef.n_view_30, 0) AS n_view_30,
    COALESCE(ef.n_cart_30, 0) AS n_cart_30,
    COALESCE(ef.sentinel_event_count, 0) AS sentinel_event_count,
    COALESCE(ef.n_event_types_prior, 0) AS n_event_types_prior,
    COALESCE(cf.n_distinct_categories, 0) AS n_distinct_categories,
    lw.rolling_3txn_avg,
    lw.running_spend AS running_spend_at_last_txn,
    CASE WHEN hv.prediction_id IS NOT NULL THEN 1 ELSE 0 END AS is_heavy_spender,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM orders AS o
            WHERE o.customer_id = p.customer_id
              AND o.order_ts <= p.cutoff_ts
              AND o.status = 'completed'
        ) THEN 1
        ELSE 0
    END AS has_prior_completed_order,
    (
        SELECT MAX(e.event_ts)
        FROM events AS e
        WHERE e.customer_id = p.customer_id
          AND e.event_ts <= p.cutoff_ts
    ) AS last_event_ts,
    CASE
        WHEN lf.lag_label_ts IS NOT NULL AND lf.lag_label_ts <= p.cutoff_ts
        THEN lf.lag_y_raw
        ELSE NULL
    END AS lag_y
FROM predictions AS p
INNER JOIN customers AS c
    ON c.customer_id = p.customer_id
INNER JOIN txn_feat AS tf
    ON tf.prediction_id = p.prediction_id
LEFT JOIN sess_feat AS sf
    ON sf.prediction_id = p.prediction_id
LEFT JOIN event_feat AS ef
    ON ef.prediction_id = p.prediction_id
LEFT JOIN cat_feat AS cf
    ON cf.prediction_id = p.prediction_id
LEFT JOIN last_txn_window AS lw
    ON lw.prediction_id = p.prediction_id
LEFT JOIN heavy AS hv
    ON hv.prediction_id = p.prediction_id
INNER JOIN lag_feat AS lf
    ON lf.prediction_id = p.prediction_id
ORDER BY p.prediction_id;
