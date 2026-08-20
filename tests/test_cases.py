"""Cases A–H: group vs window, cohort, lag/lead, PIT, explain plans."""

from __future__ import annotations

import pandas as pd

from sqlfeat.cases import (
    case_a_groupby_vs_window,
    case_b_dedup,
    case_c_cohort,
    case_e_lag_vs_lead,
    case_f_pit_training,
)
from sqlfeat.explain import explain_pit_probe
from sqlfeat.features import referral_depth, self_join_referrer


def test_case_a_window_keeps_txn_grain(conn) -> None:
    result = case_a_groupby_vs_window(conn)
    assert result.window_rows == result.n_txn_rows
    assert result.totals_rows == result.n_customer_rows
    assert result.n_txn_rows > result.n_customer_rows


def test_case_b_dedup_matches_clean_table(conn) -> None:
    result = case_b_dedup(conn)
    assert result.n_deduped == result.n_txn
    assert result.n_raw > result.n_txn


def test_case_c_cohort_has_month_pairs(conn) -> None:
    frame = case_c_cohort(conn)
    assert len(frame) > 0
    assert {"cohort_month", "activity_month", "n_active"}.issubset(frame.columns)


def test_case_e_lead_sees_future_timestamps(conn) -> None:
    result = case_e_lag_vs_lead(conn)
    assert result.n_with_lag > 0
    assert result.n_lead_after_cutoff > 0


def test_case_f_pit_has_label_and_features(conn) -> None:
    frame = case_f_pit_training(conn)
    assert {"y", "txn_count_30", "spend_30", "lag_y", "tenure_days"}.issubset(frame.columns)
    assert set(frame["y"].unique()).issubset({0, 1})


def test_case_h_index_changes_explain_plan(conn) -> None:
    pair = explain_pit_probe(conn)
    assert pair.sqlite_version
    assert "SCAN" in pair.without_indexes.upper() or "SEARCH" in pair.without_indexes.upper()
    assert "idx_txn_customer_ts" in pair.with_indexes


def test_referral_depth_roots_are_zero(conn) -> None:
    tree = referral_depth(conn)
    n_cust = int(pd.read_sql_query("SELECT COUNT(*) AS n FROM customers", conn)["n"].iloc[0])
    assert len(tree) == n_cust
    roots = tree.loc[tree["referred_by"].isna()]
    assert (roots["depth"] == 0).all()
    assert (tree["depth"] >= 0).all()


def test_self_join_referrer_preserves_customers(conn) -> None:
    frame = self_join_referrer(conn)
    n_cust = int(pd.read_sql_query("SELECT COUNT(*) AS n FROM customers", conn)["n"].iloc[0])
    assert len(frame) == n_cust
