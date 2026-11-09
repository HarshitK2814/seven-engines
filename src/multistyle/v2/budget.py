"""D4/D5 helpers: Carver-style cost budget per style and the fixed fast-style restriction (prereg v2)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from multistyle import model


def cost_sharpe_units(cost: pd.Series, gross: pd.Series) -> float:
    """Annual cost (fraction of NAV) divided by the annualised volatility of the gross return."""
    return float(cost.mean() * 252 / (gross.std(ddof=1) * np.sqrt(252)))


def budget_ok(gross_sharpe: float, cost_units: float, frac: float = 1 / 3) -> bool:
    """D4: annual cost in Sharpe units at most one third of the gross Sharpe. No positive gross edge = fail."""
    return bool(np.isfinite(gross_sharpe) and gross_sharpe > 0 and cost_units <= frac * gross_sharpe)


def cheap_markets(cost_bp: pd.Series) -> list[str]:
    """D5: markets with cost_bp at or below the universe median (cutoff fixed in the prereg)."""
    return [str(c) for c in cost_bp.index[cost_bp <= cost_bp.median()]]


def restricted_style_book(R, V, macro, inst, cfg, style: str, keep: list[str]):
    """One style's vol-targeted book using only the markets in `keep` (signals of other markets removed before
    sizing, so risk is re-spread across the kept markets and the vol target is re-applied). All inputs at t are known at t."""
    sig = model.signals(R, V, macro, inst["sector"])[style]
    sig = sig.copy()
    sig.loc[:, [c for c in sig.columns if c not in keep]] = np.nan
    unit = model.unit_positions(R, sig, inst["sector"], cfg)
    W0 = (sig * unit).fillna(0.0)
    k = model.vol_scale(R, W0, cfg)
    return W0.mul(k, axis=0), unit.fillna(0.0).mul(k, axis=0), k
