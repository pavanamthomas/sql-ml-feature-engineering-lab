# Contributing to the SQL feature lab

Useful work is a time predicate that actually withholds post-cutoff events, or a sentinel that fires without using the label column.

1. Open an issue naming the cutoff, the grain, and the leak (usually a missing `txn_ts <= cutoff`).
2. Add a failing test before a numerical change.
3. Keep commits to one information-set claim.
4. Comment as-of joins and window frames, not obvious SELECT lists.

See `FLAGSHIP_POINT_IN_TIME_FAILURE.md`, `docs/cross_engine_parity.md`, `ROADMAP.md`, and `.github/workflows/ci.yml`.
