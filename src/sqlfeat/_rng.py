"""Shared random-number construction.

Every generator and Monte Carlo routine in this package accepts either
an integer seed or a ``numpy.random.Generator``. Passing a seed makes
the draw sequence reproducible. Passing an existing generator lets a
caller share state across several steps without resetting it.
"""

from __future__ import annotations

import numpy as np

DEFAULT_SEED = 2026


def get_rng(seed: int | np.random.Generator | None = DEFAULT_SEED) -> np.random.Generator:
    """Return a NumPy Generator.

    Parameters
    ----------
    seed
        Integer seed, an existing Generator, or ``None`` for
        non-reproducible draws from the OS entropy pool.
    """
    if isinstance(seed, np.random.Generator):
        return seed
    if seed is None:
        return np.random.default_rng()
    return np.random.default_rng(int(seed))
