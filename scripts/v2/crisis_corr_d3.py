"""P8 v2 Task 5 (D3): crisis correlation. Monthly net returns (lag 2, v1 costs) of the v1 blend and the H1 blend vs
managed-futures benchmarks and SPY: all months vs the worst 10% SPY months, Fisher-z 95% CI, and the share of the
blend's worst-decile months that are also the benchmark's worst-decile months. 2001-2017 main; 2018-2026 is
the seen period (v1 reported it). Run: python scripts/v2/crisis_corr_d3.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import run as v1run
from common import *  # noqa
from multistyle import analysis as A
from qengine.costs import CostModel
from qengine.engine import run_weights

from multistyle.v2.trading import blend_weights

H1 = {"smoother": "partial", "rate": 0.05, "cost_scaled": True}


def fisher(r: float, n: int):
    if n < 5 or not np.isfinite(r):
        return (np.nan, np.nan)
    z, se = np.arctanh(np.clip(r, -0.999999, 0.999999)), 1 / np.sqrt(n - 3)
    return float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))


def main():
    R, V, inst, m, rf, bench = load(end=None)
    cfg = model.Config()
    cm = CostModel.from_instruments(inst)
    Rp = model.prepare(R)
    bk = model.style_books(Rp, V, m, inst, cfg)
    books = {"v1 blend": blend_weights(R, V, m, inst, cfg, {"smoother": "buffer"}, books=bk),
             "H1 blend": blend_weights(R, V, m, inst, cfg, H1, books=bk)}
    mnet = {}
    for k, W in books.items():
        net = run_weights(W, Rp.fillna(0.0), cm, lag=2).net
        live = net.index[W.abs().sum(axis=1).gt(0)][0]
        mnet[k] = A.monthly(net.loc[live:])
    mrf = A.monthly(rf.dropna())
    bm = {k: A.monthly(bench[k].dropna().pct_change().dropna()) - mrf for k in ("EBSIX", "AQMIX", "ASFYX", "DBMF", "KMLM")}
    bmk = v1run.benchmarks(bench, rf)
    bm["managed_futures_avg(AQMIX,ASFYX)"] = bmk["managed_futures"]
    bm["SPY"] = bmk["spy"]
    spy = bm["SPY"]
    periods = {"2001-2017": ("2001-01-01", END), f"2018-2026 - {SEEN}": ("2018-01-01", "2026-12-31")}
    rows = []
    for pn, (a, b) in periods.items():
        for bk_name, bs in mnet.items():
            for name, x in bm.items():
                D = pd.concat([bs, x, spy], axis=1, keys=["b", "x", "spy"]).loc[a:b].dropna()
                if len(D) < 12:
                    rows.append({"period": pn, "book": bk_name, "benchmark": name, "n_months_all": len(D)})
                    continue
                stress = D["spy"] <= D["spy"].quantile(0.10)
                c_all, c_st = D["b"].corr(D["x"]), D.loc[stress, "b"].corr(D.loc[stress, "x"])
                lo_a, hi_a = fisher(c_all, len(D)); lo_s, hi_s = fisher(c_st, int(stress.sum()))
                wb = D["b"] <= D["b"].quantile(0.10); wx = D["x"] <= D["x"].quantile(0.10)
                rows.append({"period": pn, "book": bk_name, "benchmark": name, "n_months_all": len(D),
                             "corr_all": c_all, "corr_all_lo": lo_a, "corr_all_hi": hi_a,
                             "n_months_stress": int(stress.sum()), "corr_stress": c_st, "corr_stress_lo": lo_s,
                             "corr_stress_hi": hi_s,
                             "joint_worst_decile_share": float((wb & wx).sum() / max(wb.sum(), 1)),
                             "n_joint": int((wb & wx).sum()), "n_worst_decile": int(wb.sum())})
    t = pd.DataFrame(rows)
    t.to_csv(TAB / "d3_crisis_corr.csv", index=False)
    (TAB / "d3_crisis_corr.json").write_text(json.dumps(t.to_dict("records"), indent=1, default=float))
    main_ = t[(t["period"] == "2001-2017") & t["corr_all"].notna()]
    fig, ax = plt.subplots(figsize=(8, 3.8))
    labs = main_[main_["book"] == "v1 blend"]["benchmark"].tolist()
    x = np.arange(len(labs)); w = 0.2
    for i, (bk_name, col, off) in enumerate([("v1 blend", "corr_all", -1.5), ("v1 blend", "corr_stress", -0.5),
                                              ("H1 blend", "corr_all", 0.5), ("H1 blend", "corr_stress", 1.5)]):
        q = main_[main_["book"] == bk_name].set_index("benchmark").reindex(labs)
        ax.bar(x + off * w, q[col], w, label=f"{bk_name} {col.split('_')[1]}")
    ax.set_xticks(x); ax.set_xticklabels(labs, rotation=20, fontsize=7); ax.axhline(0, color="k", lw=0.6)
    ax.set_ylabel("monthly correlation"); ax.set_title("P8 correlation, 2001-2017 (benchmarks with >=12 months)")
    ax.legend(fontsize=7); fig.tight_layout(); fig.savefig(FIG / "d3_crisis_corr.png", dpi=130)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(t.round(3).to_string())


if __name__ == "__main__":
    main()
