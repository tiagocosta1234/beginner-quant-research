# PREREG_DOW_US30: the 4-symbol indicator and the A+ London 12 EMA on the Dow (US30 as the stand-in for MYM)

Written Mon 26 Oct 2026 ~10:1x local (local clock), BEFORE any result was computed. the trader: "test the YM on US30 since you dont have data".

## Data and costs
- MT5 broker US30 1-minute bid / ask, 2021-12 to 2026-10-16 (mid prices for signals and exits), converted from MT5 broker server time (Europe/Athens) to UTC / London.
- Costs as MYM futures, not the CFD spread: 1 point slippage per side + USD 1.20 per micro at USD 0.50 a point = **4.4 points round trip** (the same as the Pine indicator's MYM setting). The CFD tracks the cash Dow, MYM the futures: same intraday moves, a different level (basis).

## Test 1: the frozen indicator (track A of the forward test)
`LONDON_FIRST15_1TO1.pine` = Edge Lab 5 engine D1, buffer 0.5, floor 0.03 ATR, 1:1, 1m exits, stop first, flat 16:00 London. Every day with data.

## Test 2: the A+ London 12 EMA plan
Same mechanical rules as `PREREG_LONDON12_APLUS.md` (+ Amendment 1), except the stop band: the plan's 1.5-6.0 points is a GOLD number; for the Dow it is scaled to the same share of price as gold at USD 2,500: **0.06% to 0.24% of the entry price** (about 24-96 points at 40,000). Primary: A+ at 1:1. Secondary: A+ at 1.5R, hard rules only.

## Bar (alpha 0.025 each, two primaries: Test 1 and Test 2 A+ 1:1)
Mean net R > 0 AND random-side P <= 0.025 (20,000 coin flips to each trade's mirror) AND mean > 0 in at least 3 of the 5 years 2022-2026 AND n >= 100. Reported too: by year, 2026 alone.

## Honest prior
On GC / NQ / ES / SI the indicator lost (-0.06 to -0.17 R, 2019-2023) and the A+ plan made -0.02 R on gold. The Dow has the largest cost in points of the four (4.4). Expected: no pass.
