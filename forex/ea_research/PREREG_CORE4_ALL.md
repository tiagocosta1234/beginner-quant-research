# Pre-registration: the trader's Bollinger + RSI(2) 4-hour rule on every MT5 broker symbol (written 2026-10-12, before the rule was run on any symbol outside SP/NSDQ/DOW/NIKKEI)

the trader: "(original wording omitted)". The rule is the one in his last pasted script, unchanged and not re-tuned (see PREREG_CORE4_BB.md; on SP/NSDQ/DOW/NIKKEI it failed out-of-sample, +2.7 bp, t 0.34 for 2022-01..2024-09, and works only in the window it was chosen on).
Rule: 4 h bars from MT5 broker M1 bid/ask (server clock, 14,400 s, drop bars with < 120 minutes), Cutler RSI(2) < 10 AND close > SMA(200 bars) AND close < SMA(20) - 2 x sd(20); exit when close > SMA(5) OR RSI(2) > 70; long only; one position per symbol; signal at a bar close, ASK-open of the next bar in, BID-open of the bar after the exit signal out (next bar must start within 2 bar lengths).
Symbols: every MT5 broker symbol in `data_mt5` (about 50), grouped: indices (SP, NSDQ, DOW, DAX, NIKKEI, ASX), metals (XAUUSD, XAGUSD), energy (WTI, BRENT), crypto (BTC, ETH, LTC, SOL, XRP, ADA, BNB, BCH), FX (all pairs present).

## Windows (by entry date)
OUT-OF-SAMPLE = 2022-01-01 .. 2024-09-30 (decides); IN-SAMPLE = 2024-10-01 .. 2026-09-30 (the window the script was tuned on; must be positive too).

## Statistic and acceptance
Per group, trades of the same calendar day (server date of entry) are averaged into one observation (one group is a trial; the all-symbols pool is a fifth trial, not a separate chance). Four group trials plus "all": five trials, so about one false pass is plausible by luck; that is why BOTH windows must pass.
Group passes if: out-of-sample >= 40 day-observations, mean >= +15 bp after the real spread, PF(day) >= 1.3, one-sided t >= 1.65, AND in-sample mean > 0. Per-symbol rows are descriptive only (reported with counts of positive symbols against what luck gives).
Also reported: trades per year per group and the indicative annualised Sharpe at 25,000 USD per trade.
A pass is a candidate only; nothing goes live from this round.

## Honest prior
Low. The rule has no edge out-of-sample on its own markets. Equity indices are the only place the dip effect was found, so the other groups should be near zero or negative; FX and crypto behave differently (trend, no leverage-driven dip reversal). The all-symbols pool is expected to be dominated by FX (about 28 of 50 symbols).
