"""P8 v2 Task 4 (D2): style allocation. Equal-risk (v1) vs inverse-vol vs HRP (Ledoit-Wolf) vs trailing net Sharpe,
36-month trailing window, annual rebalance (first month-end of the year, applies from the next day).
Judged on net Sharpe with 95% CI over the evaluation window (lag 2, v1 costs) and by CPCV selection on 2001-2017.
Equal-risk stays the baseline. Nothing is chosen from 2018-2026. Run: python scripts/v2/allocation_d2.py"""
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
from qcore.validation import cpcv_paths, cpcv_splits, group_index
from qengine.costs import CostModel
from qengine.engine import run_weights

from multistyle.v2.allocation import METHODS, rolling_alloc
from multistyle.v2.trading import blend_weights

H1_PARAMS = {"smoother": "partial", "rate": 0.05, "cost_scaled": True}   # chosen in every H1 fold (EXP-V2-002)
BUF = {"smoother": "buffer"}


def monthly_net(r: pd.Series) -> pd.Series:
    return ((1 + r).resample("ME").prod(min_count=1) - 1).dropna()


def main():
    R, V, inst, m, rf, bench = load()
    cfg = model.Config()
    cm = CostModel.from_instruments(inst)
    res = model.run(R, V, m, inst, cfg)
    sm = pd.DataFrame({s: monthly_net(res[s]["net"]) for s in model.STYLES})
    sm = sm.loc["2001-01-01":]
    books = model.style_books(model.prepare(R), V, m, inst, cfg)

    allocs = {k: rolling_alloc(sm, k) for k in METHODS}
    start = allocs["equal"].index[0]                 # first allocation date (36-month warm-up from 2001)
    runs, rows, series = {}, [], {}
    for sm_name, base in (("H1 partial (0.05, cost-scaled)", H1_PARAMS), ("v1 buffer 10%", BUF)):
        for name in ("v1 equal-risk (daily n_live)",) + METHODS:
            p = dict(base)
            if name in METHODS:
                p["alloc"] = allocs[name]
            W = blend_weights(R, V, m, inst, cfg, p, books=books)
            r = run_weights(W, R, cm, lag=2)
            net = r.net.loc[start:]
            s = sharpe_ci(net)
            series[(sm_name, name)] = net
            rows.append({"smoother": sm_name, "allocation": name, "net_sharpe": s[0], "ci95_lo": s[1], "ci95_hi": s[2],
                         "gross_sharpe": sh_a(r.gross.loc[start:]), "ann_cost": float((r.costs["linear"] + r.costs["roll"]).loc[start:].mean() * 252),
                         "n_days": len(net), "turnover_per_yr": float(r.turnover.loc[start:].mean() * 252)})
    t = pd.DataFrame(rows)
    # differences vs equal-risk baseline of the same smoother
    d_rows = []
    for sm_name in t["smoother"].unique():
        base = series[(sm_name, "v1 equal-risk (daily n_live)")]
        for name in METHODS:
            d, lo, hi = diff_ci(series[(sm_name, name)], base)
            d_rows.append({"smoother": sm_name, "allocation": name, "diff_vs_v1_equal_risk": d, "ci95_lo": lo, "ci95_hi": hi,
                           "ci_excludes_zero": bool(lo > 0 or hi < 0)})
    dt = pd.DataFrame(d_rows)
    t.to_csv(TAB / "d2_allocation.csv", index=False)
    dt.to_csv(TAB / "d2_allocation_diff.csv", index=False)
    for k, a in allocs.items():
        a.to_csv(TAB / f"d2_weights_{k}.csv")

    # CPCV on 2001-2017: select the best-train-Sharpe allocation per split (main smoother = H1), keep test returns
    M = pd.DataFrame({n: series[("H1 partial (0.05, cost-scaled)", n)] for n in ("v1 equal-risk (daily n_live)",) + METHODS}).dropna()
    G, K = 6, 2
    gi = group_index(M.index, G)
    X = M.to_numpy(); names = list(M.columns)
    oos, picks = {}, []
    for tr, te, tg in cpcv_splits(len(M), n_groups=G, k_test=K, purge=0, embargo=21):
        sr_tr = X[tr].mean(axis=0) / X[tr].std(axis=0, ddof=1)
        j = int(np.argmax(sr_tr)); picks.append(names[j]); oos[tg] = pd.Series(X[te, j], index=M.index[te])
    paths = cpcv_paths(oos, G, K, gi)
    cp = {"n_groups": G, "k_test": K, "embargo": 21, "n_splits": len(picks),
          "selected_counts": pd.Series(picks).value_counts().to_dict(),
          "path_ann_sharpe": [sh_a(p) for p in paths],
          "fixed_rule_ann_sharpe_full_window": {n: sh_a(M[n]) for n in names}}
    # fixed rules, per CPCV test-group Sharpe spread (no fitting, so each rule is its own path)
    cp["fixed_rule_group_sharpe"] = {n: [sh_a(M[n].loc[g.intersection(M.index)]) for g in gi] for n in names}

    out = {"eval_window": [str(M.index[0].date()), str(M.index[-1].date())], "lag": 2,
           "table": t.to_dict("records"), "diff_vs_equal": dt.to_dict("records"), "cpcv": cp,
           "best_by_net_sharpe_main_smoother": t[t["smoother"].str.startswith("H1")].sort_values("net_sharpe").iloc[-1]["allocation"],
           "note": "allocation needs a full 36-month window; value net starts 2004-03, so value is in the allocation from Jan 2008"}
    (TAB / "d2_allocation.json").write_text(json.dumps(out, indent=1, default=float))
    pd.set_option("display.width", 220)
    print(t.round(3).to_string()); print(dt.round(3).to_string()); print(json.dumps(cp, indent=1, default=float))

    fig, axs = plt.subplots(1, 3, figsize=(13, 3.6), sharey=True)
    for ax, k in zip(axs, ("invvol", "hrp", "sharpe")):
        a = allocs[k].copy(); a.index = a.index.year
        im = ax.imshow(a.T.to_numpy(), aspect="auto", vmin=0, vmax=0.6, cmap="viridis")
        ax.set_xticks(range(len(a))); ax.set_xticklabels(a.index, rotation=90, fontsize=6)
        ax.set_yticks(range(len(a.columns))); ax.set_yticklabels(a.columns, fontsize=7); ax.set_title(k)
    fig.colorbar(im, ax=axs, shrink=0.8, label="weight")
    fig.savefig(FIG / "d2_allocation_heatmap.png", dpi=130, bbox_inches="tight")


if __name__ == "__main__":
    main()
