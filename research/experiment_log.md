# Experiment log (append-only)

Development = 2001-2012, validation = 2013-2017. The test period was locked for all of these. Data, cleaning,
carry-correct bonds/FX and costs are inherited from P7 (its EXP-001 to EXP-003).

| ID | Date | Period | What | Why | Result |
|---|---|---|---|---|---|
| EXP-001 | 2026-10-13 | dev+val | Seven styles as defined a priori (5-day mean reversion, 1-day volume-conditioned reversal) | baseline | Blend gross Sharpe 0.54 / 0.87, **net -0.04 / 0.23**: cost drag 4.7-5.6%/yr, mostly from the two fast styles (liquidity 8-10%/yr). Mean pairwise style correlation ~0. |
| EXP-002 | 2026-10-13 | dev+val | Mean reversion -> 21 days, liquidity -> 5 days | the 10-K says "generally medium-term"; cut turnover | Net blend dev -0.48, val 0.46; dev+val 0.04 -> **-0.20**. The 1-month reversal fights 1-month trends. **Rejected.** |
| EXP-003 | 2026-10-13 | dev+val | Kept EXP-001 (higher dev+val net Sharpe, 0.04 vs -0.20); added a half-cost blend as a reported sensitivity | selection between two logged variants on dev+val only | Half-cost blend 0.25 / 0.55 net. Best single style on dev+val: idiosyncratic (0.25). |
| - | 2026-10-13 | - | **Frozen.** | | |
| EXP-004 | 2026-10-13 | **test** | Locked test run (hash e9f40ec73819) | pre-registered | H2 supported; H1, H3, H4 not supported. See results.md. |
