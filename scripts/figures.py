"""Figures. Needs results/runs from `run.py test` (PREREG_HASH set)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from multistyle import analysis as A
from multistyle import model

ROOT = Path(__file__).resolve().parents[1]
FIG, RUNS, TAB = ROOT / "results" / "figures", ROOT / "results" / "runs", ROOT / "results" / "tables"
INK, MUTED, GRID = "#1f2328", "#6e7781", "#d8dee4"
BLUE, ORANGE, GREY = "#2f6fdf", "#e07b00", "#8c959f"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "figure.dpi": 150})
LABEL = {"mean_reversion": "mean\nreversion", "cross_market": "cross-\nmarket", "idiosyncratic": "idio-\nsyncratic"}


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    N = pd.read_parquet(RUNS / "net_daily.parquet")
    G = pd.read_parquet(RUNS / "gross_daily.parquet")
    books = ["blend"] + list(model.STYLES)

    # 1. Gross vs net Sharpe, test
    gs = [A.sharpe_m(A.period(A.monthly(G[k]), "test")) for k in books]
    ns = [A.sharpe_m(A.period(A.monthly(N[k]), "test")) for k in books]
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    x = np.arange(len(books))
    ax.bar(x - 0.2, gs, 0.4, color=GREY, label="Before costs")
    ax.bar(x + 0.2, ns, 0.4, color=BLUE, label="After costs")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x, [LABEL.get(k, k) for k in books], fontsize=8.5)
    ax.set_ylabel("Sharpe, locked test 2018-24")
    ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("Seven engines: what costs took away", loc="left", color=INK)
    fig.tight_layout()
    fig.savefig(FIG / "gross_vs_net.png")
    plt.close(fig)

    # 2. Style correlation heatmap, test
    C = pd.read_csv(TAB / "style_corr_test.csv", index_col=0).loc[list(model.STYLES), list(model.STYLES)]
    fig, ax = plt.subplots(figsize=(5.6, 4.8))
    im = ax.imshow(C.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(7), [k.replace("_", " ") for k in C.columns], rotation=45, ha="right", fontsize=8.5)
    ax.set_yticks(range(7), [k.replace("_", " ") for k in C.index], fontsize=8.5)
    for i in range(7):
        for j in range(7):
            ax.text(j, i, f"{C.iat[i, j]:.2f}", ha="center", va="center", fontsize=7.5,
                    color="white" if abs(C.iat[i, j]) > 0.6 else INK)
    ax.grid(False)
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title("Monthly correlation between styles, test", loc="left", color=INK, fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / "style_corr.png")
    plt.close(fig)

    # 3. Cumulative net and gross blend, plus cross-market
    fig, ax = plt.subplots(figsize=(9, 3.8))
    for s, c, lab, ls in ((G["blend"], GREY, "Blend before costs", "-"), (N["blend"], BLUE, "Blend after costs", "-"),
                          (N["cross_market"], ORANGE, "Cross-market style after costs", "-")):
        ax.plot((1 + s.loc["2001":]).cumprod(), color=c, lw=1.4, label=lab, ls=ls)
    ax.axvspan(pd.Timestamp("2018-01-01"), pd.Timestamp("2024-12-31"), color="#fff8c5", zorder=0)
    ax.set_yscale("log")
    ax.set_ylabel("Growth of $1 (excess return)")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("Seven-style blend, 37 markets, 10% vol target", loc="left", color=INK)
    fig.tight_layout()
    fig.savefig(FIG / "growth.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
