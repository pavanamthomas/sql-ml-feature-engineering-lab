# Still not modelled

DuckDB is in CI on the compact point-in-time fixture. SQLite remains the main path.

Event time ≠ ingest time. A row with event time before cutoff and ingestion after cutoff still passes an event-time predicate. I have not built late-arriving facts.

No time zones. Timestamps in the DGP are naive UTC-style strings.

No Postgres in CI. DuckDB is a second SQL engine, not a guarantee of PostgreSQL equivalence. Query-plan parity is not claimed — I check result semantics on deterministic fixtures.

I am not treating simulated AUC as a production result, and I am not building a feature store.

`docs/cross_engine_parity.md` if you want the fixture bounds.
