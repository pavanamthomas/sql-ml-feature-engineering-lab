"""Point-in-time SQL feature engineering laboratory.

Synthetic relational events, correct and leaky queries, and tests that
distinguish them with planted future-only sentinels. Nothing here is an
empirical finding about real customers.
"""

from sqlfeat.flagship import FlagshipResult, evaluate_flagship
from sqlfeat.generate import (
    DEFAULT_SEED,
    N_CUSTOMERS,
    SENTINEL_AMOUNT,
    generate_frames,
    populate,
    write_database,
)
from sqlfeat.leakage import assert_correct_excludes_sentinels, assert_leaky_includes_sentinels
from sqlfeat.pandas_features import FILLNA, pandas_pit_features

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_SEED",
    "FILLNA",
    "FlagshipResult",
    "N_CUSTOMERS",
    "SENTINEL_AMOUNT",
    "assert_correct_excludes_sentinels",
    "assert_leaky_includes_sentinels",
    "evaluate_flagship",
    "generate_frames",
    "pandas_pit_features",
    "populate",
    "write_database",
]
