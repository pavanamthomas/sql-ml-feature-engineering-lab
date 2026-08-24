"""Execute the SQL files under sql/correct and sql/leaky.

The query text is the artefact. A statement that compiles is not therefore
point-in-time safe; sentinel and pandas-parity tests decide that.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from sqlfeat.db import read_sql


@dataclass(frozen=True)
class TrainingTables:
    """Correct and leaky training frames with aligned prediction ids."""

    correct: pd.DataFrame
    leaky: pd.DataFrame


def correct_training_table(conn) -> pd.DataFrame:
    """Point-in-time training table (``sql/correct/pit_training_table.sql``)."""
    return read_sql(conn, "correct/pit_training_table.sql")


def leaky_training_table(conn) -> pd.DataFrame:
    """Leaky training table (``sql/leaky/pit_training_table.sql``)."""
    return read_sql(conn, "leaky/pit_training_table.sql")


def load_training_tables(conn) -> TrainingTables:
    """Return both pipelines."""
    return TrainingTables(correct=correct_training_table(conn), leaky=leaky_training_table(conn))


def txn_counts_correct(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/txn_counts.sql")


def txn_counts_leaky(conn) -> pd.DataFrame:
    return read_sql(conn, "leaky/txn_counts.sql")


def rolling_spend_correct(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/rolling_spend.sql")


def recency_tenure(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/recency_tenure.sql")


def event_frequencies(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/event_frequencies.sql")


def session_aggregates(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/session_aggregates.sql")


def lagged_outcomes(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/lagged_outcomes.sql")


def product_behaviour(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/product_behaviour.sql")


def cohort_retention(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/cohort.sql")


def dedup_transactions(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/dedup.sql")


def ranking_demo(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/ranking.sql")


def referral_depth(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/referral_depth.sql")


def groupby_vs_window(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/groupby_vs_window.sql")


def groupby_totals(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/groupby_totals.sql")


def null_join_left(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/null_join.sql")


def null_join_inner(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/null_join_inner.sql")


def exists_prior(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/exists_prior.sql")


def self_join_referrer(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/self_join_referrer.sql")


def lag_previous_txn(conn) -> pd.DataFrame:
    return read_sql(conn, "correct/lag_previous_txn.sql")


def leaky_join_all(conn) -> pd.DataFrame:
    return read_sql(conn, "leaky/join_all_transactions.sql")


def leaky_lead_next_txn(conn) -> pd.DataFrame:
    return read_sql(conn, "leaky/lead_next_txn.sql")


def leaky_label_day(conn) -> pd.DataFrame:
    return read_sql(conn, "leaky/rolling_includes_label_day.sql")


def leaky_date_truncation(conn) -> pd.DataFrame:
    return read_sql(conn, "leaky/date_truncation.sql")
