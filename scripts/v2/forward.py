"""P8 v2 forward paper tracker. Books: v1_blend, h1_blend, alloc_annual_equal (best D2 allocation, H1 smoother).
Signal at close t, traded at the next close (lag 2), v1 costs, no impact. Only dates >= the forward start in
configs/splits_v2.yaml are written, through qcore.splits.select (locked by the v2 prereg hash b14b0cc95d53). Idempotent.
Usage: python scripts/v2/forward.py [--refresh]    (--refresh re-downloads data with the v1 functions first;
without it the tracker uses the data already on disk, so seen-period numbers cannot shift under us.)"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd
import yaml
from common import *  # noqa
from multistyle import data, macro
from multistyle.v2.books import build_weights
from multistyle.v2.forward_log import append_new
from qcore.splits import Splits, file_hash, select
from qengine.costs import CostModel
from qengine.engine import run_weights

PREREG = ROOT / "research" / "preregistration_v2.md"
OUT = ROOT / "results" / "v2" / "forward" / "forward.csv"


def main(refresh: bool = False) -> int:
    if refresh:
        data.download(); data.build(); macro.download_macro()
    R, V, inst, m, rf, bench = load(end=None)
    W, Rw = build_weights(R, V, m, inst)
    cm = CostModel.from_instruments(inst, 0.0)
    splits = Splits.from_dict(yaml.safe_load((ROOT / "configs" / "splits_v2.yaml").read_text()))
    h = file_hash(PREREG)
    rows = []
    for name, w in W.items():
        net = run_weights(w, Rw, cm, lag=2).net
        f = select(net, splits, "forward", PREREG)
        rows.append(pd.DataFrame({"date": f.index, "book": name, "net_return": f.to_numpy(), "prereg_hash": h}))
    rows = pd.concat(rows, ignore_index=True)
    n_new = append_new(OUT, rows)
    log = pd.read_csv(OUT, parse_dates=["date"])
    days = log["date"].nunique()
    print(f"data ends {R.index[-1].date()}; forward start {splits.forward[0]}; new rows {n_new}; forward days tracked: {days}")
    return days


if __name__ == "__main__":
    main("--refresh" in sys.argv)
