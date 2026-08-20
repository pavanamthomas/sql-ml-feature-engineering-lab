"""Synthetic relational event DGP for point-in-time feature checks.

Problem: feature queries over customers, accounts, and events need a
known information set at each prediction cutoff, including planted
future-only rows that a correct query must not see.

Assumptions: timestamps are naive UTC ISO strings at second precision;
SQLite ``datetime`` / ``julianday`` arithmetic is valid on that format;
referrals form a DAG (``referred_by < customer_id``); the binary label
is a completed order in ``(cutoff_ts, cutoff_ts + 30 days]``.

Why this method: only a fully observed DGP can prove that a query did
not read the future. A public retail dump does not label the
information set at t.

Alternative: replay an observational log and argue from code review
alone. That cannot produce a sentinel test.

What can go wrong: sentinels timestamped at or before cutoff make the
exclusion test a false alarm. Defining y from the same post-cutoff
orders that a leaky spend window includes will inflate fit metrics —
that inflation is the demonstration, not a claim of skill.

How checked: two generations with seed 2026 must match; every sentinel
row has ``txn_ts > cutoff_ts``; correct SQL yields ``sentinel_spend = 0``.

What can be concluded: on this DGP, a named query either includes or
excludes post-cutoff rows.

What cannot: that a production warehouse is leak-free, or that a
classifier trained here generalises to real customers.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from sqlfeat._rng import DEFAULT_SEED, get_rng
from sqlfeat.db import apply_indexes, apply_schema, connect

N_CUSTOMERS = 400
N_PRODUCTS = 40
PRIMARY_CUTOFF = datetime(2025, 7, 1, 0, 0, 0)
SECOND_CUTOFF = datetime(2025, 10, 1, 0, 0, 0)
LABEL_HORIZON_DAYS = 30
SENTINEL_AMOUNT = 99999.0
SENTINEL_EVENT_TYPE = "SENTINEL_FUTURE"
KNOWN_SENTINEL_CUSTOMERS = (1, 2, 3, 7, 11)

COUNTRIES = ("IN", "US", "GB", "DE", "SG")
SEGMENTS = ("A", "B", "C")
CATEGORIES = ("grocery", "electronics", "home", "apparel", "other")
CHANNELS = ("card", "ach", "wallet")
DEVICES = ("mobile", "desktop", "tablet")
EVENT_TYPES = ("login", "view", "add_to_cart", "purchase", "support")
ACCOUNT_TYPES = ("checking", "savings", "credit")

SIGNUP_START = datetime(2023, 1, 1, 0, 0, 0)
SIGNUP_END = datetime(2024, 6, 1, 0, 0, 0)
HISTORY_END = datetime(2025, 12, 1, 0, 0, 0)


def fmt_ts(value: datetime) -> str:
    """Format a timestamp at second precision for SQLite TEXT columns."""
    return value.replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")


def _uniform_datetime(rng: np.random.Generator, start: datetime, end: datetime) -> datetime:
    span = (end - start).total_seconds()
    if span <= 0:
        raise ValueError("end must be after start")
    offset = float(rng.uniform(0.0, span))
    return (start + timedelta(seconds=offset)).replace(microsecond=0)


def _clip_ts(value: datetime, start: datetime, end: datetime) -> datetime:
    if value < start:
        return start
    if value > end:
        return end
    return value.replace(microsecond=0)


def generate_frames(seed: int | np.random.Generator | None = DEFAULT_SEED) -> dict[str, pd.DataFrame]:
    """Build all laboratory tables as DataFrames.

    The returned dict is the DGP realisation. ``write_database`` loads it
    into SQLite.
    """
    rng = get_rng(seed)

    products = _products()
    customers = _customers(rng)
    accounts = _accounts(rng, customers)
    sessions = _sessions(rng, customers)
    events = _events(rng, customers, sessions, products)
    transactions = _transactions(rng, customers, accounts, products)
    orders = _orders(rng, customers, products, transactions)
    rank_demo = _rank_demo()
    segment_lookup = pd.DataFrame(
        {"segment": ["A", "B"], "risk_bucket": ["low", "medium"]}
    )

    predictions = _predictions(customers)
    transactions, events = _plant_same_day_after_cutoff(
        rng, transactions, events, accounts, products, customers
    )
    outcomes = _outcomes(predictions, orders)
    transactions, events = _plant_sentinels(
        transactions, events, accounts, products, predictions, outcomes
    )
    transactions_raw = _transactions_raw(rng, transactions)

    return {
        "products": products,
        "customers": customers,
        "accounts": accounts,
        "segment_lookup": segment_lookup,
        "rank_demo": rank_demo,
        "sessions": sessions,
        "events": events,
        "transactions": transactions,
        "orders": orders,
        "predictions": predictions,
        "outcomes": outcomes,
        "transactions_raw": transactions_raw,
    }


def populate(conn, seed: int | np.random.Generator | None = DEFAULT_SEED, *, with_indexes: bool = True) -> dict[str, pd.DataFrame]:
    """Create schema, insert the DGP, optionally add indexes.

    Insert order respects foreign keys.
    """
    apply_schema(conn)
    frames = generate_frames(seed)
    order = [
        "products",
        "customers",
        "accounts",
        "segment_lookup",
        "rank_demo",
        "sessions",
        "events",
        "transactions",
        "orders",
        "predictions",
        "outcomes",
        "transactions_raw",
    ]
    for name in order:
        frames[name].to_sql(name, conn, if_exists="append", index=False)
    if with_indexes:
        apply_indexes(conn)
    conn.commit()
    return frames


def write_database(
    path: str | Path,
    seed: int | np.random.Generator | None = DEFAULT_SEED,
    *,
    with_indexes: bool = True,
) -> Path:
    """Write a SQLite file at ``path`` and return that path."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    conn = connect(out)
    try:
        populate(conn, seed, with_indexes=with_indexes)
    finally:
        conn.close()
    return out


