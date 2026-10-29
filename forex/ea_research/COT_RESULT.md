# P: CFTC COT positioning on 13 MT5 broker: result (2026-10-10, local local clock)

Pre-registration `PREREG_COT.md` (commit 777a2ae, before download), script `cot.py`, data `data\data_macro\cot\` (CFTC legacy futures-only 2020-2026), output `COT_OUTPUT.txt`. Hold-out NOT opened.

## Verdict: both trials fail acceptance 1
| trial | DEV 2021-24 | VAL 2025 |
|---|---|---|
| P1 contrarian at 52-week extremes of the net speculative % of open interest | 154 weeks, +13.3 bp/week, 52% up, t +1.15 | +5.4 bp, t +0.22 |
| P2 follow the 4-week change in speculative positioning | 154 weeks, -2.1 bp/week, t -0.39 | +3.6 bp, t +0.27 |
P1's average is carried by crude oil (+111 bp a trade over 80 market-weeks) while NSDQ (-57) and S&P (-14) lose: one market, not a pattern.

## Reading
Positioning extremes and flows add no reliable weekly information on these 13 markets in 2021-25. With this, every information source within reach (price rules daily/hourly/intraday, relative value, macro calendar, overnight, weekends, positioning) has been tested in registered rounds on 2026-10-10 and none passed.
