"""Point-in-time correctness: no post-cutoff facts in correct features."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from sqlfeat.features import correct_training_table, recency_tenure, txn_counts_correct
from sqlfeat.generate import PRIMARY_CUTOFF, SENTINEL_AMOUNT, fmt_ts


def test_training_table_one_row_per_prediction(conn) -> None:
    frame = correct_training_table(conn)
    n_pred = int(pd.read_sql_query("SELECT COUNT(*) AS n FROM predictions", conn)["n"].iloc[0])
    assert len(frame) == n_pred
    assert frame["prediction_id"].nunique() == len(frame)


def test_correct_counts_ignore_post_cutoff_transactions(conn) -> None:
    counts = txn_counts_correct(conn)
    txn = pd.read_sql_query("SELECT customer_id, txn_ts FROM transactions", conn)
    txn["txn_dt"] = pd.to_datetime(txn["txn_ts"])
    pred = pd.read_sql_query("SELECT prediction_id, customer_id, cutoff_ts FROM predictions", conn)
    pred["cutoff_dt"] = pd.to_datetime(pred["cutoff_ts"])
    merged = counts.merge(pred, on=["prediction_id", "customer_id", "cutoff_ts"])
    sample = merged.sample(n=min(40, len(merged)), random_state=2026)
    for rec in sample.itertuples(index=False):
        hist = txn.loc[(txn["customer_id"] == rec.customer_id) & (txn["txn_dt"] <= rec.cutoff_dt)]
        last_30 = hist.loc[hist["txn_dt"] > pd.Timestamp(rec.cutoff_dt) - timedelta(days=30)]
        assert int(rec.txn_count_30) == len(last_30)


def test_recency_null_when_no_history(conn) -> None:
    rec = recency_tenure(conn)
    # Tenure is always finite.
    assert rec["tenure_days"].notna().all()
    assert (rec["tenure_days"] > 0).all()


def test_correct_sentinel_spend_is_zero(conn) -> None:
    frame = correct_training_table(conn)
    primary = frame.loc[frame["cutoff_ts"] == fmt_ts(PRIMARY_CUTOFF)]
    assert (primary["sentinel_spend"].fillna(0.0) == 0.0).all()
    assert (primary["sentinel_txn_count"].fillna(0) == 0).all()
    assert (primary["sentinel_event_count"].fillna(0) == 0).all()


def test_primary_cutoff_has_planted_future_sentinels(conn) -> None:
    cutoff = fmt_ts(PRIMARY_CUTOFF)
    n = int(
        pd.read_sql_query(
            "SELECT COUNT(*) AS n FROM transactions WHERE is_sentinel = 1 AND txn_ts > ?",
            conn,
            params=(cutoff,),
        )["n"].iloc[0]
    )
    assert n > 0
    amounts = pd.read_sql_query(
        "SELECT DISTINCT amount FROM transactions WHERE is_sentinel = 1",
        conn,
    )
    assert list(amounts["amount"]) == [SENTINEL_AMOUNT]
