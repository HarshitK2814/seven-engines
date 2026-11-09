import numpy as np
import pandas as pd

from multistyle.v2.budget import budget_ok, cheap_markets, cost_sharpe_units, restricted_style_book


def test_cost_in_sharpe_units_is_cost_over_vol():
    rng = np.random.default_rng(0)
    gross = pd.Series(rng.normal(0, 0.01, 1000))
    cost = pd.Series(0.0002, index=gross.index)
    assert abs(cost_sharpe_units(cost, gross) - 0.0002 * 252 / (gross.std(ddof=1) * np.sqrt(252))) < 1e-12


def test_budget_rule_one_third_of_gross_sharpe():
    assert budget_ok(0.9, 0.3) and not budget_ok(0.9, 0.31)
    assert not budget_ok(-0.1, 0.0) and not budget_ok(0.0, 0.0)   # no gross edge: cannot meet the budget
    assert not budget_ok(float("nan"), 0.1)


def test_cheap_markets_at_or_below_median():
    c = pd.Series({"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0, "e": 5.0})
    assert cheap_markets(c) == ["a", "b", "c"]          # median 3.0 is included


def test_restricted_book_zero_outside_keep_and_still_live():
    from multistyle import model
    from test_lookahead import _toy
    R, V, inst, macro = _toy()
    cfg = model.Config()
    Rp = model.prepare(R)
    keep = list(Rp.columns[: len(Rp.columns) // 2 + 1])
    for style in model.STYLES:
        scaled, units, k = restricted_style_book(Rp, V.reindex(Rp.index), macro, inst, cfg, style, keep)
        out = [c for c in Rp.columns if c not in keep]
        assert (scaled.loc[:, out].fillna(0) == 0).all().all() and (units.loc[:, out].fillna(0) == 0).all().all()
        assert scaled.loc[:, keep].abs().sum().sum() > 0
    full, _, _ = model.style_books(Rp, V.reindex(Rp.index), macro, inst, cfg, ("momentum",))
    same, _, _ = restricted_style_book(Rp, V.reindex(Rp.index), macro, inst, cfg, "momentum", list(Rp.columns))
    pd.testing.assert_frame_equal(same, full["momentum"])   # keeping all markets changes nothing
