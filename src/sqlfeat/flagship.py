"""Flagship comparison: leaky versus correct training tables.

Problem: two pipelines can emit similarly named columns while one
includes the label window. Apparent classification performance then
rises without any change in the estimator.

Assumptions: ``y`` is a completed order in the 30 days after cutoff;
the leaky table's ``spend_30`` / ``txn_count_30`` include post-cutoff
transactions; the model is in-sample logistic regression on a fixed
column list. In-sample AUC is a diagnostic of leakage, not a claim of
out-of-sample skill.

Why logistic regression: it is a linear baseline. If leakage inflates
fit here, a more flexible model is not required to see the artefact.

Alternative: report only the sentinel test. That catches planted rows
but does not show why a reviewer might believe the leaky table.

What can go wrong: quoting the leaky AUC as model quality; using
``lead_y`` as a feature and calling it a covariate.

How checked: sentinel spend is zero on the correct table at the
primary cutoff and positive on the leaky table there; leaky AUC
exceeds correct AUC on this DGP.

What can be concluded: on this DGP, including post-cutoff transactions
inflates in-sample AUC relative to the point-in-time table.

What cannot: a real-world lift, a causal effect of any feature, or a
ranking of production models.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from sqlfeat.generate import PRIMARY_CUTOFF, fmt_ts

FEATURE_COLUMNS = (
    "txn_count_7",
    "txn_count_30",
    "spend_7",
    "spend_30",
    "tenure_days",
    "recency_days",
    "n_sessions_30",
)


@dataclass(frozen=True)
class FlagshipResult:
    n_rows: int
    prevalence: float
    auc_correct: float
    auc_leaky: float
    auc_gap: float
    n_correct_sentinel: int
    n_leaky_sentinel: int


def _design_matrix(frame: pd.DataFrame) -> tuple[NDArray[np.float64], NDArray[np.int32]]:
    missing = [c for c in FEATURE_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"training table missing columns: {missing}")
    x = frame.loc[:, list(FEATURE_COLUMNS)].copy()
    # Recency NULL means no prior txn. For the linear model only, fill
    # with the column median. This is a model-matrix convention, not the
    # SQL/pandas feature-store policy (which keeps recency NULL).
    if x["recency_days"].isna().all():
        x["recency_days"] = 0.0
    else:
        x["recency_days"] = x["recency_days"].fillna(float(x["recency_days"].median()))
    x = x.fillna(0.0)
    y = frame["y"].to_numpy(dtype=np.int32)
    return x.to_numpy(dtype=np.float64), y


def fit_in_sample_auc(frame: pd.DataFrame, seed: int = 2026) -> float:
    """In-sample ROC AUC of a scaled logistic regression.

    The fit uses the same rows it scores. That is intentional: the
    quantity of interest is leakage-driven separability, not generalisation.
    """
    x, y = _design_matrix(frame)
    if len(np.unique(y)) < 2:
        raise ValueError("need both classes to compute ROC AUC")
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    max_iter=500,
                    solver="lbfgs",
                    random_state=seed,
                ),
            ),
        ]
    )
    pipe.fit(x, y)
    scores = pipe.predict_proba(x)[:, 1]
    return float(roc_auc_score(y, scores))


def evaluate_flagship(correct: pd.DataFrame, leaky: pd.DataFrame, seed: int = 2026) -> FlagshipResult:
    """Compare in-sample AUC and sentinel visibility on the two tables."""
    if len(correct) != len(leaky):
        raise ValueError("correct and leaky tables must have the same number of rows")
    auc_c = fit_in_sample_auc(correct, seed=seed)
    auc_l = fit_in_sample_auc(leaky, seed=seed)
    cutoff = fmt_ts(PRIMARY_CUTOFF)
    c_primary = correct.loc[correct["cutoff_ts"] == cutoff]
    l_primary = leaky.loc[leaky["cutoff_ts"] == cutoff]
    return FlagshipResult(
        n_rows=len(correct),
        prevalence=float(correct["y"].mean()),
        auc_correct=auc_c,
        auc_leaky=auc_l,
        auc_gap=auc_l - auc_c,
        n_correct_sentinel=int((c_primary["sentinel_spend"].fillna(0) > 0).sum()),
        n_leaky_sentinel=int((l_primary["sentinel_spend"].fillna(0) > 0).sum()),
    )
