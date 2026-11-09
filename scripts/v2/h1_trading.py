"""P8 v2 Task 3 (H1, H2, D7, D8). Walk-forward OOS 2009-2017, lag 2, v1 per-contract costs.
Run: python scripts/v2/h1_trading.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from common import *  # noqa
from qengine.costs import CostModel
from qengine.engine import run_weights
from qengine.walkforward import walk_forward, wf_folds

from multistyle.v2.trading import blend_weights

RATES = [0.05, 0.1, 0.2, 0.35, 0.5, 1.0]
GRID = {"rate": RATES, "cost_scaled": [False, True]}


def main():
    R, V, inst, m, rf, bench = load()
    cfg = model.Config()
    books = BookCache(V, m, inst, cfg)
    cm = CostModel.from_instruments(inst)
    mk = lambda Rf, p: blend_weights(Rf, V, m, inst, cfg, {"smoother": "partial", **p}, books=books(Rf))
    folds = wf_folds(R.index, first_test_year=2009, test_years=2, last_year=2017)
    wf = walk_forward(mk, GRID, R, cm, folds, lag=2)
    oos_start, oos_end = folds[0][2], folds[-1][3]

    gross, net, link, roll, trn = [], [], [], [], []
    for (tr0, tr1, te0, te1), row in zip(folds, wf["chosen"].itertuples()):
        Rf = R.loc[:te1]
        res = run_weights(mk(Rf, row.params), Rf, cm, lag=2)
        sl = slice(te0, te1)
        gross.append(res.gross.loc[sl]); net.append(res.net.loc[sl])
        link.append(res.costs["linear"].loc[sl]); roll.append(res.costs["roll"].loc[sl]); trn.append(res.turnover.loc[sl])
    h1 = {"gross": pd.concat(gross), "net": pd.concat(net), "cost": pd.concat(link) + pd.concat(roll),
          "turnover": pd.concat(trn)}
    assert np.allclose(h1["net"], wf["oos"], atol=1e-12), "recomputed OOS != walk_forward OOS"

    def oos_book(W, lag):
        res = run_weights(W, R, cm, lag=lag)
        sl = slice(oos_start, oos_end)
        return {"gross": res.gross.loc[sl], "net": res.net.loc[sl],
                "cost": (res.costs["linear"] + res.costs["roll"]).loc[sl], "turnover": res.turnover.loc[sl],
                "n_reb": int((res.turnover.loc[sl] > 0).sum())}
    bk = books(R)
    W_v1 = blend_weights(R, V, m, inst, cfg, {"smoother": "buffer"}, books=bk)
    W_cb = blend_weights(R, V, m, inst, cfg, {"smoother": "cost_band", "buffer": cfg.buffer}, books=bk)
    v1 = oos_book(W_v1, 2)
    cband = oos_book(W_cb, 2)

    out = {"oos": [str(oos_start.date()), str(oos_end.date())], "lag": 2, "n_oos_days": int(len(h1["net"])),
           "chosen": wf["chosen"].assign(params=lambda d: d["params"].astype(str)).to_dict("records"),
           "n_grid_cells": wf["n_trials"]}
    out["rebalance_days"] = {"h1": int((h1["turnover"] > 1e-12).sum()), "v1_buffer": v1["n_reb"],
                             "cost_band_D7": cband["n_reb"]}
    cost_h1, cost_v1 = float(h1["cost"].mean() * 252), float(v1["cost"].mean() * 252)
    g_h1, g_v1 = sh_a(h1["gross"]), sh_a(v1["gross"])
    n_h1, n_v1 = sharpe_ci(h1["net"]), sharpe_ci(v1["net"])
    dif = diff_ci(h1["net"], v1["net"])
    cut = 1 - cost_h1 / cost_v1
    out["annual_cost"] = {"h1": cost_h1, "v1_buffer": cost_v1, "reduction": cut,
                          "cost_band_D7": float(cband["cost"].mean() * 252)}
    out["gross_sharpe"] = {"h1": g_h1, "v1_buffer": g_v1, "ratio": g_h1 / g_v1 if g_v1 != 0 else None}
    out["net_sharpe"] = {"h1": list(n_h1), "v1_buffer": list(n_v1), "cost_band_D7": list(sharpe_ci(cband["net"])),
                         "diff_h1_minus_v1": list(dif)}
    # literal rule: gross_h1 >= 0.8 * gross_v1 (if gross_v1 < 0 the floor lies above gross_v1: flagged)
    h1_cost_ok = bool(cut >= 0.40)
    h1_gross_ok = bool(g_h1 >= 0.8 * g_v1)
    out["H1"] = {"cost_cut_ge_40pct": h1_cost_ok, "gross_ge_80pct_of_v1": h1_gross_ok,
                 "supported": h1_cost_ok and h1_gross_ok, "note_gross_v1_negative": bool(g_v1 < 0)}
    out["H2"] = {"net_h1_gt_v1": bool(n_h1[0] > n_v1[0]), "ci_excludes_zero": bool(dif[1] > 0 or dif[2] < 0),
                 "supported": bool(n_h1[0] > n_v1[0] and (dif[1] > 0 or dif[2] < 0))}
    gross1, net1 = [], []
    for (tr0, tr1, te0, te1), row in zip(folds, wf["chosen"].itertuples()):
        Rf = R.loc[:te1]
        res = run_weights(mk(Rf, row.params), Rf, cm, lag=1)
        gross1.append(res.gross.loc[te0:te1]); net1.append(res.net.loc[te0:te1])
    v1_l1 = oos_book(W_v1, 1)
    out["lag1_secondary"] = {"h1_net_sharpe": list(sharpe_ci(pd.concat(net1))),
                             "v1_net_sharpe": list(sharpe_ci(v1_l1["net"])),
                             "h1_gross": sh_a(pd.concat(gross1)), "v1_gross": sh_a(v1_l1["gross"])}
    out["turnover_per_year"] = {"h1": float(h1["turnover"].mean() * 252), "v1_buffer": float(v1["turnover"].mean() * 252)}

    # D8 and figure: full grid on 2001-2012 only (development period); no choice is made from it
    rows = []
    Rd = R.loc[:"2012-12-31"]

    def live_slice(res):
        i = res.weights.index[res.weights.abs().sum(axis=1) > 0][0]
        return res.net.loc[i:].index

    for cs in (False, True):
        for r in RATES:
            res = run_weights(blend_weights(Rd, V, m, inst, cfg, {"smoother": "partial", "rate": r, "cost_scaled": cs},
                                            books=books(Rd)), Rd, cm, lag=2)
            live = live_slice(res)
            rows.append({"rate": r, "cost_scaled": cs, "half_life_days": float(np.log(0.5) / np.log(1 - r)) if r < 1 else 0.0,
                         "net_sharpe": sh_a(res.net.loc[live]), "gross_sharpe": sh_a(res.gross.loc[live]),
                         "ann_cost": float((res.costs["linear"] + res.costs["roll"]).loc[live].mean() * 252)})
    resb = run_weights(W_v1.loc[:"2012-12-31"], Rd, cm, lag=2)
    live = live_slice(resb)
    rows.append({"rate": None, "cost_scaled": None, "half_life_days": None, "label": "v1 10% buffer",
                 "net_sharpe": sh_a(resb.net.loc[live]), "gross_sharpe": sh_a(resb.gross.loc[live]),
                 "ann_cost": float((resb.costs["linear"] + resb.costs["roll"]).loc[live].mean() * 252)})
    d8 = pd.DataFrame(rows)
    d8.to_csv(TAB / "d8_rate_grid_2001_2012.csv", index=False)
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
    for cs, ls in ((False, "-"), (True, "--")):
        q = d8[d8["cost_scaled"] == cs]
        ax[0].plot(q["rate"], q["net_sharpe"], ls, marker="o", label=f"cost_scaled={cs}")
        ax[1].plot(q["rate"], q["ann_cost"] * 100, ls, marker="o", label=f"cost_scaled={cs}")
    v = d8[d8["rate"].isna()].iloc[0]
    ax[0].axhline(v["net_sharpe"], color="k", lw=0.8, label="v1 buffer")
    ax[1].axhline(v["ann_cost"] * 100, color="k", lw=0.8)
    ax[0].set_xlabel("adjustment rate / day"); ax[0].set_ylabel("net Sharpe (lag 2)")
    ax[1].set_xlabel("adjustment rate / day"); ax[1].set_ylabel("annual cost, % NAV")
    ax[0].legend(fontsize=7); fig.suptitle("P8 blend, 2001-2012 development period only")
    fig.tight_layout(); fig.savefig(FIG / "cost_vs_rate.png", dpi=130)

    (TAB / "h1_h2_trading.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))
    print(d8.round(3).to_string())
    pd.DataFrame({"h1_net": h1["net"], "v1_net": v1["net"], "h1_gross": h1["gross"], "v1_gross": v1["gross"]}
                 ).to_parquet(RUNS / "h1_oos_daily.parquet")
    wf["chosen"].assign(params=lambda d: d["params"].astype(str)).to_csv(TAB / "h1_chosen_params.csv", index=False)


if __name__ == "__main__":
    main()
