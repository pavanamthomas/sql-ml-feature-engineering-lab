"""Shared SQLite laboratory fixture.

One in-memory database per test session, seed 2026. Tests that check
reproducibility open their own connections.
"""

from __future__ import annotations

import pytest

from sqlfeat.db import connect
from sqlfeat.generate import DEFAULT_SEED, populate


@pytest.fixture(scope="session")
def conn():
    connection = connect(None)
    populate(connection, seed=DEFAULT_SEED, with_indexes=True)
    yield connection
    connection.close()