def _products() -> pd.DataFrame:
    rows = []
    for i in range(1, N_PRODUCTS + 1):
        rows.append(
            {
                "product_id": i,
                "category": CATEGORIES[(i - 1) % len(CATEGORIES)],
                "name": f"product_{i:02d}",
            }
        )
    return pd.DataFrame(rows)


def _customers(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for i in range(1, N_CUSTOMERS + 1):
        signup = _uniform_datetime(rng, SIGNUP_START, SIGNUP_END)
        referred_by = None
        if i > 1 and float(rng.random()) < 0.28:
            referred_by = int(rng.integers(1, i))
        segment: str | None
        if float(rng.random()) < 0.10:
            segment = None
        else:
            segment = str(SEGMENTS[int(rng.integers(0, len(SEGMENTS)))])
        rows.append(
            {
                "customer_id": i,
                "signup_ts": fmt_ts(signup),
                "referred_by": referred_by,
                "cohort_month": signup.strftime("%Y-%m"),
                "country": str(COUNTRIES[int(rng.integers(0, len(COUNTRIES)))]),
                "segment": segment,
            }
        )
    return pd.DataFrame(rows)


def _accounts(rng: np.random.Generator, customers: pd.DataFrame) -> pd.DataFrame:
    rows = []
    account_id = 1
    for rec in customers.itertuples(index=False):
        signup = datetime.strptime(rec.signup_ts, "%Y-%m-%d %H:%M:%S")
        n_acct = int(rng.integers(1, 4))
        parent_id = None
        for k in range(n_acct):
            opened = _clip_ts(
                signup + timedelta(days=int(rng.integers(0, 40))),
                signup,
                PRIMARY_CUTOFF,
            )
            parent = None if k == 0 else parent_id
            rows.append(
                {
                    "account_id": account_id,
                    "customer_id": int(rec.customer_id),
                    "parent_account_id": parent,
                    "opened_ts": fmt_ts(opened),
                    "account_type": str(ACCOUNT_TYPES[int(rng.integers(0, len(ACCOUNT_TYPES)))]),
                    "status": "open" if float(rng.random()) > 0.08 else "closed",
                }
            )
            if k == 0:
                parent_id = account_id
            account_id += 1
    return pd.DataFrame(rows)


def _sessions(rng: np.random.Generator, customers: pd.DataFrame) -> pd.DataFrame:
    rows = []
    session_id = 1
    for rec in customers.itertuples(index=False):
        signup = datetime.strptime(rec.signup_ts, "%Y-%m-%d %H:%M:%S")
        n_sess = int(rng.poisson(8)) + 2
        for _ in range(n_sess):
            ts = _uniform_datetime(rng, signup, HISTORY_END)
            duration = int(rng.integers(20, 1800))
            if float(rng.random()) < 0.04:
                duration_val: int | None = None
            else:
                duration_val = duration
            rows.append(
                {
                    "session_id": session_id,
                    "customer_id": int(rec.customer_id),
                    "session_ts": fmt_ts(ts),
                    "duration_sec": duration_val,
                    "pages": int(rng.integers(1, 18)),
                    "device": str(DEVICES[int(rng.integers(0, len(DEVICES)))]),
                }
            )
            session_id += 1
    return pd.DataFrame(rows)


def _typed_events(df: pd.DataFrame) -> pd.DataFrame:
    """Keep nullable integer ids so concat does not drop dtypes."""
    out = df.copy()
    if "session_id" in out.columns:
        out["session_id"] = out["session_id"].astype("Int64")
    if "product_id" in out.columns:
        out["product_id"] = out["product_id"].astype("Int64")
    return out


def _events(
    rng: np.random.Generator,
    customers: pd.DataFrame,
    sessions: pd.DataFrame,
    products: pd.DataFrame,
) -> pd.DataFrame:
    product_ids = products["product_id"].to_numpy()
    rows = []
    event_id = 1
    grouped = sessions.groupby("customer_id", sort=True)
    for rec in customers.itertuples(index=False):
        cust_sessions = grouped.get_group(int(rec.customer_id))
        for sess in cust_sessions.itertuples(index=False):
            n_ev = int(rng.integers(2, 6))
            base = datetime.strptime(sess.session_ts, "%Y-%m-%d %H:%M:%S")
            for j in range(n_ev):
                ts = base + timedelta(seconds=int(j * 40 + rng.integers(0, 30)))
                etype = str(EVENT_TYPES[int(rng.integers(0, len(EVENT_TYPES)))])
                prod = int(rng.choice(product_ids)) if etype in {"view", "add_to_cart", "purchase"} else None
                rows.append(
                    {
                        "event_id": event_id,
                        "customer_id": int(rec.customer_id),
                        "session_id": int(sess.session_id),
                        "event_ts": fmt_ts(ts),
                        "event_type": etype,
                        "product_id": prod,
                        "is_sentinel": 0,
                    }
                )
                event_id += 1
        n_loose = int(rng.integers(0, 3))
        signup = datetime.strptime(rec.signup_ts, "%Y-%m-%d %H:%M:%S")
        for _ in range(n_loose):
            ts = _uniform_datetime(rng, signup, HISTORY_END)
            rows.append(
                {
                    "event_id": event_id,
                    "customer_id": int(rec.customer_id),
                    "session_id": None,
                    "event_ts": fmt_ts(ts),
                    "event_type": "login",
                    "product_id": None,
                    "is_sentinel": 0,
                }
            )
            event_id += 1
    return _typed_events(pd.DataFrame(rows))


def _transactions(
    rng: np.random.Generator,
    customers: pd.DataFrame,
    accounts: pd.DataFrame,
    products: pd.DataFrame,
) -> pd.DataFrame:
    product_ids = products["product_id"].to_numpy()
    acct_groups = accounts.groupby("customer_id", sort=True)
    rows = []
    txn_id = 1
    for rec in customers.itertuples(index=False):
        signup = datetime.strptime(rec.signup_ts, "%Y-%m-%d %H:%M:%S")
        cust_accts = acct_groups.get_group(int(rec.customer_id))["account_id"].to_numpy()
        n_txn = int(rng.poisson(14)) + 3
        for _ in range(n_txn):
            ts = _uniform_datetime(rng, signup, HISTORY_END)
            amount = float(np.exp(rng.normal(3.2, 0.7)))
            amount = round(max(amount, 1.0), 2)
            prod = int(rng.choice(product_ids)) if float(rng.random()) > 0.08 else None
            rows.append(
                {
                    "txn_id": txn_id,
                    "account_id": int(rng.choice(cust_accts)),
                    "customer_id": int(rec.customer_id),
                    "product_id": prod,
                    "txn_ts": fmt_ts(ts),
                    "amount": amount,
                    "is_sentinel": 0,
                    "channel": str(CHANNELS[int(rng.integers(0, len(CHANNELS)))]),
                }
            )
            txn_id += 1
    return pd.DataFrame(rows)


def _orders(
    rng: np.random.Generator,
    customers: pd.DataFrame,
    products: pd.DataFrame,
    transactions: pd.DataFrame,
) -> pd.DataFrame:
    """Place completed orders with probability increasing in prior activity.

    Some orders have NULL status so LEFT JOIN / NULL tests have unmatched
    semantics. Label y is defined later from completed orders in the
    horizon window, not from this function's return directly.
    """
    product_ids = products["product_id"].to_numpy()
    txn_counts = transactions.groupby("customer_id").size()
    rows = []
    order_id = 1
    for rec in customers.itertuples(index=False):
        signup = datetime.strptime(rec.signup_ts, "%Y-%m-%d %H:%M:%S")
        activity = int(txn_counts.get(int(rec.customer_id), 0))
        n_ord = int(rng.poisson(max(activity / 8.0, 0.8))) + 1
        for _ in range(n_ord):
            ts = _uniform_datetime(rng, signup + timedelta(days=7), HISTORY_END)
            draw = float(rng.random())
            if draw < 0.78:
                status: str | None = "completed"
            elif draw < 0.90:
                status = "cancelled"
            else:
                status = None
            rows.append(
                {
                    "order_id": order_id,
                    "customer_id": int(rec.customer_id),
                    "product_id": int(rng.choice(product_ids)),
                    "order_ts": fmt_ts(ts),
                    "amount": round(float(np.exp(rng.normal(3.4, 0.6))), 2),
                    "status": status,
                }
            )
            order_id += 1
    return pd.DataFrame(rows)


def _predictions(customers: pd.DataFrame) -> pd.DataFrame:
    rows = []
    prediction_id = 1
    primary = fmt_ts(PRIMARY_CUTOFF)
    secondary = fmt_ts(SECOND_CUTOFF)
    for rec in customers.itertuples(index=False):
        rows.append(
            {
                "prediction_id": prediction_id,
                "customer_id": int(rec.customer_id),
                "cutoff_ts": primary,
                "as_of_date": PRIMARY_CUTOFF.strftime("%Y-%m-%d"),
            }
        )
        prediction_id += 1
        if int(rec.customer_id) % 5 < 2:
            rows.append(
                {
                    "prediction_id": prediction_id,
                    "customer_id": int(rec.customer_id),
                    "cutoff_ts": secondary,
                    "as_of_date": SECOND_CUTOFF.strftime("%Y-%m-%d"),
                }
            )
            prediction_id += 1
    return pd.DataFrame(rows)


def _outcomes(predictions: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    completed = orders.loc[orders["status"] == "completed", ["customer_id", "order_ts"]].copy()
    completed["order_ts_dt"] = pd.to_datetime(completed["order_ts"])
    rows = []
    for rec in predictions.itertuples(index=False):
        cutoff = datetime.strptime(rec.cutoff_ts, "%Y-%m-%d %H:%M:%S")
        label_ts = cutoff + timedelta(days=LABEL_HORIZON_DAYS)
        cust = completed.loc[completed["customer_id"] == rec.customer_id]
        in_window = cust[
            (cust["order_ts_dt"] > cutoff) & (cust["order_ts_dt"] <= label_ts)
        ]
        y = 1 if len(in_window) > 0 else 0
        rows.append(
            {
                "prediction_id": int(rec.prediction_id),
                "customer_id": int(rec.customer_id),
                "cutoff_ts": rec.cutoff_ts,
                "label_ts": fmt_ts(label_ts),
                "y": y,
            }
        )
    return pd.DataFrame(rows)


def _plant_same_day_after_cutoff(
    rng: np.random.Generator,
    transactions: pd.DataFrame,
    events: pd.DataFrame,
    accounts: pd.DataFrame,
    products: pd.DataFrame,
    customers: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Add events on the cutoff calendar day but after midnight cutoff.

    A query that truncates to dates will include these rows. A query that
    compares timestamps to ``cutoff_ts`` will not.
    """
    txn_id = int(transactions["txn_id"].max()) + 1
    event_id = int(events["event_id"].max()) + 1
    product_ids = products["product_id"].to_numpy()
    acct_groups = accounts.groupby("customer_id")
    txn_rows = []
    ev_rows = []
    chosen = customers["customer_id"].to_numpy()[:50]
    same_day = PRIMARY_CUTOFF + timedelta(hours=16, minutes=30)
    for cid in chosen:
        cust_accts = acct_groups.get_group(int(cid))["account_id"].to_numpy()
        txn_rows.append(
            {
                "txn_id": txn_id,
                "account_id": int(rng.choice(cust_accts)),
                "customer_id": int(cid),
                "product_id": int(rng.choice(product_ids)),
                "txn_ts": fmt_ts(same_day),
                "amount": round(float(rng.uniform(40.0, 90.0)), 2),
                "is_sentinel": 0,
                "channel": "card",
            }
        )
        txn_id += 1
        ev_rows.append(
            {
                "event_id": event_id,
                "customer_id": int(cid),
                "session_id": None,
                "event_ts": fmt_ts(same_day),
                "event_type": "view",
                "product_id": int(rng.choice(product_ids)),
                "is_sentinel": 0,
            }
        )
        event_id += 1
    transactions = pd.concat([transactions, pd.DataFrame(txn_rows)], ignore_index=True)
    events = pd.concat([events, _typed_events(pd.DataFrame(ev_rows))], ignore_index=True)
    return transactions, events


def _plant_sentinels(
    transactions: pd.DataFrame,
    events: pd.DataFrame,
    accounts: pd.DataFrame,
    products: pd.DataFrame,
    predictions: pd.DataFrame,
    outcomes: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Insert future-only rows that correct PIT queries must not see at the primary cutoff.

    Sentinels are planted seven days after the primary cutoff for:
    - every known sentinel customer id
    - every primary-cutoff row with y = 1

    Amount ``SENTINEL_AMOUNT`` is unique in the DGP. At a later cutoff
    the same rows are ordinary history.
    """
    primary_pred = predictions.loc[predictions["cutoff_ts"] == fmt_ts(PRIMARY_CUTOFF)]
    primary_y = outcomes.merge(primary_pred[["prediction_id"]], on="prediction_id")
    positive = set(primary_y.loc[primary_y["y"] == 1, "customer_id"].tolist())
    planted = sorted(set(KNOWN_SENTINEL_CUSTOMERS) | positive)

    txn_id = int(transactions["txn_id"].max()) + 1
    event_id = int(events["event_id"].max()) + 1
    product_ids = products["product_id"].to_numpy()
    acct_groups = accounts.groupby("customer_id")
    txn_rows = []
    ev_rows = []
    sentinel_ts = PRIMARY_CUTOFF + timedelta(days=7, hours=3)
    if not (sentinel_ts > PRIMARY_CUTOFF):
        raise ValueError("sentinel timestamp must be strictly after cutoff")
    for cid in planted:
        cust_accts = acct_groups.get_group(int(cid))["account_id"].to_numpy()
        txn_rows.append(
            {
                "txn_id": txn_id,
                "account_id": int(cust_accts[0]),
                "customer_id": int(cid),
                "product_id": int(product_ids[0]),
                "txn_ts": fmt_ts(sentinel_ts),
                "amount": SENTINEL_AMOUNT,
                "is_sentinel": 1,
                "channel": "wallet",
            }
        )
        txn_id += 1
        ev_rows.append(
            {
                "event_id": event_id,
                "customer_id": int(cid),
                "session_id": None,
                "event_ts": fmt_ts(sentinel_ts),
                "event_type": SENTINEL_EVENT_TYPE,
                "product_id": int(product_ids[0]),
                "is_sentinel": 1,
            }
        )
        event_id += 1
    transactions = pd.concat([transactions, pd.DataFrame(txn_rows)], ignore_index=True)
    events = pd.concat([events, _typed_events(pd.DataFrame(ev_rows))], ignore_index=True)
    return transactions, events


def _transactions_raw(rng: np.random.Generator, transactions: pd.DataFrame) -> pd.DataFrame:
    """Duplicate a subset of transactions with a later ingest time.

    Dedup by ``ROW_NUMBER() ... ORDER BY ingested_ts DESC`` must keep one
    row per ``txn_id``. The later ingest carries a perturbed amount so a
    wrong dedup is detectable.
    """
    rows = []
    raw_id = 1
    for rec in transactions.itertuples(index=False):
        ingest = datetime.strptime(rec.txn_ts, "%Y-%m-%d %H:%M:%S") + timedelta(minutes=5)
        rows.append(
            {
                "raw_id": raw_id,
                "txn_id": int(rec.txn_id),
                "account_id": int(rec.account_id),
                "customer_id": int(rec.customer_id),
                "product_id": rec.product_id if pd.notna(rec.product_id) else None,
                "txn_ts": rec.txn_ts,
                "amount": float(rec.amount),
                "ingested_ts": fmt_ts(ingest),
                "channel": rec.channel,
            }
        )
        raw_id += 1
        if int(rec.txn_id) % 11 == 0:
            later = ingest + timedelta(hours=2)
            rows.append(
                {
                    "raw_id": raw_id,
                    "txn_id": int(rec.txn_id),
                    "account_id": int(rec.account_id),
                    "customer_id": int(rec.customer_id),
                    "product_id": rec.product_id if pd.notna(rec.product_id) else None,
                    "txn_ts": rec.txn_ts,
                    "amount": round(float(rec.amount) + 0.17, 2),
                    "ingested_ts": fmt_ts(later),
                    "channel": rec.channel,
                }
            )
            raw_id += 1
    _ = rng
    return pd.DataFrame(rows)


def _rank_demo() -> pd.DataFrame:
    """Known-tie scores so ROW_NUMBER, RANK, and DENSE_RANK disagree."""
    return pd.DataFrame(
        {
            "player_id": [1, 2, 3, 4, 5],
            "player": ["ann", "ben", "cam", "drew", "eve"],
            "score": [30, 20, 20, 20, 10],
        }
    )


def counts_by_table(frames: dict[str, pd.DataFrame]) -> dict[str, int]:
    """Return row counts for each generated table."""
    return {name: int(len(df)) for name, df in frames.items()}
