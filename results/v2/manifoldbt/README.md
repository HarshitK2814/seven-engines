# ManifoldBT runs on P8 price-only styles (v2)

- Rules: `mom` (12-1 style return, cs_rank tercile long/short) and `rev` (short-term reversal, -cs_zscore of w-day return). Code: `tools/mbt_parity/dsl_p8_styles.py`.
- Data: 33 tickers (<5% missing days in 2001-2017) as SYNTHETIC bars: price = 100*cumprod(1+r) from P8 returns, o=h=l=c. 2001-01-02..2017-12-29 only.
- Signal on close t, fill at close t+1 (signal_delay=1). Fee = median P7 cost_bp (one number for all legs). No slippage, no roll cost.
- Files per rule: `sweep_*.csv` (2001-2012), `walk_forward_*.json` (anchored, 8y train, 2y tests, 4 folds), `lookahead_*.json` (honest passes, deliberate `.lead(1)` caught), `monte_carlo_*.json` (10k block-bootstrap paths, GPU), `tearsheet_*.html`, `equity_*.parquet`, `metrics_*.json`.
- Carry, value, macro and other styles need FRED/other data and are NOT run in ManifoldBT.
- mbt Sharpe annualises with sqrt(365.25); not comparable to the qengine sqrt(252) figures. No CIs here; these are tool outputs, not results claims.
