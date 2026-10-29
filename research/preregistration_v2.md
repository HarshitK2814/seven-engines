# Pre-registration v2: Seven Engines (P8)
Frozen 2026-10-29. v1 pre-registration (hash e9f40ec73819) and its results are unchanged.

## Evidence ranking
1. Forward paper tracking from 2026-11 (only unseen data). 2. Walk-forward / CPCV on 2001-2017.
3. 2018-2026: seen period (v1 reported it); descriptive only. Every table with dates after 2017 carries the label `seen period (v1 reported it)`.

Timing: every signal is computed at the close of day t from data up to and including t. v1 trades at that close (lag 1); v2 reports lag 1 and the realistic lag 2 (next close).
v1 problem being attacked: costs of 5.4%/yr turned gross Sharpe 0.28 into net -0.24 (test 2018-24). Nothing here is tuned on 2018-2026.

## Primary hypotheses (walk-forward OOS 2009-2017: anchored folds, 2-year test blocks, parameters
## chosen on data before each block by plateau-smoothed net Sharpe; lag 2; v1 per-contract costs)
- **H1 (cost-aware trading).** Partial adjustment towards the target (grid: rate {0.05, 0.1, 0.2, 0.35,
  0.5, 1.0} x cost_scaled {no, yes}) cuts annual cost by at least 40% versus the v1 10% buffer while
  keeping gross Sharpe at least 80% of the v1 buffer's gross Sharpe on the same OOS dates.
  The rate is chosen only from data before each test block (never from 2018-2026); the grid is fixed here.
  With cost_scaled, rate_i = min(1, rate x sqrt(median cost / cost_i)): faster in cheap markets.
- **H2 (net result).** The H1 blend's net Sharpe exceeds the v1 blend's net Sharpe on the OOS dates;
  stationary-bootstrap 95% CI of the difference (mean block 21) excludes 0.
- **H3 (overfitting audit of v1).** Family = 7 single styles + blend x buffer {0, 0.05, 0.1, 0.2} x
  vol_com {30, 60, 120} (96 configs) on 2001-2017: PBO < 0.5 and v1 blend deflated Sharpe > 0.90.

## Descriptive (no hypothesis)
- D1 execution and capacity (as P7 D1): lag 1 vs lag 2; square-root impact (coef 0.25/0.5/1.0) at AUM
  $10m-$5bn; integer contracts; capacity = largest AUM with net Sharpe within 0.10 of the $10m value.
  ADV from Yahoo volume, with contracts.yaml used for FX futures and cash indices whose Yahoo volume is defective (P7 v2 data audit); a thin-ADV-off lower bound is also shown.
  Costs are also reported as annual drag, in Sharpe units, as round turns per year, and as implied margin-to-equity (margin 5% of notional,
  stated in the table), next to the $2.61 average round-turn cost in a multi-advisor fund 10-K (Futures Portfolio Fund FY2023) and its 10-35% margin band.
  Seen period: split by sector, labelled.
- D2 style allocation: equal-risk (v1) vs inverse-volatility vs HRP (skfolio, Ledoit-Wolf covariance, trailing 36 months,
  annual rebalance) vs trailing-net-Sharpe-weighted (floored at 0). Judged on net Sharpe with 95% CI from 2004 (36-month warm-up) to 2017, and by CPCV on 2001-2017.
  Equal-risk stays the baseline (HRP out-of-sample gains are contested). No weights are picked from 2018-2026.
- D3 crisis correlation: correlation with managed-futures benchmarks and SPY in the worst 10% SPY
  months vs all months (v1 H2 said 0.16 overall), with Fisher-z 95% CIs and the share of joint worst-decile months.
- D4 cost budget (Carver speed limit): per style, annual cost in Sharpe units must be at most one third of that style's
  gross Sharpe on 2001-2017, at its measured turnover. A style that exceeds it is slowed or restricted, not tuned afterwards;
  if it still fails, it is dropped and the drop is reported.
- D5 fast styles (mean reversion, liquidity): if a style breaks the D4 budget, it is restricted to markets whose
  cost_bp (configs/universe.yaml) is at or below the universe median; this cutoff is fixed here and not varied.
- D6 netting: cost of the blend, whose orders are netted across styles into one book per market, vs the sum of the
  seven styles' separate costs, with and without the band. The size of the netting benefit is untested and is reported as measured.
- D7 per-market bands: a variant where the no-trade band widens with market cost (scaled by the same sqrt(median cost / cost_i) rule, inverted), reported beside H1; it is not part of H1.
- D8 range of rates: the partial-adjustment rate is also reported against signal half-life (Gârleanu-Pedersen idea),
  shown for 2001-2012 only; no rate is chosen from a seen period.

## Exploratory
- E1 two-state Gaussian HMM (hmmlearn) on monthly blend returns, refit yearly on past data; style
  tilt in the "stress" state. Labelled exploratory, never headline.

## Forward test
From 2026-11: v1 blend, H1 blend, best D2 allocation. First read 2027-11. Report Sharpe with CI and rebalance count.

## What would change our conclusions
A bug found after freezing is fixed, logged in experiment_log_v2.md, and both numbers reported. The honest result may be "no":
at half cost the v1 blend's net Sharpe was only 0.02, so cost cuts alone may not make it worthwhile. Tuning bands or rates on 2018-2024 to rescue the blend is rejected.
