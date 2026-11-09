import numpy as np
import pandas as pd

from multistyle.v2.allocation import rolling_alloc


def _m(n=120, k=4, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2001-01-31", periods=n, freq="ME")
    return pd.DataFrame(rng.normal(0.005, 0.03, (n, k)), index=idx, columns=list("abcd"))


def test_alloc_sums_to_one_and_uses_past_only():
    m = _m()
    idx = m.index
    for method in ("equal", "invvol", "hrp", "sharpe"):
        a = rolling_alloc(m, method)
        assert len(a) > 0 and np.allclose(a.sum(axis=1), 1) and (a >= 0).all().all()
    m2 = m.copy()
    m2.iloc[100:] *= -5
    for method in ("invvol", "hrp", "sharpe"):
        pd.testing.assert_frame_equal(rolling_alloc(m, method).loc[:idx[99]], rolling_alloc(m2, method).loc[:idx[99]])


def test_rebalance_dates_are_first_month_end_of_year_plus_one_day():
    a = rolling_alloc(_m(), "equal")
    assert (a.index.month == 2).all() or (a.index.day == 1).all()
    assert a.index[0] == pd.Timestamp("2004-02-01")        # 36 months of data exist at 2004-01-31


def test_style_without_full_window_gets_zero_weight():
    m = _m()
    m.loc[m.index < "2003-06-30", "d"] = np.nan             # d has < 36 months at the first rebalance
    a = rolling_alloc(m, "equal")
    assert a["d"].iloc[0] == 0 and np.isclose(a.iloc[0].sum(), 1)


def test_sharpe_weights_favour_winner_and_floor_losers():
    idx = pd.date_range("2001-01-31", periods=60, freq="ME")
    rng = np.random.default_rng(1)
    m = pd.DataFrame({"win": 0.02 + rng.normal(0, 0.01, 60), "lose": -0.02 + rng.normal(0, 0.01, 60)}, index=idx)
    a = rolling_alloc(m, "sharpe")
    assert (a["win"] > 0.99).all()
