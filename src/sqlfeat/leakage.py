"""Temporal leakage sentinels.

Problem: a training table can look well-formed and still include events
that occurred after the prediction cutoff. A planted future-only row is
an independent detector.

Assumptions: every sentinel transaction has ``is_sentinel = 1`` and
``txn_ts`` strictly after that customer's primary cutoff; amount equals
``SENTINEL_AMOUNT``.

Why a sentinel: comparing two SQL strings by eye does not prove an
information-set claim. A row that exists only in the future does.

Alternative: audit query text with a linter. Useful, not sufficient;
this test executes the query.

What can go wrong: planting sentinels before cutoff; using the sentinel
as a model feature and calling the AUC a skill result.

How checked: correct tables have ``sentinel_spend == 0`` on every row;
leaky tables have ``sentinel_spend == SENTINEL_AMOUNT`` for planted
customers at the primary cutoff.

What can be concluded: the named correct query does not see these
planted rows on this DGP.

What cannot: that an unseen production query is leak-free.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from sqlfeat.generate import KNOWN_SENTINEL_CUSTOMERS, PRIMARY_CUTOFF, SENTINEL_AMOUNT, fmt_ts


@dataclass(frozen=True)
class SentinelReport:
    n_sentinel_txn: int
    n_correct_nonzero: int
    n_leaky_nonzero: int
    known_customers_leaky: tuple[int, ...]


def _primary(df: pd.DataFrame) -> pd.DataFrame:
    cutoff = fmt_ts(PRIMARY_CUTOFF)
    return df.loc[df["cutoff_ts"] == cutoff].copy()


def sentinel_report(correct: pd.DataFrame, leaky: pd.DataFrame) -> SentinelReport:
    """Compare sentinel_spend on the primary cutoff."""
    c = _primary(correct)
    l = _primary(leaky)
    n_c = int((c["sentinel_spend"].fillna(0) > 0).sum())
    n_l = int((l["sentinel_spend"].fillna(0) > 0).sum())
    known = tuple(
        int(x)
        for x in sorted(
            l.loc[
                (l["customer_id"].isin(KNOWN_SENTINEL_CUSTOMERS))
                & (l["sentinel_spend"].fillna(0) > 0),
                "customer_id",
            ].unique()
        )
    )
    return SentinelReport(
        n_sentinel_txn=n_l,
        n_correct_nonzero=n_c,
        n_leaky_nonzero=n_l,
        known_customers_leaky=known,
    )


def assert_correct_excludes_sentinels(correct: pd.DataFrame) -> None:
    """Raise if a primary-cutoff row sees sentinel spend.

    Sentinels are planted after the primary cutoff. They are future then.
    They are legitimate history at a later cutoff and must not be treated
    as leakage there.
    """
    primary = _primary(correct)
    spent = primary["sentinel_spend"].fillna(0)
    if (spent != 0).any():
        bad = primary.loc[spent != 0, ["prediction_id", "customer_id", "cutoff_ts", "sentinel_spend"]]
        raise AssertionError(f"correct table includes sentinel spend at primary cutoff:\n{bad}")


def assert_leaky_includes_sentinels(leaky: pd.DataFrame) -> None:
    """Raise AssertionError if known sentinel customers are invisible."""
    primary = _primary(leaky)
    for cid in KNOWN_SENTINEL_CUSTOMERS:
        row = primary.loc[primary["customer_id"] == cid]
        if row.empty:
            raise AssertionError(f"missing primary prediction for sentinel customer {cid}")
        value = float(row["sentinel_spend"].iloc[0])
        if abs(value - SENTINEL_AMOUNT) > 1e-6:
            raise AssertionError(
                f"leaky table missed sentinel for customer {cid}: spend={value}"
            )
