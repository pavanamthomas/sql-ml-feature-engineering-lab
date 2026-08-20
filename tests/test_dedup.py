"""Dedup with ROW_NUMBER keeps one row per txn_id — the latest ingest."""

from __future__ import annotations

import pandas as pd

from sqlfeat.db import table_count
from sqlfeat.features import dedup_transactions


def test_dedup_row_count_matches_transactions(conn) -> None:
    deduped = dedup_transactions(conn)
    assert len(deduped) == table_count(conn, "transactions")
    assert deduped["txn_id"].nunique() == len(deduped)


def test_dedup_prefers_later_ingest(conn) -> None:
    raw = pd.read_sql_query("SELECT * FROM transactions_raw", conn)
    dup_ids = raw.groupby("txn_id").size()
    dup_ids = dup_ids[dup_ids > 1].index
    assert len(dup_ids) > 0
    deduped = dedup_transactions(conn).set_index("txn_id")
    for txn_id in list(dup_ids)[:25]:
        grp = raw.loc[raw["txn_id"] == txn_id].sort_values(["ingested_ts", "raw_id"])
        expected = grp.iloc[-1]
        got = deduped.loc[txn_id]
        assert abs(float(got["amount"]) - float(expected["amount"])) < 1e-9
        assert str(got["ingested_ts"]) == str(expected["ingested_ts"])


def test_raw_has_more_rows_than_deduped(conn) -> None:
    assert table_count(conn, "transactions_raw") > table_count(conn, "transactions")
