"""P8 v2 descriptive items D4 (cost budget per style), D5 (fast-style restriction), D6 (netting benefit).
Prereg v2 hash b14b0cc95d53. 2001-2017, lag 2 (signal at close t, trade next close), v1 per-contract costs, v1 10% buffer.
Run: python scripts/v2/d4_d6.py"""
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

from multistyle.v2.budget import budget_ok, cheap_markets, cost_sharpe_units, restricted_style_book

NAMED_FAST = ("mean_reversion", "liquidity")


def style_stats(W, R, cm, lag=2):
    res = run_weights(W, R, cm, lag=lag)
    live = max(W.abs().sum(axis=1).gt(0).idxmax(), pd.Timestamp('2001-01-01'))   # prereg window 2001-2017
    gross, net = res.gross.loc[live:], res.net.loc[live:]
    cost = (res.costs["linear"] + res.costs["roll"]).loc[live:]
    D = pd.concat([cost, gross], axis=1, keys=["cost", "gross"])
    d = bootstrap_stat(D, lambda x: x["cost"].mean() * 252 / (x["gross"].std(ddof=1) * np.sqrt(252)),
                       n_boot=1000, mean_block=21, seed=0)
    cu_lo, cu_hi = percentile_ci(d)
    g = sharpe_ci(gross)
    cu = cost_sharpe_units(cost, gross)
    return {"live_from": str(live.date()), "n_days": int(len(gross)), "gross_sharpe": g[0], "gross_ci": [g[1], g[2]],
            "net_sharpe": sh_a(net), "cost_units": cu, "cost_units_ci": [cu_lo, cu_hi],
            "ann_cost": float(cost.mean() * 252), "turnover_per_yr": float(res.turnover.loc[live:].mean() * 252),
            "budget_gross_over_3": g[0] / 3, "passes_D4": budget_ok(g[0], cu)}


def main():
    R, V, inst, m, rf, bench = load()
    cfg = model.Config()
    Rp = model.prepare(R)
    cm = CostModel.from_instruments(inst, 0.0)
    scaled, units, ks = model.style_books(Rp, V.reindex(Rp.index), m, inst, cfg)
    Rw = Rp.reindex(columns=scaled["momentum"].columns).fillna(0.0)
    buf = lambda s, u: model.apply_buffer(s.fillna(0.0), u.fillna(0.0), cfg.buffer)
    cheap = cheap_markets(inst["cost_bp"].reindex(Rw.columns))

    out = {"prereg_hash": "b14b0cc95d53", "lag": 2, "period": "2001-2017", "cheap_market_cutoff_bp": float(inst["cost_bp"].reindex(Rw.columns).median()),
           "n_cheap_markets": len(cheap), "n_markets": int(Rw.shape[1]), "styles": {}}
    rows = []
    for s in model.STYLES:
        base = style_stats(buf(scaled[s], units[s]), Rw, cm)
        rec = {"D4": base}
        if not base["passes_D4"]:
            sc, un, _ = restricted_style_book(Rp, V.reindex(Rp.index), m, inst, cfg, s, cheap)
            rst = style_stats(buf(sc, un), Rw, cm)
            rec["D5_restricted_to_cheap"] = rst
            rec["named_fast_style"] = s in NAMED_FAST
            rec["outcome"] = "passes after restriction" if rst["passes_D4"] else "still fails: dropped (reported)"
        else:
            rec["outcome"] = "passes"
        out["styles"][s] = rec
        rows.append({"style": s, "version": "v1 buffered", **{k: base[k] for k in ("live_from", "gross_sharpe", "cost_units", "turnover_per_yr", "net_sharpe", "passes_D4")}})
        if "D5_restricted_to_cheap" in rec:
            r_ = rec["D5_restricted_to_cheap"]
            rows.append({"style": s, "version": "D5 cheap markets only", **{k: r_[k] for k in ("live_from", "gross_sharpe", "cost_units", "turnover_per_yr", "net_sharpe", "passes_D4")}})
    pd.DataFrame(rows).to_csv(TAB / "d4_d5_style_budget.csv", index=False)

    # D6 netting: the blend's netted book vs the seven style books traded separately at the same blend weights
    live = pd.DataFrame({s: scaled[s].abs().sum(axis=1) > 0 for s in model.STYLES})
    n = live.sum(axis=1).replace(0, np.nan)
    Wb = sum(scaled[s].fillna(0.0) for s in model.STYLES).div(n, axis=0)
    Ub = sum(units[s].fillna(0.0) for s in model.STYLES).div(n, axis=0)
    kb = model.vol_scale(Rp, Wb.fillna(0.0), cfg)
    T_net, U_net = Wb.mul(kb, axis=0).fillna(0.0), Ub.mul(kb, axis=0).fillna(0.0)
    start = max(kb.notna().idxmax(), pd.Timestamp('2001-01-01'))
    d6 = {}
    for label, band in (("no band", None), ("v1 10% band", cfg.buffer)):
        net_book = T_net if band is None else model.apply_buffer(T_net, U_net, band)
        sep_cost = 0.0
        sep_gross = 0.0
        sep_turn = 0.0
        for s in model.STYLES:
            Ts = scaled[s].fillna(0.0).div(n, axis=0).mul(kb, axis=0).fillna(0.0)
            Us = units[s].fillna(0.0).div(n, axis=0).mul(kb, axis=0).fillna(0.0)
            Ws = Ts if band is None else model.apply_buffer(Ts, Us, band)
            r = run_weights(Ws, Rw, cm, lag=2)
            sep_cost = sep_cost + (r.costs["linear"] + r.costs["roll"])
            sep_gross = sep_gross + r.gross
            sep_turn = sep_turn + r.turnover
        rn = run_weights(net_book, Rw, cm, lag=2)
        c_net = (rn.costs["linear"] + rn.costs["roll"]).loc[start:]
        c_sep = sep_cost.loc[start:]
        vol = rn.gross.loc[start:].std(ddof=1) * np.sqrt(252)
        if band is None:   # without a band, the netted book is exactly the sum of the separate books: pnl must agree
            assert np.allclose(rn.gross, sep_gross, atol=1e-10), "netted gross != sum of separate gross"
        D = pd.concat([c_net, c_sep], axis=1, keys=["n", "s"])
        d = bootstrap_stat(D, lambda x: 1 - x["n"].mean() / x["s"].mean(), n_boot=1000, mean_block=21, seed=0)
        lo, hi = percentile_ci(d)
        d6[label] = {"netted_cost_per_yr": float(c_net.mean() * 252), "separate_cost_per_yr": float(c_sep.mean() * 252),
                     "netting_benefit": float(1 - c_net.mean() / c_sep.mean()), "benefit_ci": [lo, hi],
                     "netted_cost_sharpe_units": float(c_net.mean() * 252 / vol),
                     "separate_cost_sharpe_units": float(c_sep.mean() * 252 / vol),
                     "turnover_netted": float(rn.turnover.loc[start:].mean() * 252),
                     "turnover_separate": float(sep_turn.loc[start:].mean() * 252),
                     "netted_net_sharpe": sh_a(rn.net.loc[start:]), "n_days": int(len(c_net)), "live_from": str(start.date())}
    out["D6"] = d6
    (TAB / "d4_d6.json").write_text(json.dumps(out, indent=1, default=float))
    print(pd.DataFrame(rows).round(3).to_string())
    print(json.dumps({"D6": d6, "outcomes": {k: v["outcome"] for k, v in out["styles"].items()}}, indent=1, default=float))


if __name__ == "__main__":
    main()
