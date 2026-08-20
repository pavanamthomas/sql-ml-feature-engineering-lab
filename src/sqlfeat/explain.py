"""SQLite EXPLAIN QUERY PLAN helpers.

Problem: record whether a point-in-time join is planned as a scan or as
an index search. The artefact is the plan text, not a latency number.

Assumptions: SQLite ``EXPLAIN QUERY PLAN`` vocabulary (SCAN, SEARCH,
USING INDEX, COVERING INDEX) is the object of interest. Plans can
change across SQLite versions.

Why not wall-clock times: they are machine-specific and are not a
property of the query. This laboratory does not invent production
latency.

Alternative: ``EXPLAIN`` (opcodes) or a PostgreSQL ``EXPLAIN ANALYZE``
on another engine. Out of scope for CI.

How checked: tests assert that creating ``idx_txn_customer_ts`` changes
the plan string for the probe query to mention that index.

What can be concluded: on this SQLite build, the named index is used
in the plan after it is created.

What cannot: a millisecond budget, or that PostgreSQL will choose the
same join order.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlfeat.db import apply_indexes, drop_laboratory_indexes
from sqlfeat.paths import load_sql


@dataclass(frozen=True)
class ExplainPair:
    without_indexes: str
    with_indexes: str
    sqlite_version: str


def _strip_full_line_comments(sql: str) -> str:
    """Drop blank lines and full-line ``--`` comments so EXPLAIN can prepend."""
    keep = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped == "" or stripped.startswith("--"):
            continue
        keep.append(line)
    return "\n".join(keep)


def explain_query_plan(conn, sql: str) -> str:
    """Return EXPLAIN QUERY PLAN as a newline-joined string."""
    statement = _strip_full_line_comments(sql).strip().rstrip(";")
    rows = conn.execute("EXPLAIN QUERY PLAN " + statement).fetchall()
    lines = []
    for row in rows:
        # SQLite 3: (id, parent, notused, detail) or Row mapping.
        detail = row["detail"] if "detail" in row.keys() else row[-1]
        lines.append(str(detail))
    return "\n".join(lines)


def explain_pit_probe(conn) -> ExplainPair:
    """Explain the PIT probe before and after laboratory indexes."""
    probe = load_sql("correct/pit_explain_probe.sql").strip().rstrip(";")
    version = str(conn.execute("SELECT sqlite_version()").fetchone()[0])
    drop_laboratory_indexes(conn)
    without = explain_query_plan(conn, probe)
    apply_indexes(conn)
    with_idx = explain_query_plan(conn, probe)
    return ExplainPair(without_indexes=without, with_indexes=with_idx, sqlite_version=version)
