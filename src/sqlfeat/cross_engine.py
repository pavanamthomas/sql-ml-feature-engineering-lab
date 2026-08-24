"""Cross-engine point-in-time checks on one deterministic relational fixture.

This module is intentionally small.  It does not claim that SQLite and DuckDB
are interchangeable databases.  It asks a narrower question: given the same
prediction cutoffs and transaction rows, do both engines produce the same
point-in-time feature table once their date-difference syntax is made explicit?
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ParityFixture:
    predictions: pd.DataFrame
    transactions: pd.DataFrame


def build_fixture() -> ParityFixture:
    """Return rows containing a planted post-cutoff sentinel transaction."""
    predictions = pd.DataFrame(
        [
            ("p1", 1, "2026-01-10 00:00:00"),
            ("p2", 2, "2026-01-10 00:00:00"),
            ("p3", 3, "2026-01-10 00:00:00"),
        ],
        columns=["prediction_id", "customer_id", "cutoff"],
    )
    transactions = pd.DataFrame(
        [
            ("t1", 1, "2026-01-01 00:00:00", 10.0),
            ("t2", 1, "2026-01-09 00:00:00", 20.0),
            # Deliberately future-only. A correct point-in-time query excludes it.
            ("sentinel", 1, "2026-01-11 00:00:00", 99999.0),
            ("t4", 2, "2026-01-05 00:00:00", 7.5),
        ],
        columns=["txn_id", "customer_id", "txn_ts", "amount"],
    )
    return ParityFixture(predictions=predictions, transactions=transactions)


_SQLITE_QUERY = """
WITH eligible AS (
    SELECT
        p.prediction_id,
        p.customer_id,
        p.cutoff,
        t.txn_id,
        t.txn_ts,
        t.amount
    FROM predictions AS p
    LEFT JOIN transactions AS t
      ON t.customer_id = p.customer_id
     AND t.txn_ts <= p.cutoff
), aggregated AS (
    SELECT
        prediction_id,
        customer_id,
        cutoff,
        COUNT(txn_id) AS txn_count,
        COALESCE(SUM(amount), 0.0) AS spend,
        MAX(txn_ts) AS last_txn_ts
    FROM eligible
    GROUP BY prediction_id, customer_id, cutoff
)
SELECT
    prediction_id,
    customer_id,
    txn_count,
    spend,
    CASE
        WHEN last_txn_ts IS NULL THEN NULL
        ELSE CAST(julianday(cutoff) - julianday(last_txn_ts) AS INTEGER)
    END AS recency_days
FROM aggregated
ORDER BY prediction_id
"""


_DUCKDB_QUERY = """
WITH eligible AS (
    SELECT
        p.prediction_id,
        p.customer_id,
        p.cutoff,
        t.txn_id,
        t.txn_ts,
        t.amount
    FROM predictions AS p
    LEFT JOIN transactions AS t
      ON t.customer_id = p.customer_id
     AND CAST(t.txn_ts AS TIMESTAMP) <= CAST(p.cutoff AS TIMESTAMP)
), aggregated AS (
    SELECT
        prediction_id,
        customer_id,
        cutoff,
        COUNT(txn_id) AS txn_count,
        COALESCE(SUM(amount), 0.0) AS spend,
        MAX(txn_ts) AS last_txn_ts
    FROM eligible
    GROUP BY prediction_id, customer_id, cutoff
)
SELECT
    prediction_id,
    customer_id,
    txn_count,
    spend,
    CASE
        WHEN last_txn_ts IS NULL THEN NULL
        ELSE date_diff('day', CAST(last_txn_ts AS TIMESTAMP), CAST(cutoff AS TIMESTAMP))
    END AS recency_days
FROM aggregated
ORDER BY prediction_id
"""


_RANK_QUERY = """
SELECT
    id,
    score,
    ROW_NUMBER() OVER (ORDER BY score DESC, id) AS row_number_value,
    RANK() OVER (ORDER BY score DESC) AS rank_value,
    DENSE_RANK() OVER (ORDER BY score DESC) AS dense_rank_value
FROM rank_demo
ORDER BY id
"""


def sqlite_point_in_time_features(fixture: ParityFixture | None = None) -> pd.DataFrame:
    fixture = fixture or build_fixture()
    conn = sqlite3.connect(":memory:")
    try:
        fixture.predictions.to_sql("predictions", conn, index=False)
        fixture.transactions.to_sql("transactions", conn, index=False)
        return pd.read_sql_query(_SQLITE_QUERY, conn)
    finally:
        conn.close()


def duckdb_point_in_time_features(fixture: ParityFixture | None = None) -> pd.DataFrame:
    try:
        import duckdb
    except ImportError as exc:  # pragma: no cover - exercised only without optional dependency
        raise ImportError("install sqlfeat[duckdb] to run DuckDB parity checks") from exc

    fixture = fixture or build_fixture()
    conn = duckdb.connect(database=":memory:")
    try:
        conn.register("predictions_df", fixture.predictions)
        conn.register("transactions_df", fixture.transactions)
        conn.execute("CREATE TABLE predictions AS SELECT * FROM predictions_df")
        conn.execute("CREATE TABLE transactions AS SELECT * FROM transactions_df")
        return conn.execute(_DUCKDB_QUERY).df()
    finally:
        conn.close()


def independent_expected_features(fixture: ParityFixture | None = None) -> pd.DataFrame:
    """Pandas calculation that does not execute either SQL query."""
    fixture = fixture or build_fixture()
    p = fixture.predictions.copy()
    t = fixture.transactions.copy()
    p["cutoff_dt"] = pd.to_datetime(p["cutoff"])
    t["txn_dt"] = pd.to_datetime(t["txn_ts"])

    rows: list[dict[str, object]] = []
    for pred in p.itertuples(index=False):
        eligible = t[(t["customer_id"] == pred.customer_id) & (t["txn_dt"] <= pred.cutoff_dt)]
        if eligible.empty:
            recency: int | None = None
            spend = 0.0
        else:
            last = eligible["txn_dt"].max()
            recency = int((pred.cutoff_dt - last).days)
            spend = float(eligible["amount"].sum())
        rows.append(
            {
                "prediction_id": pred.prediction_id,
                "customer_id": int(pred.customer_id),
                "txn_count": int(len(eligible)),
                "spend": spend,
                "recency_days": recency,
            }
        )
    return pd.DataFrame(rows).sort_values("prediction_id").reset_index(drop=True)


def rank_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [("a", 9.0), ("b", 9.0), ("c", 7.0), ("d", 4.0)],
        columns=["id", "score"],
    )


def sqlite_rank_results() -> pd.DataFrame:
    conn = sqlite3.connect(":memory:")
    try:
        rank_fixture().to_sql("rank_demo", conn, index=False)
        return pd.read_sql_query(_RANK_QUERY, conn)
    finally:
        conn.close()


def duckdb_rank_results() -> pd.DataFrame:
    try:
        import duckdb
    except ImportError as exc:  # pragma: no cover
        raise ImportError("install sqlfeat[duckdb] to run DuckDB parity checks") from exc
    conn = duckdb.connect(database=":memory:")
    try:
        conn.register("rank_df", rank_fixture())
        conn.execute("CREATE TABLE rank_demo AS SELECT * FROM rank_df")
        return conn.execute(_RANK_QUERY).df()
    finally:
        conn.close()
