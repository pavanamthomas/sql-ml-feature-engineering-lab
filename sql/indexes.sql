-- Indexes used by the point-in-time feature queries.
-- Create these after loading data. docs/query_performance.md records
-- EXPLAIN QUERY PLAN output with and without them. No latency numbers.

CREATE INDEX IF NOT EXISTS idx_txn_customer_ts
    ON transactions (customer_id, txn_ts);

CREATE INDEX IF NOT EXISTS idx_txn_ts
    ON transactions (txn_ts);

CREATE INDEX IF NOT EXISTS idx_events_customer_ts
    ON events (customer_id, event_ts);

CREATE INDEX IF NOT EXISTS idx_sessions_customer_ts
    ON sessions (customer_id, session_ts);

CREATE INDEX IF NOT EXISTS idx_orders_customer_ts
    ON orders (customer_id, order_ts);

CREATE INDEX IF NOT EXISTS idx_pred_customer_cutoff
    ON predictions (customer_id, cutoff_ts);

CREATE INDEX IF NOT EXISTS idx_accounts_customer
    ON accounts (customer_id);
