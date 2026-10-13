# Limitations

* **L1 Same data limits as P7:** commodity roll yield is missing (front-month series), bonds are US-only synthetic
  constant-maturity, and two equity indices are cash-index proxies. This hurts carry most: we have no commodity or
  equity carry, so the carry style trades only FX and the US curve.
* **L2 Volume** for the liquidity style is Yahoo front-month volume, which drops and jumps around rolls; for the
  synthetic FX and bond series we borrow the matching CME future's volume.
* **L3 Costs** are per-contract estimates for small size (P7 L4). The fast styles are where this matters; a
  manager with better execution, intraday timing or smaller fast-style risk budgets would do better (see the
  half-cost book). We did not optimise the style risk budgets; that would have been tuning on the test question.
* **L4 Public definitions, not the manager's.** The 10-K names the styles only (Layer A). Every formula is a
  literature default fixed before the test (Layer B). One variant (EXP-002) was tried and rejected on dev+val.
* **L5 Benchmarks:** "managed futures" is the average of two large trend-following mutual funds, and "traditional
  assets" is a 60/40 SPY/AGG portfolio. Other proxies could give different correlations.
* **L6 84 test months:** correlation CIs are wide (H3 failed on width, not on the point estimate of 0.19).
