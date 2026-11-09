# P8 evidence for v2 (multi-style futures)

Scope: what firms, papers, public code and SEC filings say about running several futures styles at once. v1 problem to fix: costs of 5.4%/yr turned gross Sharpe 0.28 into net -0.24 (test 2018-24). Task tags point to `06-p8-v2.md`. Links were checked on 2026-10-29. Where a site blocks bots (SSRN, man.com), the link came from a search result and is marked.

## Sources

| Source | Type | One-line finding | Link |
|---|---|---|---|
| Asness, Moskowitz, Pedersen, "Value and Momentum Everywhere" (JF 2013) | Firm/academic | Value and momentum premia exist in 8 markets and are negatively correlated, so blending them is the point. The paper is about gross premia; I found no futures cost analysis in the sources I read. | [AQR](https://www.aqr.com/library/journal-articles/value-and-momentum-everywhere), [PDF](https://www.johnhcochrane.com/s/Value-and-Momentum-Everywhere.pdf) |
| Koijen, Moskowitz, Pedersen, Vrugt, "Carry" (NBER 19325) | Firm/academic | Carry predicts returns in many asset classes; carry strategies lose together in global recessions. | [NBER](https://www.nber.org/papers/w19325) |
| Gârleanu and Pedersen, "Dynamic Trading with Predictable Returns and Transaction Costs" (NBER 15205, JF 2013) | Academic | With costs, trade only part of the way toward an "aim" portfolio. The aim is a weighted mix of today's and expected future target portfolios. Slow-decaying signals get more weight. | [NBER](https://www.nber.org/papers/w15205) |
| Novy-Marx and Velikov, "A Taxonomy of Anomalies and Their Trading Costs" (RFS 2016) | Academic | Most anomalies with one-sided monthly turnover under 50% keep significant net spreads. Few faster ones do. A buy/hold spread (harder to enter than to keep a position) is the best simple cost fix. | [NBER](https://www.nber.org/papers/w20721) |
| Frazzini, Israel, Moskowitz, "Trading Costs of Asset Pricing Anomalies" | Firm (AQR) | Real institutional execution data give costs far below older estimates, and value and momentum scale. Equities, not futures. | [NBER conf. PDF](https://conference.nber.org/conf_papers/f68262/f68262.pdf) |
| Leland, "Optimal Asset Rebalancing in the Presence of Transactions Costs" | Academic | A no-trade band around the target, trading only back to the edge, cuts trading costs about half vs quarterly rebalancing. | [RePEc/econwpa](https://econwpa.ub.uni-muenchen.de/econ-wp/fin/papers/9610/9610004.html) |
| Carver, "How fast should we trade?" | Practitioner blog | Speed limit: spend at most one third of expected pre-cost Sharpe on costs. Max trades/yr = (SR/3 - holding cost) / cost per trade. | [qoppac](https://qoppac.blogspot.com/2020/04/how-fast-should-we-trade.html) |
| Carver, "Fast but not furious" | Practitioner blog | Costs are measured in Sharpe units: (turnover + rolls) x cost per trade. Buffering plus a cost-penalised optimiser cuts turnover by roughly half to two thirds. Fast rules only on the cheapest instruments cost about 1 bp of SR vs a slow system. | [qoppac](https://qoppac.blogspot.com/2023/02/fast-but-not-furious-do-fast-trading.html) |
| Carver, "Optimising weights with costs" | Practitioner blog | Cost-aware weighting of rules, in the pysystemtrade framework. | [qoppac](https://qoppac.blogspot.com/2016/05/optimising-weights-with-costs.html) |
| pysystemtrade | Public code | Reference futures system. Its README only links to docs and I did not read the code; behaviour above comes from the blog posts. | [GitHub](https://github.com/robcarver17/pysystemtrade) |
| skfolio (BSD-3) | Public code | HRP, HERC, risk budgeting, inverse-vol, Ledoit-Wolf/OAS shrinkage, and optimiser options for transaction costs and turnover. | [GitHub](https://github.com/skfolio/skfolio) |
| Riskfolio-Lib | Public code | Alternative portfolio optimiser; not read in depth. | [GitHub](https://github.com/dcajasn/Riskfolio-Lib) |
| Lopez de Prado, "Building Diversified Portfolios that Outperform Out-of-Sample" (HRP) | Academic | HRP has lower out-of-sample variance than CLA in the author's tests; independent studies are mixed. (SSRN blocks bots.) | [SSRN](https://papers.ssrn.com/abstract=2708678) |
| Futures Portfolio Fund 10-K FY2023 | SEC | Multi-advisor CTA fund. Average $2.61 per US futures round turn (incl. NFA, execution, clearing, exchange fees). Margin-to-equity "rarely exceeds 35%". | [SEC](https://www.sec.gov/Archives/edgar/data/861441/000199937124004139/fpf-10k_123123.htm) |
| Frontier Funds 10-K FY2024 | SEC | Multi-advisor trust. Risk factor: "turnover ... may be high which could result in higher brokerage commissions". Typical advisor margin-to-equity 10-30%. | [SEC](https://www.sec.gov/Archives/edgar/data/1261379/000121390025026105/ea0232637-10k_frontier.htm) |
| P8 source 10-K (Ceres Tactical, in `research/sources/`) | SEC | Already read in v1. | local file |
| AQR Style Premia Alternative Fund page | Firm | Live product combining styles across asset classes. No turnover or trading-cost figure found on the page. | [AQR](https://funds.aqr.com/funds/aqr-style-premia-alternative-fund) |
| Man Group, Risk Premia | Firm | Multi-factor, multi-asset risk-premia product. Marketing page only; no cost data. (man.com blocks bots.) | [Man](https://www.man.com/strategies/risk-premia) |

Not found: Quant StackExchange and Reddit threads on this exact question (the search tool cannot reach reddit.com and returned no Quant SE hits). No forum claims are used below.

## What industry does that v1 does not

1. **Treats cost as a budget in Sharpe units, set before research.** Carver caps costs at one third of expected pre-cost Sharpe. v1 found the cost afterwards. With gross Sharpe 0.28, the budget is about 0.09 Sharpe; v1 paid about 0.52.
2. **Trades part of the way to the target (partial adjustment), not all of it.** Gârleanu-Pedersen: move toward an aim portfolio, not the raw signal. v1 had only a 10% no-trade band (`research/preregistration.md`).
3. **Gives fast signals a smaller share, or only the cheapest markets.** Carver runs fast rules only on cheap instruments. v1's two fast styles cost 5.2% (mean reversion) and 9.2% (liquidity) per year.
4. **Nets trades across styles before sending orders.** Most styles are nearly uncorrelated (v1 average 0.03), so some trades offset. I found no paper measuring this netting benefit; the benefit is a hypothesis to test on our own data, not a cited fact.
5. **Uses a buy/hold spread (entry harder than exit).** Novy-Marx and Velikov rank it the best simple fix.
6. **Reports costs in a funds-disclosure unit.** Real multi-advisor funds quote cost per round turn ($2.61 average in one 10-K) and margin-to-equity (up to about 35%).

## v2 decisions

| # | Decision | Tag | Task | Why |
|---|---|---|---|---|
| 1 | **Copy**: pre-register a cost budget = one third of gross Sharpe per style; any style that exceeds it at its measured turnover is cut or slowed, not tuned afterwards. | copy | 06 Task 2 (prereg) | Carver speed limit. Directly targets the 0.52 Sharpe cost bill. |
| 2 | **Copy**: partial-adjustment trading, `w_t = w_{t-1} + k (aim_t - w_{t-1})`, with `k` fixed in the prereg from signal half-life, not fitted on test. | copy | 06 Task 3 (H1, H2) | Gârleanu-Pedersen. v1 already has the plan's Task 3 for this; this is the evidence for it. |
| 3 | **Fix**: replace the flat 10% no-trade band with a per-market band that is wider for costly markets (use `cost_bp` from `configs/universe.yaml`), trading back to the edge. | fix | 06 Task 3 | Leland: trade to the band edge. Carver notes theory wants wider bands for expensive instruments. |
| 4 | **Fix**: net orders across the seven styles into one book per market, then apply the band to the net position. Report cost with and without netting. | fix | 06 Task 3 | v1 almost certainly paid each style separately (I did not re-read the code to confirm). Netting benefit is untested; test it, do not assume it. |
| 5 | **Fix**: slow the two fast styles (mean reversion, liquidity) or restrict them to the cheapest markets; pre-register the cutoff in `cost_bp`. If they still fail the budget, drop them and say so. | fix | 06 Task 2, 3 | Carver conditional allocation; v1 cost drags of 5.2% and 9.2%. |
| 6 | **Fix**: style allocation by HRP and inverse-vol, with Ledoit-Wolf shrinkage, vs v1 equal weight; judged on cost-adjusted out-of-sample Sharpe from CPCV on 2001-2017, with an overfitting audit. | fix | 06 Task 4 (D2, H3) | skfolio offers these. HRP out-of-sample gains are contested, so equal weight stays as the baseline. Do not pick weights from the 2018-26 seen period. |
| 7 | **Copy**: report cost as annual drag, Sharpe units, round turns/yr, and implied margin-to-equity, next to every PnL number. Compare v1's assumed cost to the $2.61 round-turn disclosure. | copy | 06 Task 5 (D1) | Matches how funds disclose. Also check v1's cost assumptions are not too high or too low. |
| 8 | **Reject**: tuning band width or `k` on 2018-24 to rescue the blend. Net Sharpe at half cost was 0.02, so cost cuts alone may not make the blend worthwhile; the honest result may still be "no". | reject | 06 Task 6 | Seen-period tuning breaks the amended holdout rule in the roadmap. |
| 9 | **Fix**: label every table with dates after 2017 `seen period (v1 reported it)`. | fix | 06 Task 6 | Roadmap rule. |

## Rejected ideas

| Idea | Reason |
|---|---|
| Use the AQR/Man fund pages as proof that costs are manageable | Neither page gives turnover or trading cost; expense ratios there are fund fees, not execution cost. |
| Assume equity-anomaly cost results (Frazzini et al., Novy-Marx and Velikov) apply to futures | Both are equity studies. Use them for method (buy/hold spread, band), not for cost levels. |
| Take HRP as better than equal weight by default | Evidence is mixed (see HRP source); test it, keep equal weight as baseline. |
| Cite forum threads | None could be reached or verified. |
| Claim netting across styles saves a given amount | No source measures it for futures styles. |
