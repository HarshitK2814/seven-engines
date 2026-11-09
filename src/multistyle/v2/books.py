"""Shared book construction for the forward tracker and the seen-period re-run (P8 v2).
Signals are computed at the close of day t from data up to t; lag 2 trades at the next close.
Books: v1 blend (10% buffer), H1 blend (partial adjustment rate 0.05, cost-scaled; fixed from EXP-V2-002),
alloc_annual_equal (best D2 allocation by net Sharpe, EXP-V2-003, on the H1 smoother)."""

from __future__ import annotations

import pandas as pd

from multistyle import model
from multistyle.v2.allocation import rolling_alloc
from multistyle.v2.trading import blend_weights

H1_PARAMS = {"smoother": "partial", "rate": 0.05, "cost_scaled": True}


def monthly_net(r: pd.Series) -> pd.Series:
    return ((1 + r).resample("ME").prod(min_count=1) - 1).dropna()


def build_weights(R, V, macro, inst, cfg=None) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    cfg = cfg or model.Config()
    Rp = model.prepare(R)
    bk = model.style_books(Rp, V.reindex(Rp.index), macro, inst, cfg)
    res = model.run(R, V, macro, inst, cfg)
    sm = pd.DataFrame({s: monthly_net(res[s]["net"]) for s in model.STYLES}).loc["2001-01-01":]
    alloc = rolling_alloc(sm, "equal")
    W = {"v1_blend": blend_weights(R, V, macro, inst, cfg, {"smoother": "buffer"}, books=bk),
         "h1_blend": blend_weights(R, V, macro, inst, cfg, H1_PARAMS, books=bk),
         "alloc_annual_equal": blend_weights(R, V, macro, inst, cfg, {**H1_PARAMS, "alloc": alloc}, books=bk)}
    Rw = Rp.reindex(columns=W["v1_blend"].columns).fillna(0.0)
    return W, Rw
