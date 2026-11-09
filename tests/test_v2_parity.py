"""v2 refactor must not change v1 numbers (checked on 2001-2017 only)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

P8 = Path(__file__).resolve().parents[1]
saved = P8 / "results/runs/net_daily.parquet"
STYLES = ["momentum", "carry", "value", "mean_reversion", "liquidity", "cross_market", "idiosyncratic"]


@pytest.fixture(scope="module")
def v1_out():
    import sys
    sys.path.insert(0, str(P8 / "scripts"))
    import run as v1run
    from multistyle import model
    R, V, inst, m, rf, bench = v1run.load()          # real return order of scripts/run.py:load()
    return model.run(R.loc[:"2017-12-31"], V.loc[:"2017-12-31"], m, inst, model.Config())


@pytest.mark.skipif(not saved.exists(), reason="needs v1 run outputs")
def test_run_rebuilds_v1_blend_and_styles(v1_out):
    v1 = pd.read_parquet(saved).loc[:"2017-12-31"]
    for book in ["blend"] + STYLES:
        common = v1_out[book]["net"].index.intersection(v1.index)
        assert len(common) > 3000
        assert np.allclose(v1_out[book]["net"].loc[common], v1[book].loc[common], atol=1e-10), book


def test_style_books_interface():
    from multistyle import model
    from test_lookahead import COLS, _toy
    R, V, inst, macro = _toy()
    scaled, units, k = model.style_books(model.prepare(R), V, macro, inst, model.Config())
    assert set(scaled) == set(units) == set(k) == set(model.STYLES)
    assert list(scaled["momentum"].columns) == COLS and k["momentum"].index.equals(R.index)
