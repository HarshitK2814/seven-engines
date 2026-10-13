# Pre-registration: Seven Engines (P8)

Frozen before the test period (2018-01 to 2024-12, 84 months) is read. The code refuses to load test data until
`PREREG_HASH` equals the SHA-256 prefix of this file. Development (2001-2012) and validation (2013-2017) informed
every choice (`experiment_log.md`).

## Question
A managed-futures advisor discloses in a 10-K that its programme blends seven model styles "seeking consistent
returns, uncorrelated to traditional asset classes and the managed futures asset class". Built from public
definitions on free data, does such a blend (i) earn a positive return net of costs, (ii) stay uncorrelated with
trend-following managed futures, (iii) stay uncorrelated with a 60/40 portfolio, and (iv) beat its best single style?

## Frozen system (`src/multistyle/model.py`, `configs/universe.yaml`)
Same 37 markets, data and cost model as P7 (per-contract half tick + commission plus two trades per roll).
Signals at the close of t; positions earn t+1. Each style: signal x 40%/vol, equal risk across the sectors where
it has a signal, scaled to 10% ex-ante vol (EWMA covariance, half-life 126 d), 10% no-trade band. Blend: equal
risk across live styles (at least 4 of 7), rescaled to 10%, costs charged on the netted blend positions.

| Style | Definition | Markets |
|---|---|---|
| momentum | rank within sector of the 12-1 month return t-stat | all |
| carry | FX: rate differential; bonds: (yield - 3m bill) / vol; rank within sector | FX, rates |
| value | rank within sector of log(average price 4.5-5.5 years ago / price) | all |
| mean_reversion | tanh(-5-day return t-stat) | all |
| liquidity | tanh(-1-day return z x positive abnormal log volume vs 20-day median) | all |
| cross_market | bond 12m -> equities (+); S&P 12m -> bonds (-); local equity 12m -> EUR, JPY, GBP (+); metals 3m -> AUD, oil 3m -> CAD, MXN (+) | equity, rates, 6 currencies |
| idiosyncratic | tanh(t-stat of the 12-1 month return relative to the sector average, in vol units) | all |

## Hypotheses (monthly net excess returns, test period)
* **H1:** Blend Sharpe > 0; stationary bootstrap (mean block 6, 5,000 draws), one-sided p < 0.05. On dev+val
  the blend earned 0.04 net (0.54 / 0.87 gross in dev / val), so we expect H1 to fail at full costs.
* **H2 (uncorrelated with managed futures):** the upper bound of the 95% bootstrap CI of the monthly correlation
  between the blend and the average of two large trend-following mutual funds (AQMIX, ASFYX) is below 0.50.
* **H3 (uncorrelated with traditional assets):** the 95% bootstrap CI of the correlation with a 60/40 portfolio
  (60% SPY, 40% AGG, monthly rebalanced) lies inside (-0.30, 0.30).
* **H4 (blending helps):** Sharpe(blend) - Sharpe(best single style on dev+val = idiosyncratic) > 0, paired
  bootstrap, one-sided p < 0.05.

## Reported without a hypothesis
Each style alone (net and gross), the half-cost blend, cost drag, the style correlation matrix, and the 2025+
period (used for nothing).

Nothing in this file will be edited after the hash is set.
