# Results: Seven Engines (P8)

Monthly excess returns, net of per-contract costs (half tick + commission, plus rolls) unless marked gross.
Signals use the close of t; positions earn t+1. Pre-registration hash `e9f40ec73819`. Test = 2018-01 to 2024-12
(84 months). Same 37-market, six-sector universe as P7.

## Hypotheses

| | Claim (from the 10-K) | Test result | Verdict |
|---|---|---|---|
| H1 | The blend earns a positive return | Net Sharpe -0.24 [-0.72, 0.29]; gross 0.28 | **Not supported** (predicted) |
| H2 | "uncorrelated to ... the managed futures asset class" | corr 0.16, 95% CI [-0.07, 0.39]; upper bound < 0.50 | **Supported** |
| H3 | "uncorrelated to traditional asset classes" (60/40) | corr 0.19, CI [-0.18, 0.54]; not inside (-0.30, 0.30) | **Not supported** (too uncertain) |
| H4 | Blending beats the best single style (idiosyncratic) | +0.38 [-0.26, 1.13], p = 0.15 | **Not supported** |

## Styles (test 2018-24)

| Style | Net Sharpe | Gross Sharpe | Cost drag/yr |
|---|---|---|---|
| **Blend** | **-0.24** | **0.28** | 5.4% |
| Blend at half cost | 0.02 | 0.28 | 2.7% |
| momentum | -0.39 | -0.13 | 2.2% |
| carry | -0.14 | 0.05 | 1.2% |
| value | 0.03 | 0.18 | 1.2% |
| mean reversion | -0.59 | -0.13 | 5.2% |
| liquidity | -0.34 | 0.40 | 9.2% |
| **cross-market** | **0.40** | 0.46 | 0.6% |
| idiosyncratic | -0.61 | -0.46 | 1.2% |

The average pairwise correlation between the seven styles was 0.03: the styles genuinely are different return
streams. Two pairs are the exception: momentum and idiosyncratic momentum (0.71) and mean reversion and
liquidity (0.53), which are close cousins by construction (`results/tables/style_corr_test.csv`).

## What we learned

1. **The diversification claim is real.** Seven public-definition styles are nearly uncorrelated with each other
   (0.03) and with trend-following managed futures (0.16, CI upper bound 0.39). The 10-K's "uncorrelated to the
   managed futures asset class" holds for this architecture.
2. **But the edge is smaller than the trading bill.** Before costs the blend earned a 0.54, 0.87 and 0.28 Sharpe
   in development, validation and test. The two fast styles (5-day mean reversion, 1-day volume-conditioned
   reversal) turn over daily and cost 5-9%/yr at retail-style per-contract costs. A real programme lives or dies
   on execution: halving costs lifts the test Sharpe from -0.24 to 0.02, and to 0.38 in 2025-26.
3. **Cross-market links were the one style that worked out of sample** (net 0.40, almost no turnover): bond
   rallies leading equities, equity rallies leading bonds down, commodity moves leading commodity currencies.
   This is direct input to P4, which pre-registers a spanning test of exactly these signals.
4. **Last period's winner flopped.** Idiosyncratic (residual) momentum was the best style on dev+val and the worst
   in the test (-0.61), an out-of-sample example of why picking the best backtest is not a strategy.

## Recent period (2025-01 to 2026-10, 22 months; reported only)
Blend net 0.07 (half cost 0.38, gross 0.69); carry 0.64, value 0.56. Too short to test anything.
