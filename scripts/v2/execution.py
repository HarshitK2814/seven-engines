"""P8 v2 Task 5 (D1): execution realism and capacity for the v1 blend and the H1 blend (rate 0.05, cost-scaled).
Main table 2001-2017; 2018-2026 is the seen period (v1 reported it). Signal at close t; lag 1 = trade that close,
lag 2 = next close. ADV from Yahoo volume except FX futures/cash indices (qengine.market). Run: python scripts/v2/execution.py"""
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
from multistyle import data, macro
from qengine.capacity import capacity_at, capacity_curve
from qengine.contracts import run_contracts
from qengine.costs import CostModel
from qengine.engine import run_weights
from qengine.market import FORCE_FALLBACK, market_inputs

from multistyle.v2.trading import blend_weights

AUMS = [1e7, 1e8, 5e8, 1e9, 5e9]
COEFS = [0.25, 0.5, 1.0]
H1 = {"smoother": "partial", "rate": 0.05, "cost_scaled": True}
MARGIN, FUND_RT_COST = 0.05, 2.61


def main():
    R, V, inst, m, rf, bench = load(end=None)
    cfg = model.Config()
    Rp = model.prepare(R)
    bk = model.style_books(Rp, V, m, inst, cfg)
    W = {"v1 blend": blend_weights(R, V, m, inst, cfg, {"smoother": "buffer"}, books=bk),
         "H1 blend": blend_weights(R, V, m, inst, cfg, H1, books=bk)}
    close = pd.read_parquet(data.RAW / "close.parquet").reindex(R.index).ffill()
    volume = pd.read_parquet(data.RAW / "volume.parquet").reindex(R.index)
    fx = macro.fx_spot().reindex(R.index).ffill()
    Rw = Rp.reindex(columns=W["v1 blend"].columns).fillna(0.0)
    mi = market_inputs(Rw, close, volume, fx)
    base = CostModel.from_instruments(inst, 0.0)
    start = pd.Timestamp("2001-01-01")
    med = mi["adv_usd"].loc[start:END].median()
    thin = sorted(med[med < 50e6].index)
    mi_lo = {**mi, "adv_usd": mi["adv_usd"].copy()}
    mi_lo["adv_usd"][thin] = np.nan
    variants = {"primary_yahoo_adv": mi, "low_adv_instruments_impact_off": mi_lo}
    periods = {"2001-2017": lambda x: x.loc[start:END],
               f"2018-2026 - {SEEN}": lambda x: x.loc["2018-01-01":]}

    rows, caps = [], []
    for bn, Wb in W.items():
        for pn, sl in periods.items():
            live_start = sl(Wb).abs().sum(axis=1).gt(0).idxmax()
            slc = lambda x, s=sl, ls=live_start: s(x).loc[ls:]
            for lag in (1, 2):
                r = run_weights(Wb, Rw, base, lag=lag)
                net = slc(r.net); s = sharpe_ci(net)
                c = slc(r.costs)
                vol = net.std(ddof=1) * np.sqrt(252)
                tr = slc(r.weights.diff().abs().sum(axis=1)).mean() * 252
                rows.append({"book": bn, "period": pn, "run": f"v1 costs lag{lag}", "net_sharpe": s[0], "ci95_lo": s[1],
                             "ci95_hi": s[2], "gross_sharpe": sh_a(slc(r.gross)), "n_days": len(net),
                             "ann_cost_linear": c["linear"].mean() * 252, "ann_cost_roll": c["roll"].mean() * 252,
                             "ann_cost_total": (c["linear"] + c["roll"]).mean() * 252,
                             "cost_in_sharpe_units": (c["linear"] + c["roll"]).mean() * 252 / vol,
                             "turnover_per_yr": float(tr), "n_trade_days": int((slc(r.turnover) > 1e-12).sum()),
                             "margin_to_equity": float(MARGIN * slc(r.weights.abs().sum(axis=1)).mean())})
            for vn, mm in variants.items():
                for coef in COEFS:
                    cm = CostModel.from_instruments(inst, coef)
                    for aum in AUMS:
                        r = run_weights(Wb, Rw, cm, lag=2, aum=aum, adv_usd=mm["adv_usd"], sigma_daily=mm["sigma_daily"])
                        net = slc(r.net); s = sharpe_ci(net, 500)
                        rows.append({"book": bn, "period": pn, "run": f"impact {coef} @ AUM {aum:.0e} [{vn}]",
                                     "net_sharpe": s[0], "ci95_lo": s[1], "ci95_hi": s[2], "n_days": len(net),
                                     "ann_cost_impact": slc(r.costs)["impact"].mean() * 252, "impact_coef": coef, "aum": aum,
                                     "adv_variant": vn})
            # integer contracts (lag 2) over the period
            ymax = pn[:4] == "2001" and END or None
            for aum0 in (1e7, 5e7):
                Wc, Rc, Nc = Wb.loc[:ymax], Rw.loc[:ymax], mi["notional"].loc[:ymax]
                cr = run_contracts(Wc, Rc, Nc, aum0, base, lag=2)
                net = slc(cr.returns); s = sharpe_ci(net, 500)
                n = cr.contracts.diff().abs()
                rt_per_yr = float(slc(n.sum(axis=1)).mean() * 252 / 2)
                ann_c = float(slc(cr.costs).mean() * 252)
                rows.append({"book": bn, "period": pn, "run": f"integer contracts ${aum0/1e6:.0f}m lag2",
                             "net_sharpe": s[0], "ci95_lo": s[1], "ci95_hi": s[2], "n_days": len(net),
                             "ann_cost_total": ann_c, "round_turns_per_yr": rt_per_yr,
                             "avg_cost_per_round_turn_usd": ann_c * aum0 / rt_per_yr if rt_per_yr else np.nan,
                             "fund_10k_round_turn_usd": FUND_RT_COST})
    t = pd.DataFrame(rows)
    t.to_csv(TAB / "execution.csv", index=False)

    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    grid = [1e7, 2.5e7, 5e7, 1e8, 2.5e8, 5e8, 1e9, 2.5e9, 5e9]
    sl_idx = slice(start, END)
    for bn, Wb in W.items():
        ls0 = Wb.loc[sl_idx].abs().sum(axis=1).gt(0).idxmax()
        for vn, mm in variants.items():
            for coef in COEFS:
                cm = CostModel.from_instruments(inst, coef)
                cur = capacity_curve(Wb.loc[ls0:END], Rw.loc[ls0:END], cm, mm["adv_usd"].loc[ls0:END],
                                     mm["sigma_daily"].loc[ls0:END], grid, lag=2)
                cap = capacity_at(cur, 0.10)
                caps.append(cur.assign(book=bn, impact_coef=coef, adv_variant=vn, capacity_aum_drop0p10=cap))
                if coef == 0.5:
                    ax.plot(cur["aum"], cur["net_sharpe"], marker="o", ls="-" if vn.startswith("primary") else "--",
                            label=f"{bn}, {'Yahoo ADV' if vn.startswith('primary') else 'thin-ADV off'} (cap ${cap/1e6:,.0f}m)")
    ax.set_xscale("log"); ax.set_xlabel("AUM (USD)"); ax.set_ylabel("net Sharpe, lag 2, impact coef 0.5")
    ax.set_title("P8 capacity, 2001-2017"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "capacity.png", dpi=130)
    cap_df = pd.concat(caps)
    cap_df.to_csv(TAB / "capacity.csv", index=False)
    json.dump({"thin_adv_instruments": thin, "forced_fallback": sorted(FORCE_FALLBACK),
               "margin_assumption": MARGIN, "fund_round_turn_usd": FUND_RT_COST,
               "no_adv_share_of_traded_weight_v1": float(
                   W["v1 blend"].diff().abs().loc[sl_idx].where(
                       mi["adv_usd"].reindex_like(W["v1 blend"]).loc[sl_idx].isna(), 0.0).sum().sum()
                   / W["v1 blend"].diff().abs().loc[sl_idx].sum().sum())},
              open(TAB / "execution_notes.json", "w"), indent=1)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    show = ["book", "period", "run", "net_sharpe", "ci95_lo", "ci95_hi", "ann_cost_total", "cost_in_sharpe_units",
            "turnover_per_yr", "margin_to_equity", "round_turns_per_yr", "avg_cost_per_round_turn_usd"]
    print(t[[c for c in show if c in t]].round(4).to_string())
    print(cap_df.groupby(["book", "adv_variant", "impact_coef"])["capacity_aum_drop0p10"].first())


if __name__ == "__main__":
    main()
