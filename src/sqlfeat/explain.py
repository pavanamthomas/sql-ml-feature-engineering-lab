"""SQLite EXPLAIN QUERY PLAN text, not wall-clock latency.

Plans can change across SQLite versions. Index presence is checked by
whether the plan string changes, not by timing.
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
