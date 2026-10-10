# Z: "Trade with Pat" supply/demand zones (youtube WnzC8qnfhUA) on 35 MT5 broker: result (2026-10-10, local local clock)

Pre-registration `PREREG_SD_ZONES.md` (commit 0999ee3, before any simulation), script `sd_zones.py`, output `SD_ZONES_OUTPUT.txt`. Hold-out NOT opened.

## Verdict: the single-position rule FAILS; the "trading basket" wins 71% of the time and loses money overall, with 162 days that would have breached MT5 broker's daily line
| | 2022-24 | 2025 |
|---|---|---|
| Z1 single position (zone + break of structure + FVG + wick-in/close-out confirmation, target the impulse extreme) | 4,090 trades, win 35.0%, -0.039 R, PF 0.94, t -1.76 | 1,334 trades, win 34.9%, -0.067 R, PF 0.90, t -1.78 |
By class 2022-25: FX -0.063 R (4,487 trades), gold -0.151 R (139), indices +0.068 R (798, not a registered trial). About 113 trades a month over 35 markets.

Z2 basket (diagnostic, 1 + 2 + 4 units at three levels, first unit risking 0.15% as in the video), 2022-25: 5,424 baskets, **win rate 71.3%** (the single position: 35%), but **mean -83 USD per basket, total -452,150 USD over four years**; the worst basket lost 2,802 USD; on 162 days the summed basket losses were below -2,500 USD, each one a hard breach of an MT5 broker account.

## Reading
- The entry has no edge: 35% wins against targets typically 1.5-2 R away, slightly negative after costs in both periods.
- The basket turns the same entries into a high win rate. That is how the "24 wins in a row" streak happens: most baskets close at a small profit after averaging down. The losing baskets are many times larger, and the total is deeply negative. On a account account the large losses arrive as single bad days, exactly what MT5 broker's hard daily line ends. Never use this money management on the test.
