"""Seven model styles on one futures universe, each risk-scaled, then blended with equal risk.

Timing (tests/test_lookahead.py): every signal at t uses data up to the close of t; weights decided at t earn
day t+1. Signal definitions are fixed a priori from the public literature (research/preregistration.md):

momentum       12-1 month return t-stat, ranked within sector (Asness, Moskowitz & Pedersen 2013)
carry          FX: rate differential; bonds: (yield - 3m bill) per unit of bond vol; ranked within sector (Koijen et al. 2018)
value          5-year reversal, log(avg price 4.5-5.5 y ago / price), ranked within sector (AMP 2013)
mean_reversion tanh(-5-day return t-stat), time series (the manager's "<10-day" short-term strategies)
liquidity      tanh(-1-day return z x abnormal log volume): high-volume moves reverse (Campbell, Grossman & Wang 1993)
(EXP-002 tried 21-/5-day horizons for these two; dev+val net Sharpe fell from 0.04 to -0.20, so EXP-001 was kept.)
cross_market   pre-specified lead-lag links (Pitkajarvi, Suominen & Vaittinen 2020; P4 specification)
idiosyncratic  12-1 month momentum in the return relative to the instrument's sector (residual momentum)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252
STYLES = ("momentum", "carry", "value", "mean_reversion", "liquidity", "cross_market", "idiosyncratic")

CROSS_MARKET = {
    # target: (driver tickers, look-back days, sign)
    "equity": (["UST10"], 252, +1),                 # bond rally -> equities up
    "rates": (["ES=F"], 252, -1),                   # equity rally -> bonds down
    "EUR": (["^STOXX50E"], 252, +1), "JPY": (["NKD=F"], 252, +1), "GBP": (["^FTSE"], 252, +1),
    "AUD": (["HG=F", "GC=F"], 63, +1), "CAD": (["CL=F"], 63, +1), "MXN": (["CL=F"], 63, +1),
}


@dataclass
class Config:
    vol_com: int = 60
    instrument_vol: float = 0.40
    target_vol: float = 0.10
    cov_halflife: int = 126
    max_leverage: float = 6.0
    lag: int = 1
    buffer: float = 0.10


def prepare(R: pd.DataFrame) -> pd.DataFrame:
    started = R.notna().cumsum() > 0
    return R.fillna(0.0).where(started)


def _tstat(lr: pd.DataFrame, start: int, end: int, sd: pd.DataFrame) -> pd.DataFrame:
    """Sum of log returns over (t-start, t-end], divided by sd*sqrt(window)."""
    s = lr.rolling(start - end, min_periods=start - end).sum().shift(end)
    return s / (sd * np.sqrt(start - end))


def cs_rank(x: pd.DataFrame, sector: pd.Series) -> pd.DataFrame:
    """Cross-sectional rank within sector, mapped to [-1, 1]. Needs >= 2 live instruments."""
    sec = sector.reindex(x.columns)
    out = pd.DataFrame(np.nan, index=x.index, columns=x.columns)
    for s in sec.unique():
        cols = sec.index[sec == s]
        sub = x[cols]
        n = sub.notna().sum(axis=1)
        r = sub.rank(axis=1)
        out[cols] = ((r.sub(1, axis=0)).div((n - 1).where(n >= 2), axis=0) * 2 - 1)
    return out


def signals(R: pd.DataFrame, V: pd.DataFrame, macro: dict, sector: pd.Series) -> dict[str, pd.DataFrame]:
    lr = np.log1p(R)
    sd = lr.ewm(com=60, min_periods=60).std()
    sig = {}
    sig["momentum"] = cs_rank(_tstat(lr, 252, 21, sd), sector)

    carry = pd.DataFrame(np.nan, index=R.index, columns=R.columns)
    rates = macro["fx_rates"].reindex(R.index).ffill()
    for c in [c for c in R.columns if sector.get(c) == "fx" and c in rates]:
        carry[c] = rates[c] - rates["USD"]
    y, bill = macro["yields"].reindex(R.index).ffill(), macro["bill"].reindex(R.index).ffill()
    bvol = sd * np.sqrt(TRADING_DAYS)
    for c in [c for c in R.columns if sector.get(c) == "rates" and c in y]:
        carry[c] = (y[c] - bill) / bvol[c]
    sig["carry"] = cs_rank(carry, sector)

    P = lr.cumsum()
    old = np.exp(P).rolling(252, min_periods=200).mean().shift(1134)
    sig["value"] = cs_rank(np.log(old) - P, sector)

    sig["mean_reversion"] = np.tanh(-_tstat(lr, 5, 0, sd))

    z1 = lr / sd.shift(1)
    lv = np.log(V.where(V > 0))
    abn = (lv - lv.rolling(20, min_periods=15).median().shift(1)).clip(lower=0)
    sig["liquidity"] = np.tanh(-z1 * abn).where(abn.notna())

    cm = pd.DataFrame(np.nan, index=R.index, columns=R.columns)
    for target, (drivers, h, sign) in CROSS_MARKET.items():
        d = [x for x in drivers if x in R]
        driver = sum(np.tanh(_tstat(lr[[x]], h, 0, sd[[x]]).iloc[:, 0]) for x in d) / len(d)
        cols = [c for c in R.columns if sector.get(c) == target] if target in set(sector) else [target]
        for c in cols:
            if c in cm:
                cm[c] = sign * driver.where(R[c].notna())
    sig["cross_market"] = cm

    u = R / (sd.shift(1) * 1.0)
    sec = sector.reindex(R.columns)
    peer = u.T.groupby(sec).transform("mean").T
    e = (u - peer).clip(-6, 6)
    esd = e.rolling(252, min_periods=200).std()
    sig["idiosyncratic"] = np.tanh(e.rolling(231, min_periods=231).sum().shift(21) / (esd * np.sqrt(231)))
    return {k: v.reindex(columns=R.columns) for k, v in sig.items()}


def ewma_vol(R: pd.DataFrame, com: int) -> pd.DataFrame:
    return R.ewm(com=com, min_periods=com).std() * np.sqrt(TRADING_DAYS)


def unit_positions(R: pd.DataFrame, sig: pd.DataFrame, sector: pd.Series, cfg: Config) -> pd.DataFrame:
    """Full-signal weight: 40% / vol, equal risk across sectors where the style has a signal, equal within."""
    unit = (cfg.instrument_vol / ewma_vol(R, cfg.vol_com)).where(sig.notna())
    sec = sector.reindex(unit.columns)
    live = unit.notna()
    n_in = live.T.groupby(sec).transform("sum").T
    n_sec = live.T.groupby(sec).any().T.sum(axis=1)
    return (unit / n_in.replace(0, np.nan)).div(n_sec.replace(0, np.nan), axis=0)


def vol_scale(R: pd.DataFrame, W: pd.DataFrame, cfg: Config) -> pd.Series:
    X = R.reindex(columns=W.columns).fillna(0.0).to_numpy()
    Wn = W.fillna(0.0).to_numpy()
    lam = 0.5 ** (1 / cfg.cov_halflife)
    S = np.zeros((X.shape[1], X.shape[1]))
    k = np.full(len(X), np.nan)
    for t in range(len(X)):
        S = lam * S + (1 - lam) * np.outer(X[t], X[t])
        if t < 126:
            continue
        v = Wn[t] @ S @ Wn[t] * TRADING_DAYS
        g = np.abs(Wn[t]).sum()
        if v > 0 and g > 0:
            k[t] = min(cfg.target_vol / np.sqrt(v), cfg.max_leverage / g)
    return pd.Series(k, index=W.index)


def apply_buffer(W: pd.DataFrame, unit: pd.DataFrame, width: float) -> pd.DataFrame:
    T, U = W.to_numpy(), np.nan_to_num(unit.reindex_like(W).to_numpy())
    out, prev = np.zeros_like(T), np.zeros(T.shape[1])
    for t in range(len(T)):
        move = np.abs(T[t] - prev) > width * np.abs(U[t])
        prev = np.where(move | (U[t] == 0), T[t], prev)
        out[t] = prev
    return pd.DataFrame(out, index=W.index, columns=W.columns)


def costs(W: pd.DataFrame, inst: pd.DataFrame) -> pd.Series:
    c = inst["cost_bp"].reindex(W.columns).to_numpy() / 1e4
    rolls = inst["rolls"].reindex(W.columns).to_numpy() / TRADING_DAYS
    turnover = W.diff().abs().fillna(W.abs())
    return (turnover * c).sum(axis=1) + (W.abs() * 2 * c * rolls).sum(axis=1)


def _pnl(R, W, inst, cfg, live) -> dict:
    Rx = R.reindex(columns=W.columns).fillna(0.0)
    held = W.shift(cfg.lag).fillna(0.0)
    gross = (held * Rx).sum(axis=1)
    cost = costs(W, inst).shift(cfg.lag).fillna(0.0)
    started = live.shift(cfg.lag, fill_value=False)
    return {"gross": gross[started], "net": (gross - cost)[started], "cost": cost[started], "weights": W,
            "contrib": (held * Rx)[started]}


def run(R: pd.DataFrame, V: pd.DataFrame, macro: dict, inst: pd.DataFrame, cfg: Config,
        styles: tuple[str, ...] = STYLES) -> dict[str, dict]:
    """Each style alone (vol-targeted, buffered, costed) and the equal-risk blend of the styles."""
    R = prepare(R)
    sector = inst["sector"]
    sig = signals(R, V, macro, sector)
    scaled, units, out = {}, {}, {}
    for s in styles:
        unit = unit_positions(R, sig[s], sector, cfg)
        W0 = (sig[s] * unit).fillna(0.0)
        k = vol_scale(R, W0, cfg)
        scaled[s] = W0.mul(k, axis=0)
        units[s] = unit.fillna(0.0).mul(k, axis=0)
        W = apply_buffer(scaled[s].fillna(0.0), units[s].fillna(0.0), cfg.buffer)
        out[s] = _pnl(R, W, inst, cfg, k.notna())
    live = pd.DataFrame({s: scaled[s].notna().any(axis=1) & (scaled[s].abs().sum(axis=1) > 0) for s in styles})
    n_live = live.sum(axis=1).replace(0, np.nan)
    Wb = sum(scaled[s].fillna(0.0) for s in styles).div(n_live, axis=0)
    Ub = sum(units[s].fillna(0.0) for s in styles).div(n_live, axis=0)
    kb = vol_scale(R, Wb.fillna(0.0), cfg)
    W = apply_buffer(Wb.mul(kb, axis=0).fillna(0.0), Ub.mul(kb, axis=0).fillna(0.0), cfg.buffer)
    out["blend"] = _pnl(R, W, inst, cfg, kb.notna() & (live.sum(axis=1) >= 4))
    out["blend"]["n_styles"] = live.sum(axis=1)
    return out
