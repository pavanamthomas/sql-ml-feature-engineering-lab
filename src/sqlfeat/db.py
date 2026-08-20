"""SQLite connection helpers for the laboratory.

The executable dialect is SQLite from the Python standard library so
CI does not need a server. Queries are written in a PostgreSQL-like
style where SQLite allows it. Dialect gaps are documented, not hidden.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from sqlfeat.paths import load_sql


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with foreign keys enabled.

    Parameters
    ----------
    path
        File path, or ``None`` for an in-memory database.
    """
    target = ":memory:" if path is None else str(path)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def apply_schema(conn: sqlite3.Connection) -> None:
    """Create empty tables from ``sql/schema.sql``."""
    conn.executescript(load_sql("schema.sql"))
    conn.commit()


def apply_indexes(conn: sqlite3.Connection) -> None:
    """Create laboratory indexes from ``sql/indexes.sql``."""
    conn.executescript(load_sql("indexes.sql"))
    conn.commit()


def drop_laboratory_indexes(conn: sqlite3.Connection) -> None:
    """Drop indexes created by ``apply_indexes`` (for EXPLAIN comparisons)."""
    names = [
        "idx_txn_customer_ts",
        "idx_txn_ts",
        "idx_events_customer_ts",
        "idx_sessions_customer_ts",
        "idx_orders_customer_ts",
        "idx_pred_customer_cutoff",
        "idx_accounts_customer",
    ]
    for name in names:
        conn.execute(f"DROP INDEX IF EXISTS {name}")
    conn.commit()


def read_sql(conn: sqlite3.Connection, relative: str) -> pd.DataFrame:
    """Execute a SELECT file and return a DataFrame."""
    return pd.read_sql_query(load_sql(relative), conn)


def table_count(conn: sqlite3.Connection, table: str) -> int:
    """Return ``COUNT(*)`` for a table name.

    Table names are laboratory-controlled identifiers, not user input.
    """
    if not table.replace("_", "").isalnum():
        raise ValueError(f"refusing to count non-identifier table name: {table!r}")
    row = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
    return int(row["n"])
