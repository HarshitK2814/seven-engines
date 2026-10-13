# What the manager discloses (Layer A)

Source: Ceres Tactical Systematic L.P., **Form 10-K** for the fiscal year ended 31 Dec 2020 (CIK 1209709,
accession 0001193125-21-093858), Item 1, description of the trading advisor Episteme Capital Partners and its
Systematic Quest Program (25% of the partnership's capital at 31 Dec 2020). Saved as
`research/sources/ceres_tactical_10k_2020.htm`. Quotes are verbatim.

| # | Quote | What we take from it |
|---|---|---|
| Q1 | "The Systematic Quest Program is a diversified systematic global macro program that seeks to maximize returns by pursuing a diversified portfolio of systematic strategies subject to the constraints of its risk management framework." | Multi-strategy, risk-managed, diversified. |
| Q2 | "The trading strategies are generally medium-term and aim to exploit a number of sources of alpha based upon fundamental, technical, and liquidity effects." | Mostly medium-term; fundamental, technical and liquidity inputs. |
| Q3 | "This managed futures strategy consists of seven different model styles, which include carry, cross-market, idiosyncratic, liquidity, mean reversion, momentum, and value models." | Seven named model families. |
| Q4 | "By applying each of these trading styles, across multiple time horizons, the strategy blends multiple alpha drivers seeking consistent returns, uncorrelated to traditional asset classes and the managed futures asset class." | Two testable claims: low correlation with traditional assets and with managed futures (trend). |

## The three layers

* **A. Disclosed:** seven named styles (Q3), a blend (Q4), medium-term horizons (Q2), and the two "uncorrelated"
  claims (Q4). Nothing about markets, signal formulas, weights or risk targets.
* **B. Our reconstruction:** each style uses the standard public-literature definition (see the docstring of
  `src/multistyle/model.py` and the pre-registration), on the same 37-market, six-sector free-data universe as P7.
  Each style is scaled to 10% volatility; the blend gives each style equal risk and is rescaled to 10%.
* **C. Extensions:** a half-cost sensitivity (institutional execution) and per-style attribution.

We do **not** claim to reproduce the manager's programme; we test whether its disclosed architecture, built from
public definitions, delivers what its disclosure says it seeks.
