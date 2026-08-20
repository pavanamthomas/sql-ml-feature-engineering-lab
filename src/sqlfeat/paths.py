"""Repository paths.

SQL files live at the repository root under ``sql/``, not inside the
installed package. Editable installs (``pip install -e .``) keep that
layout. Tests and scripts resolve files from this helper.
"""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Return the repository root (parent of ``src/``)."""
    return Path(__file__).resolve().parents[2]


def sql_dir() -> Path:
    """Return the directory that holds ``schema.sql`` and query files."""
    path = repo_root() / "sql"
    if not path.is_dir():
        raise FileNotFoundError(f"sql directory not found at {path}")
    return path


def load_sql(relative: str) -> str:
    """Read a SQL file relative to ``sql/``.

    Parameters
    ----------
    relative
        Path such as ``correct/txn_counts.sql`` or ``schema.sql``.
    """
    path = sql_dir() / relative
    if not path.is_file():
        raise FileNotFoundError(f"SQL file not found: {path}")
    return path.read_text(encoding="utf-8")
