"""Style allocation (D2): equal, inverse-vol, HRP (Ledoit-Wolf covariance) and trailing-net-Sharpe weights.

Rebalanced once a year at the first month-end of each year. The weight is computed from the trailing `lookback`
months up to and including that month-end and applies from the next calendar day. A style needs a full
lookback window of returns to be allocated; otherwise it gets weight 0 at that rebalance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

METHODS = ("equal", "invvol", "hrp", "sharpe")


def _weights(X: pd.DataFrame, method: str) -> pd.Series:
    n = X.shape[1]
    if n == 1 or method == "equal":
        return pd.Series(1.0 / n, index=X.columns)
    if method == "invvol":
        w = 1.0 / X.std(ddof=1)
    elif method == "sharpe":
        sr = (X.mean() / X.std(ddof=1)).clip(lower=0.0)
        w = sr if sr.sum() > 0 else pd.Series(1.0, index=X.columns)
    elif method == "hrp":
        from skfolio.moments import LedoitWolf
        from skfolio.optimization import HierarchicalRiskParity
        from skfolio.prior import EmpiricalPrior
        mdl = HierarchicalRiskParity(prior_estimator=EmpiricalPrior(covariance_estimator=LedoitWolf()))
        w = pd.Series(np.asarray(mdl.fit(X).weights_), index=X.columns)
    else:
        raise ValueError(method)
    return w / w.sum()


def rolling_alloc(style_monthly: pd.DataFrame, method: str, lookback: int = 36) -> pd.DataFrame:
    if method not in METHODS:
        raise ValueError(method)
    m = style_monthly
    first_me = m.index.to_series().groupby(m.index.year).first()
    rows = {}
    for d in first_me:
        pos = m.index.get_loc(d)
        if pos + 1 < lookback:
            continue
        win = m.iloc[pos + 1 - lookback: pos + 1]
        ok = win.columns[win.notna().all()]
        if len(ok) == 0:
            continue
        w = pd.Series(0.0, index=m.columns)
        w[ok] = _weights(win[ok], method)
        rows[d + pd.Timedelta(days=1)] = w
    return pd.DataFrame(rows).T
