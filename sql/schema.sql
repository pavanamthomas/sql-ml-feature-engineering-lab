-- Relational event schema for the point-in-time laboratory.
-- Timestamps are ISO-8601 TEXT at second precision so SQLite datetime()
-- and julianday() are well-defined. This is the executable dialect.
-- PostgreSQL equivalents: TIMESTAMPTZ, date_trunc, FILTER, DISTINCT ON.
-- See docs/dialect_differences.md.

PRAGMA foreign_keys = ON;

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    signup_ts TEXT NOT NULL,
    referred_by INTEGER,
    cohort_month TEXT NOT NULL,
    country TEXT NOT NULL,
    segment TEXT,
    FOREIGN KEY (referred_by) REFERENCES customers (customer_id)
);

CREATE TABLE accounts (
    account_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    parent_account_id INTEGER,
    opened_ts TEXT NOT NULL,
    account_type TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
    FOREIGN KEY (parent_account_id) REFERENCES accounts (account_id)
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    category TEXT NOT NULL,
    name TEXT NOT NULL
);

CREATE TABLE segment_lookup (
    segment TEXT PRIMARY KEY,
    risk_bucket TEXT NOT NULL
);

CREATE TABLE rank_demo (
    player_id INTEGER PRIMARY KEY,
    player TEXT NOT NULL,
    score INTEGER NOT NULL
);

CREATE TABLE sessions (
    session_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    session_ts TEXT NOT NULL,
    duration_sec INTEGER,
    pages INTEGER,
    device TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

CREATE TABLE events (
    event_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    session_id INTEGER,
    event_ts TEXT NOT NULL,
    event_type TEXT NOT NULL,
    product_id INTEGER,
    is_sentinel INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);

CREATE TABLE transactions (
    txn_id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    product_id INTEGER,
    txn_ts TEXT NOT NULL,
    amount REAL NOT NULL,
    is_sentinel INTEGER NOT NULL DEFAULT 0,
    channel TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES accounts (account_id),
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);

CREATE TABLE transactions_raw (
    raw_id INTEGER PRIMARY KEY,
    txn_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    product_id INTEGER,
    txn_ts TEXT NOT NULL,
    amount REAL NOT NULL,
    ingested_ts TEXT NOT NULL,
    channel TEXT NOT NULL
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    order_ts TEXT NOT NULL,
    amount REAL NOT NULL,
    status TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);

CREATE TABLE predictions (
    prediction_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    cutoff_ts TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

CREATE TABLE outcomes (
    prediction_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    cutoff_ts TEXT NOT NULL,
    label_ts TEXT NOT NULL,
    y INTEGER NOT NULL,
    FOREIGN KEY (prediction_id) REFERENCES predictions (prediction_id),
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);
