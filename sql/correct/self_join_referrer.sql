-- Self-join on customers: referrer attributes at the referred customer's
-- signup. This is not a feature of the referee's future activity.

SELECT
    c.customer_id,
    c.signup_ts,
    c.referred_by,
    r.cohort_month AS referrer_cohort_month,
    r.country AS referrer_country
FROM customers AS c
LEFT JOIN customers AS r
    ON r.customer_id = c.referred_by
ORDER BY c.customer_id;
