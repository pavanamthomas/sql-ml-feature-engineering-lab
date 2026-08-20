-- Signup-month cohort and a retention-style activity table.
-- Activity month uses strftime; PostgreSQL would use date_trunc('month', ts).
-- A customer is retained in month m if they have a session in that month.

WITH signup AS (
    SELECT
        customer_id,
        strftime('%Y-%m', signup_ts) AS cohort_month
    FROM customers
),
activity AS (
    SELECT DISTINCT
        customer_id,
        strftime('%Y-%m', session_ts) AS activity_month
    FROM sessions
)
SELECT
    s.cohort_month,
    a.activity_month,
    COUNT(*) AS n_active,
    COUNT(*) * 1.0 / FIRST_VALUE(COUNT(*)) OVER (
        PARTITION BY s.cohort_month
        ORDER BY a.activity_month
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS retention_vs_first_observed_month
FROM signup AS s
INNER JOIN activity AS a
    ON a.customer_id = s.customer_id
GROUP BY s.cohort_month, a.activity_month
ORDER BY s.cohort_month, a.activity_month;
