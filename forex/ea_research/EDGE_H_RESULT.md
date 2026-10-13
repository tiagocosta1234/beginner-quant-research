# Family H (2026-10-09 21:42 local): the search for a second edge "far greater than the current one" - three structurally different trials, none passes (ledger 57 -> 60)

Pre-registration `PREREG_EDGE_H.md` (21:42, before any run), runner `edge_h.py`, output `EDGE_H_OUTPUT.txt`, ledger rows `edge_h` (H1, H2, H3, DIAG-H3-daytime). Yardstick: the live pair's own daily t over the last 12 months is **+4.07** (guarded series, x1.2, partly in-sample for the SDB). Tier 1 bar: DEV daily t >= 2.5; Tier 2 ("far greater"): DEV t >= 4 and VAL t >= 2. No hold-out was opened.

| trial | DEV 2022-24 | VAL 2025 | verdict |
|---|---|---|---|
| H1 gold / silver ratio mean reversion (daily, z 60d, in 2.0 out 0.5, 27 trades) | 18 trades, +130 bp per trade, PF 2.4, daily t +0.95 | 6 trades, -484 bp, PF 0.19, t -0.86 | fails: 18 trades cannot carry a t-test and 2025 reverses it; pooled t +0.10 |
| H2 Brent / WTI ratio mean reversion (29 trades) | 18 trades, +0.2 bp, PF 1.00, t 0.00 | 5 trades, -57 bp, t -0.68 | fails: nothing |
| H3 overnight index drift, 6 index CFDs (cash close -> next open) | 4,507 index-trades, +0.38 bp, PF 1.01, t +0.23 | 1,444, +4.0 bp, PF 1.16, t +1.05 | fails: an effect of about 1 bp a night after costs (pooled +1.3 bp, t +0.83) |
| control: the same indices open -> close | +0.37 bp, t +0.19 | +0.10 bp, t +0.01 | nothing in the daytime either |
Correlation with the live pair over the last 12 months: H1 -0.03, H2 +0.01, H3 -0.05 (so they would diversify, but they have no edge to diversify with).
Details: H3 one-night holds +2.5 bp vs weekend holds -0.4 bp; per index the overnight mean is positive for NSDQ, SP, DAX, NIKKEI in the pool but only NIKKEI (+10 bp) and DAX (+8 bp) stand out in 2025 and none is stable across both periods. Spreads: DAX 0.5 bp, NIKKEI 1.2, ASX 3.2, gold 0.5, silver 3.2, Brent 6.5, WTI 5.4.

## What the 60 registered trials say
No second source of edge exists in this data outside gold: FX (carry, trend, NR7, EMA pullbacks, macro bias), crypto (1 and 5 minute TA), US / European / Asian indices (intraday momentum, EMA pullback, overnight drift, VIX bias), metals and energy spreads, gold range fade and USD / real-yield filters on the SDB. The pair (SDB + the 5-minute EA) is the only edge, it is gold, and it is probably gold-bull beta plus a good entry rule. A "far greater" edge is not what a public-data search of retail CFDs returns; what remains available to change the outcome is size, time and the number of independent attempts, not a new entry rule.
