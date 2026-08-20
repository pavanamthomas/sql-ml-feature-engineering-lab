"""Pandas reimplementation of the key point-in-time features.

Problem: an independent implementation of the same estimand, used to
check the SQL.

Assumptions: timestamps parse as naive datetime; windows are half-open
on the left and closed on the right at cutoff, matching
``txn_ts <= cutoff_ts AND txn_ts > cutoff_ts - N days``.

Fillna policy (locked by tests):
- counts fill 0
- spend fills 0.0
- recency_days stays NaN when there is no prior transaction
- tenure_days is never filled; every customer has a signup_ts

Why pandas: it is a second engine, not a second copy of the SQL parser.

Alternative: a third SQL dialect (DuckDB). Optional locally; not required
in CI.

What can go wrong: ``merge`` without a time predicate reproduces the
leaky join. Inclusive vs exclusive window edges drift from SQLite
``datetime(cutoff, '-N days')``.

How checked: sort on ``prediction_id``, then ``assert_allclose`` on
numeric columns after the fillna policy.

What can be concluded: SQL and pandas agree on this DGP for the named
columns.

What cannot: that either implementation is correct for a warehouse whose
clock, timezone, or late-arriving facts differ from this DGP.
"""

from __future__ import annotations

from datetime import timedelta
from dataclasses import dataclass

import numpy as np
import pandas as pd

WINDOW_DAYS = (7, 30, 90)


@dataclass(frozen=True)
class FillnaPolicy:
    """Documented fill policy for SQL/pandas comparison."""

    counts: int = 0
    spend: float = 0.0
    recency_if_missing: float = np.nan


FILLNA = FillnaPolicy()


def _ts(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series)


def pandas_pit_features(
    predictions: pd.DataFrame,
    customers: pd.DataFrame,
    transactions: pd.DataFrame,
    sessions: pd.DataFrame,
) -> pd.DataFrame:
    """Return tenure, recency, txn counts/spend, and session counts.

    One output row per ``prediction_id``, including customers whose only
    transactions are after cutoff (counts are then zero, recency is NaN).
    """
    pred = predictions.copy()
    pred["cutoff_dt"] = _ts(pred["cutoff_ts"])
    cust = customers.copy()
    cust["signup_dt"] = _ts(cust["signup_ts"])
    txn = transactions.copy()
    txn["txn_dt"] = _ts(txn["txn_ts"])
    sess = sessions.copy()
    sess["session_dt"] = _ts(sess["session_ts"])

    base = pred.merge(
        cust[["customer_id", "signup_dt", "cohort_month"]],
        on="customer_id",
        how="inner",
    )
    base["tenure_days"] = (base["cutoff_dt"] - base["signup_dt"]).dt.total_seconds() / 86400.0
    base = base.sort_values("prediction_id").reset_index(drop=True)

    txn_by_cust = {cid: grp for cid, grp in txn.groupby("customer_id")}
    sess_by_cust = {cid: grp for cid, grp in sess.groupby("customer_id")}

    rows: list[dict[str, object]] = []
    for rec in base.itertuples(index=False):
        cutoff = pd.Timestamp(rec.cutoff_dt)
        cid = int(rec.customer_id)
        known = txn_by_cust.get(cid, txn.iloc[0:0])
        if len(known):
            known = known.loc[known["txn_dt"] <= cutoff]
        rec_row: dict[str, object] = {
            "prediction_id": int(rec.prediction_id),
            "customer_id": cid,
            "tenure_days": float(rec.tenure_days),
            "cohort_month": rec.cohort_month,
        }
        if known.empty:
            rec_row["recency_days"] = FILLNA.recency_if_missing
            rec_row["sentinel_spend"] = float(FILLNA.spend)
            for n in WINDOW_DAYS:
                rec_row[f"txn_count_{n}"] = int(FILLNA.counts)
                rec_row[f"spend_{n}"] = float(FILLNA.spend)
        else:
            last_ts = known["txn_dt"].max()
            rec_row["recency_days"] = (cutoff - last_ts).total_seconds() / 86400.0
            rec_row["sentinel_spend"] = float(known.loc[known["is_sentinel"] == 1, "amount"].sum())
            for n in WINDOW_DAYS:
                lo = cutoff - timedelta(days=int(n))
                window = known.loc[known["txn_dt"] > lo]
                rec_row[f"txn_count_{n}"] = int(len(window))
                rec_row[f"spend_{n}"] = float(window["amount"].sum()) if len(window) else float(FILLNA.spend)

        sess_c = sess_by_cust.get(cid, sess.iloc[0:0])
        if len(sess_c):
            lo30 = cutoff - timedelta(days=30)
            sess_w = sess_c.loc[(sess_c["session_dt"] <= cutoff) & (sess_c["session_dt"] > lo30)]
            rec_row["n_sessions_30"] = int(sess_w["session_id"].nunique())
        else:
            rec_row["n_sessions_30"] = int(FILLNA.counts)
        rows.append(rec_row)

    return pd.DataFrame(rows)


def align_sql_and_pandas(
    sql_df: pd.DataFrame,
    pandas_df: pd.DataFrame,
    columns: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sort both frames by prediction_id and select comparable columns."""
    left = sql_df.sort_values("prediction_id").reset_index(drop=True)
    right = pandas_df.sort_values("prediction_id").reset_index(drop=True)
    if not left["prediction_id"].equals(right["prediction_id"]):
        raise ValueError("prediction_id columns do not match after sort")
    return left[columns], right[columns]
