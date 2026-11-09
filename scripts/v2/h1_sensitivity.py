"""SENSITIVITY, NOT IN THE PREREG (hash b14b0cc95d53): H1/H2 re-run with the partial-adjustment rate grid extended below 0.05
(0.01, 0.02, 0.03), because the pre-registered walk-forward chose the grid edge (0.05) in every fold. Everything else as
scripts/v2/h1_trading.py: walk-forward OOS 2009-2017, lag 2, v1 costs. The pre-registered H1/H2 verdict is NOT replaced.
Run: python scripts/v2/h1_sensitivity.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from common import *  # noqa
from qengine.costs import CostModel
from qengine.engine import run_weights
from qengine.walkforward import walk_forward, wf_folds

from multistyle.v2.trading import blend_weights

RATES = [0.01, 0.02, 0.03, 0.05, 0.1, 0.2, 0.35, 0.5, 1.0]
GRID = {"rate": RATES, "cost_scaled": [False, True]}


def main():
    R, V, inst, m, rf, bench = load()
    cfg = model.Config()
    books = BookCache(V, m, inst, cfg)
    cm = CostModel.from_instruments(inst, 0.0)
    mk = lambda Rf, p: blend_weights(Rf, V, m, inst, cfg, {"smoother": "partial", **p}, books=books(Rf))
    folds = wf_folds(R.index, first_test_year=2009, test_years=2, last_year=2017)
    wf = walk_forward(mk, GRID, R, cm, folds, lag=2)
    oos0, oos1 = folds[0][2], folds[-1][3]
    out = {"label": "SENSITIVITY, not in prereg", "prereg_hash": "b14b0cc95d53", "rates": RATES,
           "chosen": wf["chosen"].assign(params=lambda d: d["params"].astype(str)).to_dict("records")}
    W_v1 = blend_weights(R, V, m, inst, cfg, {"smoother": "buffer"}, books=books(R))
    for lag in (2, 1):
        g, n, c, t = [], [], [], []
        for (tr0, tr1, te0, te1), row in zip(folds, wf["chosen"].itertuples()):
            Rf = R.loc[:te1]
            res = run_weights(mk(Rf, row.params), Rf, cm, lag=lag)
            sl = slice(te0, te1)
            g.append(res.gross.loc[sl]); n.append(res.net.loc[sl])
            c.append((res.costs["linear"] + res.costs["roll"]).loc[sl]); t.append(res.turnover.loc[sl])
        h1 = {"gross": pd.concat(g), "net": pd.concat(n), "cost": pd.concat(c), "turnover": pd.concat(t)}
        if lag == 2:
            assert np.allclose(h1["net"], wf["oos"], atol=1e-12)
        rv = run_weights(W_v1, R, cm, lag=lag)
        sl = slice(oos0, oos1)
        v1 = {"gross": rv.gross.loc[sl], "net": rv.net.loc[sl], "cost": (rv.costs["linear"] + rv.costs["roll"]).loc[sl]}
        cost_h1, cost_v1 = float(h1["cost"].mean() * 252), float(v1["cost"].mean() * 252)
        g_h1, g_v1 = sh_a(h1["gross"]), sh_a(v1["gross"])
        n_h1, n_v1 = sharpe_ci(h1["net"]), sharpe_ci(v1["net"])
        dif = diff_ci(h1["net"], v1["net"])
        cut = 1 - cost_h1 / cost_v1
        out[f"lag{lag}"] = {
            "annual_cost": {"h1": cost_h1, "v1_buffer": cost_v1, "reduction": cut},
            "gross_sharpe": {"h1": g_h1, "v1_buffer": g_v1, "ratio": g_h1 / g_v1},
            "net_sharpe": {"h1": list(n_h1), "v1_buffer": list(n_v1), "diff_h1_minus_v1": list(dif)},
            "turnover_per_year": float(h1["turnover"].mean() * 252),
            "H1_supported": bool(cut >= 0.40 and g_h1 >= 0.8 * g_v1),
            "H2_supported": bool(n_h1[0] > n_v1[0] and (dif[1] > 0 or dif[2] < 0))}
    # development-period (2001-2012) look at the new low rates, for reference only (no choice made from it)
    Rd = R.loc[:"2012-12-31"]
    rows = []
    for cs in (False, True):
        for r in RATES:
            res = run_weights(blend_weights(Rd, V, m, inst, cfg, {"smoother": "partial", "rate": r, "cost_scaled": cs},
                                            books=books(Rd)), Rd, cm, lag=2)
            live = res.weights.index[res.weights.abs().sum(axis=1) > 0][0]
            rows.append({"rate": r, "cost_scaled": cs, "net_sharpe": sh_a(res.net.loc[live:]), "gross_sharpe": sh_a(res.gross.loc[live:]),
                         "ann_cost": float((res.costs["linear"] + res.costs["roll"]).loc[live:].mean() * 252)})
    pd.DataFrame(rows).to_csv(TAB / "h1_sensitivity_rate_grid_2001_2012.csv", index=False)
    (TAB / "h1_sensitivity_lowrate.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))
    print(pd.DataFrame(rows).round(3).to_string())


if __name__ == "__main__":
    main()
