"""Generator reproducibility under seed 2026."""

from __future__ import annotations

import pandas as pd

from sqlfeat.db import connect, table_count
from sqlfeat.generate import DEFAULT_SEED, generate_frames, populate


def _digest(frames: dict[str, pd.DataFrame]) -> tuple:
    parts = []
    for name in sorted(frames):
        df = frames[name].sort_values(list(frames[name].columns)).reset_index(drop=True)
        parts.append((name, tuple(df.columns), pd.util.hash_pandas_object(df).sum()))
    return tuple(parts)


def test_same_seed_same_frame_digest() -> None:
    a = generate_frames(seed=DEFAULT_SEED)
    b = generate_frames(seed=DEFAULT_SEED)
    assert _digest(a) == _digest(b)


def test_same_seed_same_sqlite_counts() -> None:
    conn_a = connect(None)
    conn_b = connect(None)
    populate(conn_a, seed=DEFAULT_SEED)
    populate(conn_b, seed=DEFAULT_SEED)
    for table in ("customers", "transactions", "events", "predictions", "outcomes"):
        assert table_count(conn_a, table) == table_count(conn_b, table)
    amt_a = float(pd.read_sql_query("SELECT SUM(amount) AS s FROM transactions", conn_a)["s"].iloc[0])
    amt_b = float(pd.read_sql_query("SELECT SUM(amount) AS s FROM transactions", conn_b)["s"].iloc[0])
    assert amt_a == amt_b
    conn_a.close()
    conn_b.close()


def test_different_seed_changes_transaction_sum() -> None:
    a = generate_frames(seed=DEFAULT_SEED)
    b = generate_frames(seed=DEFAULT_SEED + 1)
    assert a["transactions"]["amount"].sum() != b["transactions"]["amount"].sum()
