"""P8 v2 Task 6: seen-period re-run (2018-2026) and tearsheets. EVERY 2018-2026 number is 'seen period (v1 reported it)'.
Books: v1_blend, h1_blend, alloc_annual_equal. Signal at close t, trade next close (lag 2); (a) v1 costs only, (b) square-root
impact coef 0.5 at AUM $100m with Yahoo ADV (primary) and with thin-ADV impact off (lower bound), as in scripts/v2/execution.py.
2001-2017 counterpart is written beside it. Run: python scripts/v2/seen_period.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from common import *  # noqa
from multistyle import data, macro
from multistyle.v2.books import build_weights
from qcore import metrics
from qengine.costs import CostModel
from qengine.engine import run_weights
from qengine.market import market_inputs
from qengine.montecarlo import mc_summary
from qengine.tearsheet import write_tearsheet

TS = ROOT / "results" / "v2" / "tearsheets"
AUM, COEF = 1e8, 0.5


def stats(r, res, sl) -> dict:
    c, to = sl(res.costs), sl(res.turnover)
    lo, hi = percentile_ci(bootstrap_stat(r, sh_a, n_boot=1000, mean_block=21, seed=0))
    return {"net_sharpe": sh_a(r), "ci95_lo": lo, "ci95_hi": hi, "n_days": len(r),
            "ann_return": float(r.mean() * 252), "ann_vol": float(r.std(ddof=1) * np.sqrt(252)),
            "max_drawdown": float(metrics.drawdown(r).min()),
            "ann_cost_linear": float(c["linear"].mean() * 252), "ann_cost_roll": float(c["roll"].mean() * 252),
            "ann_cost_impact": float(c["impact"].mean() * 252),
            "turnover_per_yr": float(to.mean() * 252), "n_rebalance_days": int((to > 1e-12).sum())}


def main():
    TS.mkdir(parents=True, exist_ok=True)
    R, V, inst, m, rf, bench = load(end=None)
    W, Rw = build_weights(R, V, m, inst)
    close = pd.read_parquet(data.RAW / "close.parquet").reindex(R.index).ffill()
    volume = pd.read_parquet(data.RAW / "volume.parquet").reindex(R.index)
    fx = macro.fx_spot().reindex(R.index).ffill()
    mi = market_inputs(Rw, close, volume, fx)
    start = pd.Timestamp("2001-01-01")
    med = mi["adv_usd"].loc[start:END].median()
    thin = sorted(med[med < 50e6].index)
    mi_lo = {**mi, "adv_usd": mi["adv_usd"].copy()}
    mi_lo["adv_usd"][thin] = np.nan
    base, cm = CostModel.from_instruments(inst, 0.0), CostModel.from_instruments(inst, impact_coef=COEF)
    periods = {"2001-2017": lambda x: x.loc[start:END], f"2018-2026 - {SEEN}": lambda x: x.loc["2018-01-01":]}
    execs = {
        "v1 costs, lag2": lambda w: run_weights(w, Rw, base, lag=2),
        f"impact {COEF} @ ${AUM/1e6:.0f}m, Yahoo ADV, lag2": lambda w: run_weights(
            w, Rw, cm, lag=2, aum=AUM, adv_usd=mi["adv_usd"], sigma_daily=mi["sigma_daily"]),
        f"impact {COEF} @ ${AUM/1e6:.0f}m, thin-ADV impact off, lag2": lambda w: run_weights(
            w, Rw, cm, lag=2, aum=AUM, adv_usd=mi_lo["adv_usd"], sigma_daily=mi_lo["sigma_daily"]),
    }
    rows, nets = [], {}
    for book, w in W.items():
        live0 = w.abs().sum(axis=1).gt(0).idxmax()
        for en, fn in execs.items():
            res = fn(w)
            for pn, sl in periods.items():
                r = sl(res.net)
                r = r[r.index >= max(start, live0)]
                rows.append({"period": pn, "book": book, "execution": en, **stats(r, res, lambda x: sl(x).loc[r.index[0]:])})
                nets[(book, en, pn)] = (r, sl(res.costs).loc[r.index[0]:])
    t = pd.DataFrame(rows)
    t.to_csv(TAB / "seen_period.csv", index=False)
    print(t.round(3).to_string())
    for (book, en, pn), (r, c) in nets.items():
        if "thin" in en:
            continue
        tag = "v1costs" if en.startswith("v1") else "impact"
        slug = f"{book}_{'dev_val_2001_2017' if pn.startswith('2001') else 'seen_2018_2026'}_{tag}"
        title = f"P8 v2 {book} {pn.split(' - ')[0]} ({en})" + (f" - {SEEN}" if pn.startswith("2018") else "")
        notes = ["Signal computed at close t from data up to and including t; trade at the next close (lag 2).",
                 "Costs: " + ("v1 per-instrument linear bp + roll cost only, no impact." if tag == "v1costs" else
                              f"v1 linear + roll + square-root impact coef {COEF} at AUM ${AUM/1e6:.0f}m, Yahoo volume ADV (upper bound on impact)."),
                 "Data: Yahoo Finance '=F' continuous futures plus synthetic FX/rates/cash indices (v1 universe); not back-adjusted.",
                 "Book: " + {"v1_blend": "equal-risk blend of seven styles, 10% no-trade buffer (v1).",
                             "h1_blend": "same blend, partial adjustment rate 0.05/day, faster in cheap markets (H1; rate chosen on pre-2009 data).",
                             "alloc_annual_equal": "H1 smoother with style weights equal across styles that have a full 36-month history, rebalanced yearly (best D2 allocation, not distinguishable from v1)."}[book],
                 "Sharpe CIs: stationary bootstrap, mean block 21. Research artifact, not investment advice."]
        if pn.startswith("2018"):
            notes.insert(0, f"{SEEN}: v1 already reported 2018-2026; this is descriptive, not out-of-sample evidence.")
        write_tearsheet(r, TS / f"{slug}.html", title, costs=c, mc=mc_summary(r, n_paths=2000), notes=notes)
    print("tearsheets:", sorted(p.name for p in TS.glob("*.html")))


if __name__ == "__main__":
    main()
