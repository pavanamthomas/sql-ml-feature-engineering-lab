"""Flagship: leaky in-sample AUC exceeds correct AUC; sentinel test still holds."""

from __future__ import annotations

from sqlfeat.features import load_training_tables
from sqlfeat.flagship import evaluate_flagship
from sqlfeat.leakage import assert_correct_excludes_sentinels, assert_leaky_includes_sentinels


def test_leaky_auc_exceeds_correct_auc(conn) -> None:
    tables = load_training_tables(conn)
    result = evaluate_flagship(tables.correct, tables.leaky, seed=2026)
    assert result.n_rows == len(tables.correct)
    assert 0.0 < result.prevalence < 1.0
    assert result.auc_correct >= 0.5
    assert result.auc_leaky > result.auc_correct
    assert result.auc_gap > 0.02
    assert result.n_correct_sentinel == 0
    assert result.n_leaky_sentinel > 0


def test_flagship_sentinel_contract(conn) -> None:
    tables = load_training_tables(conn)
    assert_correct_excludes_sentinels(tables.correct)
    assert_leaky_includes_sentinels(tables.leaky)
