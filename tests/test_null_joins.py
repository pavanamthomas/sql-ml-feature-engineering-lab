"""NULL join semantics: LEFT keeps unmatched and NULL keys; INNER drops them."""

from __future__ import annotations

import pandas as pd

from sqlfeat.db import table_count
from sqlfeat.features import null_join_inner, null_join_left


def test_left_join_preserves_all_customers(conn) -> None:
    left = null_join_left(conn)
    assert len(left) == table_count(conn, "customers")
    n_null_segment = int(
        pd.read_sql_query(
            "SELECT COUNT(*) AS n FROM customers WHERE segment IS NULL",
            conn,
        )["n"].iloc[0]
    )
    assert n_null_segment > 0
    assert int((left["join_status"] == "null_segment").sum()) == n_null_segment
    assert left.loc[left["join_status"] == "null_segment", "risk_bucket"].isna().all()


def test_inner_join_drops_null_and_unmatched_segments(conn) -> None:
    left = null_join_left(conn)
    inner = null_join_inner(conn)
    assert len(inner) < len(left)
    assert inner["risk_bucket"].notna().all()
    assert inner["segment"].notna().all()
    assert set(inner["segment"]).issubset({"A", "B"})


def test_null_equals_null_does_not_match(conn) -> None:
    n = int(
        pd.read_sql_query(
            """
            SELECT COUNT(*) AS n
            FROM customers AS c
            JOIN segment_lookup AS s
              ON c.segment = s.segment
            WHERE c.segment IS NULL
            """,
            conn,
        )["n"].iloc[0]
    )
    assert n == 0
