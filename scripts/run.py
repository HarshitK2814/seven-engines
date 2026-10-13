"""Run the seven-style programme. Usage:

    python scripts/run.py download && python scripts/run.py build
    python scripts/run.py dev      # development + validation (always allowed)
    python scripts/run.py test     # locked: needs PREREG_HASH = hash of research/preregistration.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from qcore.bootstrap import bootstrap_stat, percentile_ci

from multistyle import analysis as A
from multistyle import data, macro, model

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
BOOKS = ("blend",) + model.STYLES + ("blend_halfcost",)


def load():
    R = pd.read_parquet(data.PROC / "returns.parquet")
    V = pd.read_parquet(data.PROC / "volume.parquet").reindex(R.index)
    inst = data.instrument_table()
    f = pd.read_parquet(data.RAW / "fred_macro.parquet")
    m = {"fx_rates": macro.fx_rates(R.index),
         "yields": pd.DataFrame({k: f[sid] / 100 for k, (sid, _) in macro.BONDS.items()}),
         "bill": f["DGS3MO"] / 100}
    rf = data.tbill_daily().reindex(R.index).ffill()
    bench = pd.read_parquet(data.PROC / "benchmarks.parquet")
    return R, V, inst, m, rf, bench


def benchmarks(bench: pd.DataFrame, rf: pd.Series) -> dict[str, pd.Series]:
    """Monthly excess returns: managed futures = mean of two large trend-following mutual funds; 60/40 = SPY/AGG."""
    mrf = A.monthly(rf.dropna())
    mret = {k: A.monthly(bench[k].dropna().pct_change().dropna()) for k in bench}
    mf = pd.concat([mret["AQMIX"], mret["ASFYX"]], axis=1).mean(axis=1, skipna=False) - mrf
    sixty = 0.6 * mret["SPY"] + 0.4 * mret["AGG"] - mrf
    return {"managed_futures": mf.dropna(), "sixty_forty": sixty.dropna(), "spy": (mret["SPY"] - mrf).dropna()}


def corr_test(a: pd.Series, b: pd.Series, n_boot: int = 5000) -> dict:
    df = pd.concat([a, b], axis=1).dropna()
    df.columns = ["a", "b"]
    obs = float(df.corr().iloc[0, 1])
    draws = bootstrap_stat(df, lambda d: float(np.corrcoef(d["a"], d["b"])[0, 1]), n_boot=n_boot)
    return {"corr": obs, "ci": percentile_ci(draws), "n_months": len(df)}


def report(res, bm, periods, tag):
    out = {}
    for p in periods:
        t = A.table({k: res[k]["net"] for k in BOOKS}, p)
        cost = pd.Series({k: A.period(res[k]["cost"], p).sum() / max(len(A.period(res[k]["cost"], p)) / 252, 1e-9)
                          for k in BOOKS})
        t["cost_drag"] = cost
        mon = {k: A.period(A.monthly(res[k]["net"]), p) for k in BOOKS}
        C = pd.DataFrame(mon).corr()
        t["corr_managed_futures"] = pd.Series({k: pd.concat([mon[k], bm["managed_futures"]], axis=1).dropna().corr().iloc[0, 1]
                                               for k in BOOKS})
        t["corr_60_40"] = pd.Series({k: pd.concat([mon[k], bm["sixty_forty"]], axis=1).dropna().corr().iloc[0, 1]
                                     for k in BOOKS})
        C.to_csv(OUT / "tables" / f"style_corr_{p}.csv")
        print(f"\n===== {p} =====")
        print(t[["n_periods", "ann_return", "ann_vol", "sharpe", "sharpe_ci95_lo", "sharpe_ci95_hi", "max_drawdown",
                 "cost_drag", "corr_managed_futures", "corr_60_40"]].round(3).to_string())
        g = {k: A.sharpe_m(A.period(A.monthly(res[k]["gross"]), p)) for k in BOOKS}
        t["sharpe_gross"] = pd.Series(g)
        print("gross Sharpe:", {k: round(v, 2) for k, v in g.items()})
        print("mean pairwise style correlation:", round(C.loc[list(model.STYLES), list(model.STYLES)]
                                                      .where(~np.eye(7, dtype=bool)).stack().mean(), 3))
        t.to_csv(OUT / "tables" / f"summary_{p}.csv")
        out[p] = t.to_dict(orient="index")
    (OUT / "runs").mkdir(parents=True, exist_ok=True)
    (OUT / "runs" / f"summary_{tag}.json").write_text(json.dumps(out, default=str, indent=1))


def hypotheses(res, bm, name):
    m = {k: A.period(A.monthly(res[k]["net"]), name) for k in BOOKS}
    best = json.loads((ROOT / "research" / "sources" / "best_single_style_devval.json").read_text())["best"]
    h = {"H1_blend_sharpe_positive": A.sharpe_positive_test(m["blend"]),
         "H2_corr_with_managed_futures": corr_test(m["blend"], A.period(bm["managed_futures"], name)),
         "H3_corr_with_60_40": corr_test(m["blend"], A.period(bm["sixty_forty"], name)),
         "H4_blend_minus_best_single_style": {"best_single_from_dev_val": best,
                                              **A.sharpe_diff_test(m["blend"], m[best])}}
    print(name, json.dumps(h, indent=1, default=lambda x: round(x, 4) if isinstance(x, float) else str(x)))
    (OUT / "runs" / f"hypotheses_{name}.json").write_text(json.dumps(h, indent=1, default=str))


def main(cmd):
    if cmd == "download":
        data.download()
        return
    if cmd == "build":
        data.build()
        return
    R, V, inst, m, rf, bench = load()
    res = model.run(R, V, m, inst, model.Config())
    # Pre-registered cost sensitivity (reported, no hypothesis): the same blend at half the per-contract cost.
    half = inst.assign(cost_bp=inst["cost_bp"] * 0.5)
    hb = model.run(R, V, m, half, model.Config())["blend"]
    res["blend_halfcost"] = hb
    (OUT / "runs").mkdir(parents=True, exist_ok=True)
    pd.DataFrame({k: res[k]["net"] for k in BOOKS}).to_parquet(OUT / "runs" / "net_daily.parquet")
    pd.DataFrame({k: res[k]["gross"] for k in BOOKS}).to_parquet(OUT / "runs" / "gross_daily.parquet")
    res["blend"]["weights"].to_parquet(OUT / "runs" / "blend_weights.parquet")
    res["blend"]["contrib"].to_parquet(OUT / "runs" / "blend_contrib.parquet")
    bm = benchmarks(bench, rf)
    if cmd == "dev":
        report(res, bm, ["development", "validation"], "devval")
        dv = {s: A.sharpe_m(pd.concat([A.period(A.monthly(res[s]["net"]), p) for p in ("development", "validation")]))
              for s in model.STYLES}
        best = max(dv, key=dv.get)
        (ROOT / "research" / "sources").mkdir(parents=True, exist_ok=True)
        (ROOT / "research" / "sources" / "best_single_style_devval.json").write_text(
            json.dumps({"sharpe_devval": dv, "best": best,
                        "blend": A.sharpe_m(pd.concat([A.period(A.monthly(res["blend"]["net"]), p)
                                                       for p in ("development", "validation")]))}, indent=1))
        print("dev+val style Sharpe:", {k: round(v, 3) for k, v in dv.items()}, "-> best", best)
        for p in ("development", "validation"):
            hypotheses(res, bm, p)
    elif cmd == "test":
        report(res, bm, ["test", "recent"], "test")
        hypotheses(res, bm, "test")
        hypotheses(res, bm, "recent")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev")
