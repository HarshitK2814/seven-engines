"""P8 v2 Task 4 (H3): overfitting audit of the v1 blend over 96 configs (7 styles + blend) x buffer {0,.05,.1,.2} x
vol_com {30,60,120}, 2001-2017, v1 timing (lag 1) and v1 costs. H3: PBO < 0.5 AND deflated Sharpe of v1 blend > 0.90.
Run: python scripts/v2/overfit_audit.py"""
from __future__ import annotations

import json
import sys
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from common import *  # noqa
from qcore.validation import (cpcv_paths, cpcv_splits, deflated_sharpe, expected_max_sharpe, group_index, pbo_cscv,
                              probabilistic_sharpe)

BUFFERS, COMS = (0.0, 0.05, 0.10, 0.20), (30, 60, 120)
BOOKS = ("blend",) + model.STYLES
V1 = "blend|b0.10|com60"


def main():
    R, V, inst, m, rf, bench = load()
    cache = RUNS / "family_2001_2017.parquet"
    if cache.exists():
        M = pd.read_parquet(cache)
    else:
        cols = {}
        for b, c in product(BUFFERS, COMS):
            out = model.run(R, V, m, inst, model.Config(buffer=b, vol_com=c))
            for k in BOOKS:
                cols[f"{k}|b{b:.2f}|com{c}"] = out[k]["net"]
        M = pd.DataFrame(cols)
        M.to_parquet(cache)
    full_idx = M.index
    M = M.loc["2001-01-01":END].dropna()
    assert M.shape[1] == 96
    ref = pd.read_parquet(ROOT / "results/runs/net_daily.parquet")["blend"].loc[:END]
    cm = M.index.intersection(ref.index)
    assert np.allclose(M[V1].loc[cm], ref.loc[cm], atol=1e-10), "family v1 column != saved v1 blend"

    sr = M.apply(sh_d); sr_var = float(sr.var(ddof=1))
    pbo = pbo_cscv(M, n_blocks=16)
    dsr = deflated_sharpe(M[V1], 96, sr_var)
    sr_star = expected_max_sharpe(96, sr_var)
    psr0 = probabilistic_sharpe(M[V1], 0.0)
    v1s = sharpe_ci(M[V1])

    G, K = 8, 2
    gi = group_index(M.index, G); X = M.to_numpy(); names = list(M.columns)
    oos, picks = {}, []
    for tr, te, tg in cpcv_splits(len(M), n_groups=G, k_test=K, purge=0, embargo=21):
        s_tr = X[tr].mean(axis=0) / X[tr].std(axis=0, ddof=1)
        j = int(np.argmax(s_tr)); picks.append(names[j]); oos[tg] = pd.Series(X[te, j], index=M.index[te])
    paths = cpcv_paths(oos, G, K, gi)
    prow = []
    for i, p in enumerate(paths):
        s = sharpe_ci(p, 500)
        prow.append({"path": i, "ann_sharpe": s[0], "ci95_lo": s[1], "ci95_hi": s[2], "n_days": len(p)})
    psh = np.array([r["ann_sharpe"] for r in prow])

    h3_pbo, h3_dsr = bool(pbo["pbo"] < 0.5), bool(dsr > 0.90)
    out = {"window": [str(M.index[0].date()), str(M.index[-1].date())], "n_days": len(M), "n_trials": 96,
           "note_window": "the 96 configs are all live only from this date (value needs 5 years of history; vol_com 120)",
           "pbo": pbo["pbo"], "pbo_n_combinations": pbo["n_combinations"],
           "sr_var_per_period": sr_var, "expected_max_sharpe_annualised": sr_star * np.sqrt(252),
           "v1_blend_ann_sharpe": v1s[0], "v1_blend_ci95": [v1s[1], v1s[2]], "v1_psr_vs_0": psr0,
           "v1_deflated_sharpe": dsr, "best_in_sample": sr.idxmax(), "best_in_sample_ann_sharpe": float(sr.max() * np.sqrt(252)),
           "n_configs_sharpe_gt_0": int((sr > 0).sum()),
           "family_ann_sharpe_quantiles": {str(q): float(sr.quantile(q) * np.sqrt(252)) for q in (0, .25, .5, .75, 1)},
           "cpcv": {"n_groups": G, "k_test": K, "embargo": 21, "n_splits": len(picks), "paths": prow,
                    "median_path": float(np.median(psh)), "min_path": float(psh.min()), "max_path": float(psh.max()),
                    "selected_counts": pd.Series(picks).value_counts().head(8).to_dict()},
           "H3": {"pbo_lt_0.5": h3_pbo, "dsr_gt_0.90": h3_dsr, "supported": h3_pbo and h3_dsr}}
    (TAB / "overfit_audit.json").write_text(json.dumps(out, indent=1, default=float))
    (sr * np.sqrt(252)).rename("ann_sharpe").to_csv(TAB / "overfit_family_sharpe.csv")
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.hist(pbo["logits"], bins=40, color="#4477aa"); ax.axvline(0, color="k", lw=1)
    ax.set_xlabel("logit of OOS rank of the in-sample best config"); ax.set_ylabel("CSCV combinations")
    ax.set_title(f"P8 v1 family (96 configs): PBO = {pbo['pbo']:.2f}")
    fig.tight_layout(); fig.savefig(FIG / "pbo_logits.png", dpi=130)
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
