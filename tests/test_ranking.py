"""ROW_NUMBER vs RANK vs DENSE_RANK on known ties."""

from __future__ import annotations

from sqlfeat.features import ranking_demo


def test_rank_demo_ties(conn) -> None:
    frame = ranking_demo(conn)
    scores = list(frame["score"])
    assert scores == [30, 20, 20, 20, 10]
    assert list(frame["rn"]) == [1, 2, 3, 4, 5]
    assert list(frame["rnk"]) == [1, 2, 2, 2, 5]
    assert list(frame["dense_rnk"]) == [1, 2, 2, 2, 3]


def test_row_number_unique_rank_not_unique_on_ties(conn) -> None:
    frame = ranking_demo(conn)
    assert frame["rn"].nunique() == len(frame)
    assert frame["rnk"].nunique() < len(frame)
    assert frame["dense_rnk"].max() < frame["rnk"].max()
