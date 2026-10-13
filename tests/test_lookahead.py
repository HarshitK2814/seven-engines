"""Changing data after date D must not change any signal or weight decided at or before D."""

import numpy as np
import pandas as pd

from multistyle import model

COLS = ["ES=F", "NKD=F", "^STOXX50E", "^FTSE", "UST2", "UST10", "UST20", "EUR", "JPY", "AUD", "CL=F", "GC=F", "HG=F"]
SECT = ["equity"] * 4 + ["rates"] * 3 + ["fx"] * 3 + ["energy", "metals", "metals"]


def _toy(n=1700, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2000-01-03", periods=n)
    R = pd.DataFrame(rng.normal(0.0002, 0.01, (n, len(COLS))), index=idx, columns=COLS)
    V = pd.DataFrame(np.exp(rng.normal(10, 0.3, (n, len(COLS)))), index=idx, columns=COLS)
    inst = pd.DataFrame({"sector": SECT, "cost_bp": 1.0, "rolls": 4}, index=COLS)
    macro = {"fx_rates": pd.DataFrame({"USD": 0.03, "EUR": 0.02, "JPY": 0.0, "AUD": 0.05}, index=idx),
             "yields": pd.DataFrame({"UST2": 0.03, "UST10": 0.04, "UST20": 0.045}, index=idx)
             + rng.normal(0, 0.001, (n, 3)).cumsum(axis=0) * 0.01,
             "bill": pd.Series(0.025, index=idx)}
    return R, V, inst, macro


def test_no_lookahead():
    R, V, inst, macro = _toy()
    cut = R.index[1500]
    later = R.index > cut
    R2, V2 = R.copy(), V.copy()
    R2.loc[later] += np.linspace(0.01, 0.05, later.sum())[:, None]
    V2.loc[later] *= 3
    m2 = {**macro, "yields": macro["yields"].copy(), "fx_rates": macro["fx_rates"].copy()}
    m2["yields"].loc[later] += 0.02
    m2["fx_rates"].loc[later, "EUR"] = 0.09
    s1 = model.signals(model.prepare(R), V, macro, inst["sector"])
    s2 = model.signals(model.prepare(R2), V2, m2, inst["sector"])
    for k in model.STYLES:
        pd.testing.assert_frame_equal(s1[k].loc[:cut], s2[k].loc[:cut], obj=k)
    a = model.run(R, V, macro, inst, model.Config())
    b = model.run(R2, V2, m2, inst, model.Config())
    pd.testing.assert_frame_equal(a["blend"]["weights"].loc[:cut], b["blend"]["weights"].loc[:cut])


def test_rank_bounds():
    R, V, inst, macro = _toy()
    r = model.cs_rank(R.rolling(20).sum(), inst["sector"])
    assert r.abs().max().max() <= 1.0 + 1e-12
