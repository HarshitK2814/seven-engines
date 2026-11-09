"""Shared loaders and statistics for the P8 v2 scripts. Signals at the close of t; v1 trades that close (lag 1),
v2 reports lag 2 (next close) as the realistic case. Only 2001-2017 enters choices."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
os.environ.setdefault("PREREG_HASH", "b14b0cc95d53")
TAB, FIG, RUNS = ROOT / "results/v2/tables", ROOT / "results/v2/figures", ROOT / "results/v2/runs"
for d in (TAB, FIG, RUNS):
    d.mkdir(parents=True, exist_ok=True)
END = "2017-12-31"
SEEN = "seen period (v1 reported it)"

from qcore.bootstrap import bootstrap_stat, percentile_ci  # noqa: E402
from multistyle import model  # noqa: E402


def load(end: str | None = END):
    import run as v1run
    R, V, inst, m, rf, bench = v1run.load()
    if end:
        R, V = R.loc[:end], V.loc[:end]
    return R, V, inst, m, rf, bench


def sh_d(r) -> float:
    r = pd.Series(np.asarray(r, dtype=float)).dropna()
    return float(r.mean() / r.std(ddof=1)) if len(r) > 2 and r.std(ddof=1) > 0 else float("nan")


def sh_a(r) -> float:
    return sh_d(r) * np.sqrt(252)


def sharpe_ci(r: pd.Series, n_boot: int = 1000, block: int = 21, seed: int = 0):
    d = bootstrap_stat(r, lambda x: sh_a(x), n_boot=n_boot, mean_block=block, seed=seed)
    lo, hi = percentile_ci(d)
    return sh_a(r), lo, hi


def diff_ci(a: pd.Series, b: pd.Series, n_boot: int = 1000, block: int = 21, seed: int = 0):
    D = pd.concat([a, b], axis=1, keys=["a", "b"]).dropna()
    d = bootstrap_stat(D, lambda x: sh_a(x["a"]) - sh_a(x["b"]), n_boot=n_boot, mean_block=block, seed=seed)
    lo, hi = percentile_ci(d)
    return sh_a(D["a"]) - sh_a(D["b"]), lo, hi


class BookCache:
    """style_books does not depend on the smoother/allocation, so cache it per data end date."""
    def __init__(self, V, macro, inst, cfg):
        self.V, self.macro, self.inst, self.cfg, self._c = V, macro, inst, cfg, {}

    def __call__(self, R):
        key = (R.index[-1], R.shape)
        if key not in self._c:
            self._c[key] = model.style_books(model.prepare(R), self.V.reindex(R.index), self.macro, self.inst, self.cfg)
        return self._c[key]
