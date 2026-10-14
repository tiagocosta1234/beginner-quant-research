# Pre-registration FX3-TRENDBRACKET: the practice-round rule on every day of EURUSD 2022-25 (written 2026-10-14 before any run)
Origin: EURUSD blind chart rounds 2+3 (18 trades, 6 winners, -5.5R) under rules fixed before viewing. This tests the same rule on all days.
Data: MT5 broker EURUSD M1 bid/ask; H1 bars from M1 on the server clock; daily bars = server days, Mon-Fri. Decision at the open of the 10:00 server H1 bar, Mon-Thu only (the 24-bar horizon then ends within the week).
Rule M (main): daily EMA20 / EMA50 of daily mid closes (adjust=True, full history) up to the previous day. Long if EMA20 > EMA50 and last daily close > EMA20; short if EMA20 < EMA50 and close < EMA20; otherwise flat.
Skip if the last H1 bar before the decision moved more than 1.5 x ATR14(H1) (|close-open|; ATR14 = mean of (high-low) of the last 14 H1 bars).
Stop = max(20 pips, 2.0 x ATR14), target = 1.5 x stop, entry at ask (long) / bid (short) of the 10:00 bar open, exits at bid (long) / ask (short) when touched by the bar high/low; if both in the same bar the stop counts first; if neither within 24 H1 bars, exit at the close of the 24th bar.
Result in R (stop = 1R), real bid/ask.
Trials (3): M; R = same days and brackets with the side reversed (fade); F = on days M is flat, long with the same bracket (drift check).
Periods: DEV 2022-03-01..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-09-30 (unopened, only for a trial passing 1-2).
Accept 1: DEV mean R > 0 and t >= 2.4 (three trials, two-sided). Accept 2: VAL mean R > 0, t >= 1.65. Accept 3: beats a same-mix permutation null (side shuffled across days, 1,000 draws) at the 95th percentile of its mean R in DEV.
Hit-rate break-even for a 1.5R target is 40%; report the hit rate and exit shares (target / stop / time). Honest prior of an edge: under 5%. No variants beyond the three.
