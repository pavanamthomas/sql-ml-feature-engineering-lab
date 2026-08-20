"""Named demonstration cases A–H.

Each function returns a small result object for tests and for
``scripts/run_all.py``. The SQL lives in ``sql/correct`` and ``sql/leaky``.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from sqlfeat.db import read_sql, table_count
from sqlfeat.features import (
    cohort_retention,
    dedup_transactions,
    groupby_totals,
    groupby_vs_window,
    lagged_outcomes,
    leaky_lead_next_txn,
    ranking_demo,
)
from sqlfeat.pandas_features import align_sql_and_pandas, pandas_pit_features


@dataclass(frozen=True)
class GroupByVsWindow:
    """Case A: aggregation destroys row-level grain."""

    n_txn_rows: int
    n_customer_rows: int
    window_rows: int
    totals_rows: int


def case_a_groupby_vs_window(conn) -> GroupByVsWindow:
    window = groupby_vs_window(conn)
    totals = groupby_totals(conn)
    n_txn = table_count(conn, "transactions")
    n_cust = int(pd.read_sql_query("SELECT COUNT(DISTINCT customer_id) AS n FROM transactions", conn)["n"].iloc[0])
    return GroupByVsWindow(
        n_txn_rows=n_txn,
        n_customer_rows=n_cust,
        window_rows=len(window),
        totals_rows=len(totals),
    )


@dataclass(frozen=True)
class DedupResult:
    n_raw: int
    n_deduped: int
    n_txn: int


def case_b_dedup(conn) -> DedupResult:
    deduped = dedup_transactions(conn)
    n_raw = table_count(conn, "transactions_raw")
    n_txn = table_count(conn, "transactions")
    return DedupResult(n_raw=n_raw, n_deduped=len(deduped), n_txn=n_txn)


def case_c_cohort(conn) -> pd.DataFrame:
    return cohort_retention(conn)


def case_d_ranking(conn) -> pd.DataFrame:
    return ranking_demo(conn)


@dataclass(frozen=True)
class LagLead:
    n_with_lag: int
    n_with_lead: int
    n_lead_after_cutoff: int


def case_e_lag_vs_lead(conn) -> LagLead:
    lag = lagged_outcomes(conn)
    lead = leaky_lead_next_txn(conn)
    n_lag = int(lag["lag_y"].notna().sum())
    n_lead = int(lead["lead_amount"].notna().sum())
    n_future = int(
        (pd.to_datetime(lead["lead_txn_ts"]) > pd.to_datetime(lead["cutoff_ts"])).sum()
    )
    return LagLead(n_with_lag=n_lag, n_with_lead=n_lead, n_lead_after_cutoff=n_future)


def case_f_pit_training(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/pit_training_table.sql")


def case_g_pandas_parity(conn) -> tuple[pd.DataFrame, pd.DataFrame]:
    sql_df = read_sql(conn, "correct/pit_training_table.sql")
    pred = pd.read_sql_query("SELECT * FROM predictions", conn)
    cust = pd.read_sql_query("SELECT * FROM customers", conn)
    txn = pd.read_sql_query("SELECT * FROM transactions", conn)
    sess = pd.read_sql_query("SELECT * FROM sessions", conn)
    pan = pandas_pit_features(pred, cust, txn, sess)
    cols = [
        "prediction_id",
        "txn_count_7",
        "txn_count_30",
        "txn_count_90",
        "spend_7",
        "spend_30",
        "spend_90",
        "tenure_days",
        "recency_days",
        "n_sessions_30",
        "sentinel_spend",
    ]
    return align_sql_and_pandas(sql_df, pan, cols)
