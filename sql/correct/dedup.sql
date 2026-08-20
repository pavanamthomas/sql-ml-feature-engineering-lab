-- Dedup ingest duplicates with ROW_NUMBER.
-- PostgreSQL DISTINCT ON (txn_id) is the short form; SQLite has no DISTINCT ON.
-- Keep the latest ingested_ts. Ties on ingest are broken by raw_id DESC.

SELECT
    txn_id,
    account_id,
    customer_id,
    product_id,
    txn_ts,
    amount,
    ingested_ts,
    channel
FROM (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY txn_id
            ORDER BY ingested_ts DESC, raw_id DESC
        ) AS rn
    FROM transactions_raw AS r
) AS ranked
WHERE rn = 1
ORDER BY txn_id;
