"""SQL competencies appear in laboratory query files that tests execute."""

from __future__ import annotations

from pathlib import Path

from sqlfeat.features import (
    cohort_retention,
    correct_training_table,
    exists_prior,
    groupby_vs_window,
    lag_previous_txn,
    leaky_lead_next_txn,
    ranking_demo,
    referral_depth,
)
from sqlfeat.paths import sql_dir


def _sql_corpus() -> str:
    parts = []
    root = sql_dir()
    for path in root.rglob("*.sql"):
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts).upper()


def test_competency_tokens_present_in_sql_files() -> None:
    corpus = _sql_corpus()
    required = [
        "INNER JOIN",
        "LEFT JOIN",
        "GROUP BY",
        "HAVING",
        "CASE",
        "WITH",
        "EXISTS",
        "ROW_NUMBER",
        "RANK()",
        "DENSE_RANK",
        "LAG(",
        "LEAD(",
        "FIRST_VALUE",
        "LAST_VALUE",
        "PARTITION BY",
        "ROWS BETWEEN",
        "COALESCE",
        "DATETIME(",
        "JULIANDAY",
        "FILTER (",
        "RECURSIVE",
        "STRFTIME",
    ]
    missing = [token for token in required if token not in corpus]
    assert missing == []


def test_competency_queries_execute(conn) -> None:
    correct_training_table(conn)
    exists_prior(conn)
    groupby_vs_window(conn)
    ranking_demo(conn)
    lag_previous_txn(conn)
    leaky_lead_next_txn(conn)
    referral_depth(conn)
    cohort_retention(conn)


def test_sql_directory_layout() -> None:
    root = sql_dir()
    assert (root / "schema.sql").is_file()
    assert (root / "correct" / "pit_training_table.sql").is_file()
    assert (root / "leaky" / "pit_training_table.sql").is_file()
    assert Path(root / "leaky" / "lead_next_txn.sql").is_file()
