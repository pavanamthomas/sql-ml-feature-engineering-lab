"""Schema invariants: row-count bands, primary-key uniqueness, FK-friendly IDs."""

from __future__ import annotations

import pandas as pd

from sqlfeat.db import table_count
from sqlfeat.generate import N_CUSTOMERS, N_PRODUCTS


TABLES = (
    "customers",
    "accounts",
    "products",
    "sessions",
    "events",
    "transactions",
    "transactions_raw",
    "orders",
    "predictions",
    "outcomes",
    "segment_lookup",
    "rank_demo",
)


def test_expected_customer_and_product_counts(conn) -> None:
    assert table_count(conn, "customers") == N_CUSTOMERS
    assert table_count(conn, "products") == N_PRODUCTS
    assert table_count(conn, "predictions") >= N_CUSTOMERS
    assert table_count(conn, "outcomes") == table_count(conn, "predictions")


def test_row_counts_in_laboratory_band(conn) -> None:
    assert 500 <= table_count(conn, "accounts") <= 2000
    assert 2000 <= table_count(conn, "sessions") <= 20_000
    assert 4000 <= table_count(conn, "events") <= 80_000
    assert 2000 <= table_count(conn, "transactions") <= 20_000
    assert 400 <= table_count(conn, "orders") <= 10_000
    assert table_count(conn, "transactions_raw") >= table_count(conn, "transactions")


def test_primary_keys_unique(conn) -> None:
    keys = {
        "customers": "customer_id",
        "accounts": "account_id",
        "products": "product_id",
        "sessions": "session_id",
        "events": "event_id",
        "transactions": "txn_id",
        "transactions_raw": "raw_id",
        "orders": "order_id",
        "predictions": "prediction_id",
        "outcomes": "prediction_id",
        "rank_demo": "player_id",
        "segment_lookup": "segment",
    }
    for table, pk in keys.items():
        n = table_count(conn, table)
        n_distinct = int(
            pd.read_sql_query(f"SELECT COUNT(DISTINCT {pk}) AS n FROM {table}", conn)["n"].iloc[0]
        )
        assert n == n_distinct, f"{table}.{pk} is not unique"


def test_all_tables_present(conn) -> None:
    names = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    assert set(TABLES) <= names
