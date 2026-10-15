# Pre-registration BRK-USDIDX (breakout day, round 23; written 2026-10-15 12:50 local (commit time), before any code or result)
Question: is the breakout of a currency INDEX (less noise than one pair) a better signal than the pair's own breakout?
USD index = mean of the log mid prices of USDJPY, USDCHF, USDCAD and the negated logs of EURUSD, GBPUSD, AUDUSD (MT5 broker M1, aligned minutes). London session clock: box = 08:00-08:30 London of the index (minute closes); signal = the first minute close (08:30-11:00) beyond the box; the trade = the pair in the index's direction (USD up -> EURUSD short / USDJPY long), entered at the next minute's executable price; stop = the PAIR's own 08:00-08:30 box other side (bid chart), R = |entry - stop|; hold to 17:00 London (capped 22:55 server). R >= 2 spreads.
Cells (2): X1 trade EURUSD; X2 trade USDJPY. Reference (reported, not a cell): each pair's own session breakout (round 1 X4).
Random-entry control (same window, random side, same R). Gates (DEV 2022-24, VAL 2025, 2026 non-clean): DEV mean >= +0.05 R and t >= 2.24 (daily; Bonferroni 2); VAL mean > 0 and t >= 1.65; beats its control by >= 0.05 R in DEV and VAL.
Honest prior: about 5%.
