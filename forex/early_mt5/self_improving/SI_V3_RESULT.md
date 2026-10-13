# Self-improving trader v3: result (2026-10-13)

Pre-registration: PREREG_SELF_IMPROVING.md Amendments 1-2. Code: platform_v3.py, loop3.py. Ledgers: SI_LEDGER_V3.csv (real), SI_PLACEBO_LEDGER_V3_{7,8,9}.csv (calibration), attempt1/ (the failed 20-day-block calibration). HOLD 2026 never read.

## Setup
46 MT5 broker symbols in four classes (idx 6, fx 28, cmd 4, crypto 8), one decision bar per local day, flat carry per calendar day (0.5 / 0.7 / 1.0 / 3.0 bp), null = common circular time shift of each spec's entries (400 shifts, same markets, side and holding days), cumulative Benjamini-Hochberg q=0.10 over every spec ever run, floors n>=80, >=40 days, mean >= 3 bp net.
Calibration gate: attempt 1 (20-day-block placebo) failed because the blocks keep short-term structure; attempt 2 (every day shuffled) gave 0/0/0 survivors in three worlds at m=3,000. Only then did the real run start.

## Real run: 40 generations x 300 = 12,000 specs
| generations | mean S1 survivors | best DEV z (mean) |
|---|---|---|
| 0-4 | 12.0 | 3.01 |
| 5-9 | 7.8 | 2.98 |
| 10-14 | 33.8 | 3.00 |
| 15-19 | 21.2 | 1.95 |
| 20-24 | 8.0 | 2.20 |
| 25-39 | 0 | 1.75, 1.47, 1.40 |
End state: **0 S1 survivors** at m=12,000 (the top rank needs p <= 8.3e-6; the smallest p in the whole run is 3.3e-4; best DEV z ever 3.41). The peak was 40 survivors at generation 13 (m=4,200); the last generation with any survivor was 24.

## What happened to everything that ever passed S1 (40 specs looked at on VAL 2025)
| Group | n | median VAL mean (bp/trade) | median VAL z |
|---|---|---|---|
| fx pop_short | 16 | +0.7 | 1.0 |
| cmd rsi_dip | 11 | -53.9 | -0.8 |
| crypto breakout | 9 | -104.4 | -1.0 |
| fx low_dip | 2 | +2.6 | 1.1 |
| crypto low_dip | 2 | -30.4 | 0.0 |
Median DEV mean of these 40: +39.5 bp per trade; median VAL mean: -1.0 bp. 15 of 40 had a positive VAL mean, 11 pass the (lenient) S2, only 7 reached +3 bp. The classic winner's curse: what looked like +40 bp in the search window is -1 bp the next year.

## Verdict
No spec in this search space (four families on 46 markets at the daily close, 2022-26) survives a calibrated test, so none goes to S3 (HOLD stays unread), S4, the tester or forward. The installed system stays. Not a failure of the machine: it is calibrated (0/0/0 in the placebo worlds), it corrected itself as the cumulative bar rose, and it gave the honest answer.
It also shows the limit of 'training': the best z per generation does not climb with more generations, because the loop recombines the same pieces. More generations do not help; new information does.

## Next (not started, the trader to choose)
1. New information through the same platform: XAUUSD intraday sessions, FX majors intraday, the macro event calendar, order-flow proxies from tick data (spread, tick volume).
2. A different kind of spec: cross-sectional (rank markets against each other, long the top / short the bottom) instead of single-market timing; the FX class has 28 markets for it.
3. Leave the machine idle; the installed system keeps the account.
