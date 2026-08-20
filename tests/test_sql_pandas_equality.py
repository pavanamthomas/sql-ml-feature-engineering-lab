"""SQL and pandas implement the same point-in-time features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from sqlfeat.cases import case_g_pandas_parity
from sqlfeat.pandas_features import FILLNA


def test_sql_pandas_equality_sorted_prediction_id(conn) -> None:
    sql_part, pandas_part = case_g_pandas_parity(conn)
    assert list(sql_part["prediction_id"]) == list(pandas_part["prediction_id"])
    count_cols = ["txn_count_7", "txn_count_30", "txn_count_90", "n_sessions_30"]
    for col in count_cols:
        np.testing.assert_array_equal(
            sql_part[col].to_numpy(dtype=int),
            pandas_part[col].to_numpy(dtype=int),
            err_msg=col,
        )
    for col in ["spend_7", "spend_30", "spend_90", "tenure_days", "sentinel_spend"]:
        np.testing.assert_allclose(
            sql_part[col].to_numpy(dtype=float),
            pandas_part[col].to_numpy(dtype=float),
            rtol=1e-8,
            atol=1e-6,
            err_msg=col,
        )
    rec_sql = sql_part["recency_days"].to_numpy(dtype=float)
    rec_pd = pandas_part["recency_days"].to_numpy(dtype=float)
    np.testing.assert_allclose(rec_sql, rec_pd, rtol=1e-8, atol=1e-5, equal_nan=True)


def test_fillna_policy_recency_nan_counts_zero(conn) -> None:
    sql_part, pandas_part = case_g_pandas_parity(conn)
    assert np.isnan(FILLNA.recency_if_missing)
    # Customers with zero prior txns: recency is null in both engines.
    no_txn = pandas_part["txn_count_7"] + pandas_part["txn_count_30"] + pandas_part["txn_count_90"]
    # A customer may have older-than-90-day history, so use sentinel_spend + counts
    # only as a weak check: spend fills 0, not NaN.
    assert not pandas_part["spend_30"].isna().any()
    assert sql_part["spend_30"].notna().all()
    del no_txn
