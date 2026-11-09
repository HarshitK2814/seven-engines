"""E1 (EXPLORATORY): two-state Gaussian HMM on monthly [blend, SPY] returns, refit each January on past months only.
State at month t is the filtered (forward) probability using months up to and including t, so it is known at the
close of t. Stress state = the state with the higher SPY variance in the fitted model. Not a headline result."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd


def _fit(train: pd.DataFrame):
    from hmmlearn.hmm import GaussianHMM
    mu, sd = train.mean(), train.std(ddof=1)
    mdl = GaussianHMM(n_components=2, covariance_type="diag", random_state=0, n_iter=200)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mdl.fit(((train - mu) / sd).to_numpy())
    spy_var = mdl.covars_[:, -1] if mdl.covars_.ndim == 2 else np.array([c[-1, -1] for c in mdl.covars_])
    return mdl, mu, sd, int(np.argmax(spy_var))


def stress_states(X: pd.DataFrame, min_months: int = 60) -> tuple[pd.Series, dict]:
    """X columns: [blend, spy] monthly. Returns (state 1=stress/0=calm per month, NaN before the first fit;
    {refit_date: Viterbi state sequence of the training window, 1=stress}). Only past data enters each fit."""
    states = pd.Series(np.nan, index=X.index)
    train_states = {}
    for i, d in enumerate(X.index):
        if d.month != 1 or i < min_months:
            continue
        mdl, mu, sd, stress = _fit(X.iloc[:i])
        train_states[d] = pd.Series((mdl.predict(((X.iloc[:i] - mu) / sd).to_numpy()) == stress).astype(float),
                                    index=X.index[:i])
        for j in range(i, len(X)):
            if X.index[j].year != d.year:
                break
            p = mdl.predict_proba(((X.iloc[:j + 1] - mu) / sd).to_numpy())[-1]   # filtered: last row sees only <= j
            states.iloc[j] = float(p[stress] > 0.5)
    return states, train_states


def best_stress_styles(S: pd.DataFrame, train_state: pd.Series, k: int = 2) -> list[str]:
    """The k styles with the best mean return in the stress-state months of the (past) training window."""
    st = train_state[train_state == 1].index.intersection(S.index)
    if len(st) == 0:
        return list(S.columns[:k])
    return list(S.loc[st].mean().sort_values(ascending=False).index[:k])


def tilted_returns(S: pd.DataFrame, states: pd.Series, picks: dict, tilt: float = 0.5) -> pd.DataFrame:
    """Return of month t+1 uses the state known at the close of t. Base = equal weight over styles with data;
    tilt = in the stress state multiply the weight of the picked styles by (1 + tilt), renormalise.
    `picks` maps a refit date to its picked styles; the latest refit on or before t applies. Costs of the tilt omitted."""
    pk_dates = sorted(picks)
    rows = {}
    for t in range(len(S.index) - 1):
        d, nxt = S.index[t], S.index[t + 1]
        r = S.iloc[t + 1]
        avail = r.notna()
        if not avail.any():
            continue
        w = avail.astype(float)
        w = w / w.sum()
        base = float((w * r.fillna(0.0)).sum())
        s = states.get(d, np.nan)
        dd = [x for x in pk_dates if x <= d]
        if np.isnan(s):
            rows[nxt] = {"base": base, "tilt": np.nan}
            continue
        w2 = w.copy()
        if s == 1 and dd:
            for c in picks[dd[-1]]:
                if c in w2.index and avail[c]:
                    w2[c] *= (1 + tilt)
            w2 = w2 / w2.sum()
        rows[nxt] = {"base": base, "tilt": float((w2 * r.fillna(0.0)).sum())}
    return pd.DataFrame(rows).T
