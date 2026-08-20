"""Run the laboratory demonstrations and write figures and tables.

Numerical results printed here are computed on the synthetic DGP.
They are not empirical findings about real customers.

Usage, from the repository root::

    python scripts/run_all.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sqlfeat.cases import (
    case_a_groupby_vs_window,
    case_b_dedup,
    case_c_cohort,
    case_d_ranking,
    case_e_lag_vs_lead,
    case_f_pit_training,
    case_g_pandas_parity,
)
from sqlfeat.db import connect, table_count
from sqlfeat.explain import explain_pit_probe
from sqlfeat.features import load_training_tables
from sqlfeat.flagship import evaluate_flagship
from sqlfeat.generate import DEFAULT_SEED, PRIMARY_CUTOFF, fmt_ts, populate
from sqlfeat.leakage import sentinel_report


def _print_header(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def main() -> None:
    fig_dir = ROOT / "outputs" / "figures"
    tab_dir = ROOT / "outputs" / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tab_dir.mkdir(parents=True, exist_ok=True)

    conn = connect(None)
    populate(conn, seed=DEFAULT_SEED, with_indexes=True)

    rows: list[dict[str, object]] = []

    _print_header("A. GROUP BY vs window")
    a = case_a_groupby_vs_window(conn)
    print(
        f"Transaction rows={a.n_txn_rows}; window query rows={a.window_rows}; "
        f"GROUP BY customer rows={a.totals_rows}"
    )
    print("GROUP BY drops txn-level amount. The window keeps the txn grain.")
    rows.append({"quantity": "n_txn", "value": a.n_txn_rows})
    rows.append({"quantity": "n_groupby_customers", "value": a.totals_rows})

    _print_header("B. Dedup with ROW_NUMBER")
    b = case_b_dedup(conn)
    print(f"transactions_raw={b.n_raw}; deduped={b.n_deduped}; clean transactions={b.n_txn}")
    rows.append({"quantity": "n_raw", "value": b.n_raw})
    rows.append({"quantity": "n_deduped", "value": b.n_deduped})

    _print_header("C. Cohort / retention-style table")
    cohort = case_c_cohort(conn)
    print(f"Cohort-month x activity-month rows={len(cohort)}")
    cohort.to_csv(tab_dir / "cohort_retention.csv", index=False)

    _print_header("D. ROW_NUMBER vs RANK vs DENSE_RANK")
    ranks = case_d_ranking(conn)
    print(ranks.to_string(index=False))
    ranks.to_csv(tab_dir / "rank_demo.csv", index=False)

    _print_header("E. LAG vs LEAD")
    e = case_e_lag_vs_lead(conn)
    print(
        f"Rows with lag_y={e.n_with_lag}; LEAD amounts={e.n_with_lead}; "
        f"LEAD timestamps after cutoff={e.n_lead_after_cutoff}"
    )
    print("LAG of an already-observed outcome can be a feature. LEAD of a later txn is not.")
    rows.append({"quantity": "n_lead_after_cutoff", "value": e.n_lead_after_cutoff})

    _print_header("F. Point-in-time training table")
    pit = case_f_pit_training(conn)
    print(f"PIT rows={len(pit)}; prevalence={float(pit['y'].mean()):.3f}")
    primary = pit.loc[pit["cutoff_ts"] == fmt_ts(PRIMARY_CUTOFF)]
    print(
        "sentinel_spend all zero on correct table at primary cutoff: "
        f"{(primary['sentinel_spend'].fillna(0)==0).all()}"
    )
    rows.append({"quantity": "n_pit_rows", "value": len(pit)})
    rows.append({"quantity": "prevalence", "value": float(pit["y"].mean())})

    _print_header("G. SQL vs pandas")
    sql_part, pandas_part = case_g_pandas_parity(conn)
    spend_delta = (sql_part["spend_30"] - pandas_part["spend_30"]).abs().max()
    print(f"Max |SQL spend_30 - pandas spend_30| = {float(spend_delta):.8f}")
    rows.append({"quantity": "sql_pandas_spend30_max_abs", "value": float(spend_delta)})

    _print_header("H. EXPLAIN QUERY PLAN")
    plans = explain_pit_probe(conn)
    print(f"SQLite {plans.sqlite_version}")
    print("--- without laboratory indexes ---")
    print(plans.without_indexes)
    print("--- with laboratory indexes ---")
    print(plans.with_indexes)
    (tab_dir / "explain_plans.txt").write_text(
        f"sqlite_version={plans.sqlite_version}\n\n"
        f"WITHOUT INDEXES\n{plans.without_indexes}\n\n"
        f"WITH INDEXES\n{plans.with_indexes}\n",
        encoding="utf-8",
    )

    _print_header("Flagship: leaky vs correct in-sample logistic")
    tables = load_training_tables(conn)
    flag = evaluate_flagship(tables.correct, tables.leaky, seed=DEFAULT_SEED)
    sent = sentinel_report(tables.correct, tables.leaky)
    print(
        f"n={flag.n_rows} prevalence={flag.prevalence:.3f} "
        f"AUC_correct={flag.auc_correct:.3f} AUC_leaky={flag.auc_leaky:.3f} "
        f"gap={flag.auc_gap:.3f}"
    )
    print(
        f"sentinel nonzero rows: correct={sent.n_correct_nonzero} "
        f"leaky={sent.n_leaky_nonzero}"
    )
    print("In-sample AUC here is a leakage diagnostic, not a skill claim.")
    rows.append({"quantity": "auc_correct", "value": flag.auc_correct})
    rows.append({"quantity": "auc_leaky", "value": flag.auc_leaky})
    rows.append({"quantity": "auc_gap", "value": flag.auc_gap})

    summary = pd.DataFrame(rows)
    summary.to_csv(tab_dir / "run_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.bar(
        ["correct PIT", "leaky"],
        [flag.auc_correct, flag.auc_leaky],
        color=["#4C78A8", "#E45756"],
    )
    ax.set_ylabel("in-sample ROC AUC")
    ax.set_ylim(0.45, 1.0)
    ax.set_title("Simulated DGP: leaky table inflates in-sample AUC")
    ax.axhline(0.5, color="grey", linewidth=0.8, linestyle="--")
    fig.tight_layout()
    fig.savefig(fig_dir / "flagship_auc.png", dpi=140)
    plt.close(fig)

    print()
    print(f"customers={table_count(conn, 'customers')} transactions={table_count(conn, 'transactions')}")
    print(f"Wrote { (tab_dir / 'run_summary.csv').relative_to(ROOT) }")
    print(f"Wrote figures under {fig_dir.relative_to(ROOT)}")
    print("Done.")
    conn.close()


if __name__ == "__main__":
    main()
