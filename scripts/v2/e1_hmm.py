"""P8 v2 Task 5 (E1, EXPLORATORY, never headline): two-state HMM on monthly [blend, SPY] returns, refit each January on
past data (>= 60 months). In the stress state tilt +50% to the two styles with the best past stress-state return.
Styles are combined from the seven styles' own monthly net returns (v1 buffer, lag 1, 2001-2017): an approximation of
the blend that ignores cross-style netting and the blend vol rescale; tilt trading costs are omitted.
Run: python scripts/v2/e1_hmm.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import run as v1run
from common import *  # noqa
from multistyle import analysis as A

from multistyle.v2.regime import best_stress_styles, stress_states, tilted_returns


def msh(x: pd.Series) -> float:
    return float(x.mean() / x.std(ddof=1) * np.sqrt(12))


def main():
    R, V, inst, m, rf, bench = load()
    cfg = model.Config()
    res = model.run(R, V, m, inst, cfg)
    mon = lambda s: ((1 + s).resample("ME").prod(min_count=1) - 1).dropna()
    S = pd.DataFrame({s: mon(res[s]["net"]) for s in model.STYLES}).loc["2001-01-01":]
    blend = mon(res["blend"]["net"]).loc["2001-01-01":]
    spy = v1run.benchmarks(bench, rf)["spy"].loc["2001-01-01":END]
    X = pd.concat([blend, spy], axis=1, keys=["blend", "spy"]).dropna()
    states, train_states = stress_states(X, min_months=60)
    picks = {d: best_stress_styles(S.loc[:d].iloc[:-1], ts) for d, ts in train_states.items()}
    out = tilted_returns(S, states, picks).dropna()
    out = out.loc[:END]
    sb, st = msh(out["base"]), msh(out["tilt"])
    dr = out["tilt"] - out["base"]
    D = out[["tilt", "base"]]
    bs = bootstrap_stat(D, lambda x: msh(x["tilt"]) - msh(x["base"]), n_boot=2000, mean_block=6)
    lo, hi = percentile_ci(bs)
    ci = lambda x: percentile_ci(bootstrap_stat(x, msh, n_boot=2000, mean_block=6))
    stress_share = float(states.dropna().loc[:END].mean())
    summary = {"label": "EXPLORATORY (E1), not a headline result", "window": [str(out.index[0].date()), str(out.index[-1].date())],
               "n_months": len(out), "stress_month_share": stress_share,
               "base_sharpe": [sb, *ci(out["base"])], "tilt_sharpe": [st, *ci(out["tilt"])],
               "diff_tilt_minus_base": [st - sb, lo, hi], "diff_ci_excludes_zero": bool(lo > 0 or hi < 0),
               "mean_monthly_diff": float(dr.mean()), "picks_by_refit": {str(k.date()): v for k, v in picks.items()},
               "note": "approximation via per-style monthly nets; tilt costs omitted; filtered (causal) states; "
                       "look-ahead perturbation test in tests/test_v2_hmm.py"}
    (TAB / "e1_hmm.json").write_text(json.dumps(summary, indent=1, default=float))
    states.rename("stress").to_csv(TAB / "e1_hmm_states.csv")
    print(json.dumps(summary, indent=1, default=float))


if __name__ == "__main__":
    main()
