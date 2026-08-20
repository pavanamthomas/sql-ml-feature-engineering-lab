"""Planted future-only sentinels distinguish correct from leaky SQL."""

from __future__ import annotations

import pandas as pd

from sqlfeat.features import (
    correct_training_table,
    leaky_date_truncation,
    leaky_join_all,
    leaky_label_day,
    leaky_training_table,
    txn_counts_correct,
    txn_counts_leaky,
)
from sqlfeat.generate import KNOWN_SENTINEL_CUSTOMERS, PRIMARY_CUTOFF, SENTINEL_AMOUNT, fmt_ts
from sqlfeat.leakage import assert_correct_excludes_sentinels, assert_leaky_includes_sentinels


def test_correct_excludes_and_leaky_includes_sentinels(conn) -> None:
    correct = correct_training_table(conn)
    leaky = leaky_training_table(conn)
    assert_correct_excludes_sentinels(correct)
    assert_leaky_includes_sentinels(leaky)


def test_join_all_transactions_sees_sentinel_amount(conn) -> None:
    frame = leaky_join_all(conn)
    primary = frame.loc[frame["cutoff_ts"] == fmt_ts(PRIMARY_CUTOFF)]
    for cid in KNOWN_SENTINEL_CUSTOMERS:
        value = float(primary.loc[primary["customer_id"] == cid, "sentinel_spend"].iloc[0])
        assert abs(value - SENTINEL_AMOUNT) < 1e-6


def test_leaky_txn_counts_include_label_window_sentinels(conn) -> None:
    correct = txn_counts_correct(conn)
    leaky = txn_counts_leaky(conn)
    primary_c = correct.loc[correct["cutoff_ts"] == fmt_ts(PRIMARY_CUTOFF)]
    primary_l = leaky.loc[leaky["cutoff_ts"] == fmt_ts(PRIMARY_CUTOFF)]
    assert (primary_c["sentinel_spend"] == 0).all()
    assert (primary_l["sentinel_spend"] > 0).any()
    assert primary_l["txn_count_30"].sum() >= primary_c["txn_count_30"].sum()


def test_date_truncation_includes_same_day_after_midnight_cutoff(conn) -> None:
    frame = leaky_date_truncation(conn)
    primary = frame.loc[frame["cutoff_ts"] == fmt_ts(PRIMARY_CUTOFF)]
    assert int(primary["n_after_cutoff_included"].sum()) > 0


def test_label_day_window_includes_afternoon_same_day(conn) -> None:
    frame = leaky_label_day(conn)
    primary = frame.loc[frame["cutoff_ts"] == fmt_ts(PRIMARY_CUTOFF)]
    assert int(primary["n_same_day_after_cutoff"].sum()) > 0


def test_sentinel_rows_are_strictly_after_primary_cutoff(conn) -> None:
    cutoff = fmt_ts(PRIMARY_CUTOFF)
    n_bad = int(
        pd.read_sql_query(
            "SELECT COUNT(*) AS n FROM transactions WHERE is_sentinel = 1 AND txn_ts <= ?",
            conn,
            params=(cutoff,),
        )["n"].iloc[0]
    )
    assert n_bad == 0
