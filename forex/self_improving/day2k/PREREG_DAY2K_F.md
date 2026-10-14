# PREREG DAY2K-F - round-number level reactions as the daily 1:1 setup (written 2026-10-14, the trader: "then you need to seek for better quality setups")

Rounds A-E ranked candidates by momentum, calendar, rates, volatility and volume features and found no edge. None tested a LEVEL setup: what price does the first time it reaches a round number of the day. This is a classic discretionary setup and needs only MT5 prices.

## Setup (event-driven, at most one per instrument-day)
Window 10:06..20:00 server (the 21:55 forced close and the no-23/0 rule are kept). Grid step G per instrument (fixed here, not tuned): XAUUSD 25 USD; SP 50 points; NSDQ 250; DOW 250; DAX 250; EURUSD, GBPUSD, AUDUSD, USDCAD, USDCHF 0.0050; USDJPY 0.50. The event of the day is the FIRST M1 bar of the window whose MID range crosses a grid line that the previous bar's mid close had not yet reached (up-cross: floor(mid high/G) > floor(prev mid close/G); down-cross symmetric; if both in one bar, the line nearer to the previous close). Level L = that line. Trade at the event: FADE (against the cross direction) or CONTINUE (with it). Entry price = L at mid, i.e. long at L + half the bar's spread, short at L - half the spread (spread cost paid both ways); stop = target = k x ATR20 of the instrument from the entry; the event bar's own range counts (conservative, same for the control), tie = loss, TP/SL checked on the executable exit side, forced close at 21:55 (partial result, reported).

## Control that makes the test sharp
The same pipeline on a grid shifted by 0.37 G (placebo grid P1) and by 0.23 G and 0.61 G (P2, P3). A real round-number effect must show on the true grid and vanish on the shifted grids; the acceptance below uses the difference.

## Trials (44) and acceptance
11 instruments x {fade, continue} x k {0.3, 0.6}. Bonferroni for 44, one-sided 5%: true grid DEV (2021-12..2024) block-t >= 3.10 AND the difference true-grid minus P1 (days with an event in both) block-t >= 2.0; VAL 2025: mean R > 0 and block-t >= 1.65 and >= 200 event days. HOLD (2026) opened once for a survivor.

## Gates
Positive control (oracle side per event) > +0.3 R; placebo grids P1-P3 must give 0 cells with DEV t >= 3.10 (P1 is the control in the difference; P2, P3 are independent placebo worlds). Truncation: the event and level of random days recomputed from bars before the event bar are identical.

## Honest prior
Round-number support/resistance is widely believed and weakly documented (some FX studies find small reversal effects at 00/50 levels). Prior of a survivor under 5%. Reported next to the result regardless: events per instrument, resolved share, win share of resolved trades (the "P of +2,000 day") for the true grid versus the shifted grids.

## Dry-run record (2026-10-14, before any cell P&L)
Events on the true grid per instrument over 1,066 days: 745-998 (DAX lowest, GBPUSD highest), similar counts on the shifted grids. Resolved share by stop or target before 21:55: k0.3 80-89%, k0.6 33-47%. Truncation test (event bar, level and direction unchanged with every later bar removed): 53/53. The first version of the truncation test was wrong (cutting later bars also removed the 21:55 exit bar, so the day was skipped); event detection was moved into its own function `find_event` and tested directly. No cell, trial count, threshold or period changed.
