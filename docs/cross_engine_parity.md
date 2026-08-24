# Cross-engine point-in-time parity

The main laboratory already compares SQL features with an independent Pandas calculation. This extension adds a second SQL execution engine for a deliberately small fixture so dialect differences can be tested rather than discussed only in prose.

The fixture contains three prediction cutoffs and four transactions. Customer 1 has two historical transactions worth 10 and 20, plus a post-cutoff sentinel worth 99999. Customer 2 has one historical transaction. Customer 3 has no transaction history.

Both SQLite and DuckDB must therefore return the same customer-level objects:

- customer 1: count 2, spend 30, recency 1 day;
- customer 2: count 1, spend 7.5, recency 5 days;
- customer 3: count 0, spend 0, recency NULL.

The 99999 sentinel is not an ML metric. It is a direct information-set test: if it appears in the historical feature table, the cutoff predicate failed before any model is fitted.

The third route is Pandas. It iterates over prediction rows and explicitly filters transactions to the customer's id and timestamp at or before the cutoff. That implementation does not execute either SQL statement.

A second fixture checks `ROW_NUMBER`, `RANK`, and `DENSE_RANK` on a known tie pattern. This matters because matching column names across engines is not enough; window semantics must also agree on the object being computed.

## What this supports

- deterministic SQLite/DuckDB equality for the tested point-in-time aggregates;
- an independent Pandas calculation of the same feature object;
- explicit NULL/no-history behavior;
- a future-only sentinel that must remain excluded;
- cross-engine checks of basic ranking-window semantics.

## What it does not support

- full SQLite/DuckDB/PostgreSQL dialect equivalence;
- equivalence of query optimizers or execution plans;
- point-in-time correctness under late-arriving data, because event time is not ingest time;
- time-zone correctness;
- feature-store or warehouse claims.

The purpose is not to add another database name to the README. The purpose is to make one information-set definition survive a second SQL engine and an independent non-SQL calculation.

The DuckDB path executes the compact fixture SQL in `src/sqlfeat/cross_engine.py`. It does not re-run every file under `sql/correct/`. Those files remain SQLite-plus-Pandas checks. Cross-engine agreement on this fixture is not a claim that the main laboratory SQL has been ported to DuckDB or PostgreSQL.
