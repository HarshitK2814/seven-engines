"""Cost-aware trading (Garleanu & Pedersen 2013 intuition): move only part of the way to the target each
day, faster where trading is cheap. All inputs at t are known at the close of t."""

from __future__ import annotations

import numpy as np
import pandas as pd

from multistyle import model


def partial_adjust(target: pd.DataFrame, rate) -> pd.DataFrame:
    a = (rate.reindex(target.columns).to_numpy() if isinstance(rate, pd.Series)
         else np.full(target.shape[1], float(rate)))
    T = target.fillna(0.0).to_numpy()
    out, prev = np.zeros_like(T), np.zeros(T.shape[1])
    for t in range(len(T)):
        prev = prev + a * (T[t] - prev)
        out[t] = prev
    return pd.DataFrame(out, index=target.index, columns=target.columns)


def instrument_rates(rate: float, cost_bp: pd.Series, cost_scaled: bool) -> pd.Series:
    if not cost_scaled:
        return pd.Series(rate, index=cost_bp.index)
    return (rate * np.sqrt(cost_bp.median() / cost_bp)).clip(upper=1.0)


def band_widths(width: float, cost_bp: pd.Series) -> np.ndarray:
    """D7: the no-trade band widens with cost, the inverse of the rate rule: width_i = width x sqrt(cost_i / median)."""
    return (width * np.sqrt(cost_bp / cost_bp.median())).to_numpy()


def blend_weights(R, V, macro, inst, cfg, params: dict, books=None) -> pd.DataFrame:
    """Equal-risk (or `alloc`-weighted) blend of the seven style books, then a smoother.
    `books` = precomputed style_books output for this R (it does not depend on the smoother)."""
    R = model.prepare(R)
    scaled, units, _ = books if books is not None else model.style_books(R, V.reindex(R.index), macro, inst, cfg)
    styles = list(scaled)
    if params.get("alloc") is not None:
        al = params["alloc"].reindex(R.index).ffill()
        Wb = sum(scaled[s].fillna(0.0).mul(al[s], axis=0) for s in styles)
        Ub = sum(units[s].fillna(0.0).mul(al[s], axis=0) for s in styles)
    else:
        live = pd.DataFrame({s: scaled[s].abs().sum(axis=1) > 0 for s in styles})
        n = live.sum(axis=1).replace(0, np.nan)
        Wb = sum(scaled[s].fillna(0.0) for s in styles).div(n, axis=0)
        Ub = sum(units[s].fillna(0.0) for s in styles).div(n, axis=0)
    kb = model.vol_scale(R, Wb.fillna(0.0), cfg)
    target, unit = Wb.mul(kb, axis=0).fillna(0.0), Ub.mul(kb, axis=0).fillna(0.0)
    sm = params.get("smoother", "buffer")
    if sm == "buffer":
        return model.apply_buffer(target, unit, params.get("buffer", cfg.buffer))
    cost = inst["cost_bp"].reindex(target.columns)
    if sm == "cost_band":
        return model.apply_buffer(target, unit, band_widths(params.get("buffer", cfg.buffer), cost))
    rates = instrument_rates(params["rate"], cost, params.get("cost_scaled", False))
    return partial_adjust(target, rates)
