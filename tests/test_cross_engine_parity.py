"""Cross-engine point-in-time parity checks."""

from __future__ import annotations

import pandas as pd
import pytest

from sqlfeat.cross_engine import (
    duckdb_point_in_time_features,
    duckdb_rank_results,
    independent_expected_features,
    sqlite_point_in_time_features,
    sqlite_rank_results,
)

try:
    import duckdb as _duckdb  # noqa: F401
except ImportError:
    _HAS_DUCKDB = False
else:
    _HAS_DUCKDB = True

_duckdb_only = pytest.mark.skipif(
    not _HAS_DUCKDB, reason="install sqlfeat[duckdb] for the second-engine checks"
)


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().sort_values("prediction_id").reset_index(drop=True)
    out["customer_id"] = out["customer_id"].astype(int)
    out["txn_count"] = out["txn_count"].astype(int)
    out["spend"] = out["spend"].astype(float)
    out["recency_days"] = out["recency_days"].astype("Int64")
    return out


def test_sqlite_and_pandas_agree_on_point_in_time_features() -> None:
    sqlite = _normalise(sqlite_point_in_time_features())
    expected = _normalise(independent_expected_features())
    pd.testing.assert_frame_equal(sqlite, expected, check_dtype=False, atol=1e-12, rtol=0)


@_duckdb_only
def test_duckdb_agrees_with_sqlite_on_point_in_time_features() -> None:
    sqlite = _normalise(sqlite_point_in_time_features())
    duckdb = _normalise(duckdb_point_in_time_features())
    pd.testing.assert_frame_equal(duckdb, sqlite, check_dtype=False, atol=1e-12, rtol=0)


def test_future_sentinel_is_excluded_without_using_model_performance() -> None:
    result = _normalise(sqlite_point_in_time_features())
    row = result.loc[result["prediction_id"] == "p1"].iloc[0]
    assert row["txn_count"] == 2
    assert row["spend"] == 30.0
    assert row["spend"] < 99999.0
    assert row["recency_days"] == 1


def test_no_history_preserves_zero_aggregates_and_null_recency() -> None:
    result = _normalise(sqlite_point_in_time_features())
    row = result.loc[result["prediction_id"] == "p3"].iloc[0]
    assert row["txn_count"] == 0
    assert row["spend"] == 0.0
    assert pd.isna(row["recency_days"])


def test_sqlite_rank_semantics() -> None:
    sqlite = sqlite_rank_results().sort_values("id").reset_index(drop=True)
    # Tied score 9 gets rank 1 in both rows; the next ordinary rank is 3,
    # while dense rank advances to 2. ROW_NUMBER is made deterministic by id.
    assert list(sqlite["rank_value"]) == [1, 1, 3, 4]
    assert list(sqlite["dense_rank_value"]) == [1, 1, 2, 3]
    assert list(sqlite["row_number_value"]) == [1, 2, 3, 4]


@_duckdb_only
def test_window_rank_semantics_match_across_engines() -> None:
    sqlite = sqlite_rank_results().sort_values("id").reset_index(drop=True)
    duckdb = duckdb_rank_results().sort_values("id").reset_index(drop=True)
    pd.testing.assert_frame_equal(sqlite, duckdb, check_dtype=False)
