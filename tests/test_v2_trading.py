import numpy as np
import pandas as pd
import pytest

from multistyle.v2.trading import instrument_rates, partial_adjust

P8 = __import__("pathlib").Path(__file__).resolve().parents[1]


def test_partial_adjust_converges_and_rate_one_is_identity():
    idx = pd.bdate_range("2020-01-01", periods=50)
    tgt = pd.DataFrame({"a": np.ones(50)}, index=idx)
    out = partial_adjust(tgt, 0.2)
    assert out["a"].iloc[0] == 0.2 and abs(out["a"].iloc[-1] - 1) < 1e-4
    pd.testing.assert_frame_equal(partial_adjust(tgt, 1.0), tgt)


def test_partial_adjust_cuts_turnover_on_noisy_target():
    rng = np.random.default_rng(0)
    tgt = pd.DataFrame({"a": rng.normal(size=500)})
    turn = lambda W: W.diff().abs().sum().iloc[0]
    assert turn(partial_adjust(tgt, 0.1)) < 0.2 * turn(tgt)


def test_rates_faster_in_cheap_markets():
    r = instrument_rates(0.2, pd.Series({"cheap": 0.5, "mid": 2.0, "dear": 8.0}), cost_scaled=True)
    assert r["cheap"] > r["mid"] > r["dear"] and r["mid"] == 0.2 and r.max() <= 1


def test_unscaled_rates_are_constant():
    r = instrument_rates(0.2, pd.Series({"a": 0.5, "b": 8.0}), cost_scaled=False)
    assert (r == 0.2).all()


def test_blend_buffer_equals_v1_run_on_toy():
    from multistyle import model
    from multistyle.v2.trading import blend_weights
    from test_lookahead import _toy
    R, V, inst, macro = _toy()
    cfg = model.Config()
    v1 = model.run(R, V, macro, inst, cfg)["blend"]["weights"]
    w = blend_weights(R, V, macro, inst, cfg, {"smoother": "buffer"})
    pd.testing.assert_frame_equal(w, v1, check_freq=False)


def test_blend_weights_lookahead_partial_cost_scaled():
    """Perturb R after the cut (V/macro unchanged: only R is shocked by check_lookahead; V and macro are
    exogenous inputs that are not perturbed here, the signal tests in test_lookahead cover them)."""
    from multistyle import model
    from multistyle.v2.trading import blend_weights
    from qengine.lookahead import check_lookahead
    from test_lookahead import _toy
    R, V, inst, macro = _toy()
    cfg = model.Config()
    check_lookahead(lambda X: blend_weights(X, V, macro, inst, cfg,
                                            {"smoother": "partial", "rate": 0.2, "cost_scaled": True}),
                    R, cut=1500)


def test_alloc_changes_blend():
    from multistyle import model
    from multistyle.v2.trading import blend_weights
    from test_lookahead import _toy
    R, V, inst, macro = _toy()
    cfg = model.Config()
    idx = R.index
    al = pd.DataFrame(0.0, index=idx, columns=list(model.STYLES))
    al["momentum"] = 1.0
    w = blend_weights(R, V, macro, inst, cfg, {"smoother": "partial", "rate": 1.0, "alloc": al})
    s, u, k = model.style_books(model.prepare(R), V, macro, inst, cfg)
    ref = s["momentum"].fillna(0.0)
    kb = model.vol_scale(model.prepare(R), ref, cfg)
    pd.testing.assert_frame_equal(w, ref.mul(kb, axis=0).fillna(0.0), check_freq=False)
