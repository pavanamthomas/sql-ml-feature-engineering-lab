-- Lagged outcome: previous prediction's label, only if that label was
-- already observed by the current cutoff. LEAD is not selected here.

SELECT
    p.prediction_id,
    p.customer_id,
    p.cutoff_ts,
    o.y,
    LAG(o.y) OVER (
        PARTITION BY p.customer_id
        ORDER BY p.cutoff_ts
    ) AS lag_y_raw,
    LAG(o.label_ts) OVER (
        PARTITION BY p.customer_id
        ORDER BY p.cutoff_ts
    ) AS lag_label_ts,
    CASE
        WHEN LAG(o.label_ts) OVER (
            PARTITION BY p.customer_id
            ORDER BY p.cutoff_ts
        ) <= p.cutoff_ts
        THEN LAG(o.y) OVER (
            PARTITION BY p.customer_id
            ORDER BY p.cutoff_ts
        )
        ELSE NULL
    END AS lag_y
FROM predictions AS p
INNER JOIN outcomes AS o
    ON o.prediction_id = p.prediction_id
ORDER BY p.customer_id, p.cutoff_ts;
