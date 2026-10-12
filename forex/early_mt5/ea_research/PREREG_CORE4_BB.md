# Pre-registration: the trader's "Core 4 + Bollinger" 4-hour RSI(2) variant on MT5 broker data (written 2026-10-12, before any MT5 broker bar was evaluated for it)

the trader pasted a script (Yahoo cash indices, 4 h bars from 1 h, `period=730d`): RSI(2) < 10 AND close > SMA(200 bars) AND close < lower Bollinger band (20 bars, 2 sd); exit when close > SMA(5 bars) OR RSI(2) > 70; markets SP, NSDQ, DOW, NIKKEI ("Core 4", DAX and ASX dropped); spread 2 bp flat per trade. On Yahoo (about 2024-10 .. 2026-10): about 80 trades, +27 bp per trade, semesters -31, -8, -9, +70, +52, +47 bp, indicative Sharpe 1.4. Two choices were made after seeing the previous run of the six-index version (dropping DAX and ASX because they were negative; adding the Bollinger filter), so the Yahoo window is IN-SAMPLE for them.

## Test: out-of-sample on MT5 broker data the script never saw
MT5 broker M1 bid/ask (`data_mt5`, swap-free), 4 h bars from M1 as in PREREG_INTRADAY_DIP.md (server clock, 14,400 s, drop bars with < 120 minutes), markets SP, NSDQ, DOW, NIKKEI.
Rule exactly as the trader's script: RSI(2) = 100 - 100/(1 + simple 2-bar mean of gains / simple 2-bar mean of losses) (Cutler form, as in the script, NOT Wilder); SMA(200), SMA(5), SMA(20), sd(20) of bar closes; entry when RSI(2) < 10 AND close > SMA(200) AND close < SMA(20) - 2 x sd(20); exit when close > SMA(5) OR RSI(2) > 70; one position per index. Execution (my framework, stricter than the script): signal at a bar close, ASK-open of the next bar in, BID-open of the bar after the exit signal out; the next bar must start within 2 bar lengths; no extra cost.
Observations: trades of the same calendar day (server date of entry) averaged into one.
Periods by entry date: **OUT-OF-SAMPLE = 2022-01-01 .. 2024-09-30 (decides)**; IN-SAMPLE = 2024-10-01 .. 2026-09-30 (the window the trader's script saw; reported only).

## Acceptance (out-of-sample only)
>= 40 observation-days, mean >= +15 bp per day-observation after the real spread, PF by day >= 1.3, one-sided t >= 1.65. If it passes, the pair/ManualDip correlation, an EA with a server-side stop, an MT5 broker tester run and the pass-speed gate follow; nothing goes live from this round.
Reported beside it: trades per year, indicative annualised Sharpe at 25,000 USD per trade, by-market means.

## Honest prior
Low to moderate. The Bollinger filter keeps about 8% of the RSI(2) signals (the most extreme drops), where reversal is stronger in theory, but about 40 trades a year cannot give a high Sharpe even with +27 bp each (about 1.4 on Yahoo), so this cannot be the 30-day system; it can only be one more small leg. Trial CB1.
