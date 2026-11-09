import numpy as np
import pandas as pd

from multistyle.v2.regime import stress_states, tilted_returns


def _data(n=160, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2001-01-31", periods=n, freq="ME")
    calm = rng.normal(0.01, 0.01, (n, 2))
    wild = rng.normal(-0.01, 0.06, (n, 2))
    st = (rng.random(n) < 0.2)
    X = pd.DataFrame(np.where(st[:, None], wild, calm), index=idx, columns=["blend", "spy"])
    return X


def test_states_use_only_past_data():
    """Perturb months after 100: states up to month 100 must not change."""
    X = _data()
    X2 = X.copy()
    X2.iloc[101:] = X2.iloc[101:] * 3 + 0.05
    a, _ = stress_states(X, min_months=60)
    b, _ = stress_states(X2, min_months=60)
    end = X.index[100]
    pd.testing.assert_series_equal(a.loc[:end], b.loc[:end])
    assert a.dropna().isin([0, 1]).all() and a.first_valid_index() >= X.index[60]


def test_states_start_after_min_months():
    X = _data()
    a, _ = stress_states(X, min_months=60)
    assert a.loc[:X.index[59]].isna().all() and a.loc[X.index[60]:].notna().all()


def test_tilt_equals_equal_weight_when_never_stressed():
    X = _data()
    S = pd.DataFrame(np.random.default_rng(1).normal(0.003, 0.02, (160, 4)), index=X.index, columns=list("abcd"))
    states = pd.Series(0.0, index=X.index)
    out = tilted_returns(S, states, {pd.Timestamp("2001-01-01"): ["a", "b"]})
    pd.testing.assert_series_equal(out["tilt"].dropna(), out["base"].dropna(), check_names=False)
