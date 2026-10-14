# CRTF result (2026-10-14 ~22:45): Candle Range Theory traded as in reel 12 - NO EDGE
Pre-registration `PREREG_CRTF.md` (commit 451083d3), engine `crtf.py`, trades `D:\finance\si_ledgers\CRTF_trades.parquet`. Follows the trader's "you're not backtesting it right" on `CRT_RESULT.md`: this round adds the lower-timeframe entry inside candle 3 (session sweep -> M5 structure shift, stop under the manipulation, target the other end of candle 1, R:R >= 1), the weekly key level, and the 4H 1am-5am-9am NY model. 2026 never loaded.

Dry-run: truncation test PASS; hand check XAUUSD 2023-05-02 (candle 1 2023-04-28 L 1,976.18 H 1,995.02; candle 2 2023-05-01 swept the high to 2,006.06 and closed inside at 1,979.82; candle 3 London took the session high 1,985.25 -> 1,985.80, shifted down, short 10:20 server at 1,982.09, stop 1,985.80, target 1,976.18 = 1.6R; stopped out as gold ran to 2,019). Median stop 0.20% of price, median target 3.4R (F1/F2), 1.2R (F3).

| cell | DEV n | DEV net R | gross | t | VAL n | VAL net | gross | t | win % | median R |
|---|---|---|---|---|---|---|---|---|---|---|
| F1 daily CRT + LTF entry | 1,940 | -0.098 | -0.024 | -2.16 | 683 | -0.160 | -0.074 | -3.64 | 31.5 | -1.00 |
| F2 F1 + weekly key level | 916 | -0.119 | -0.048 | -2.11 | 303 | -0.119 | -0.039 | -1.38 | 31.2 | -1.00 |
| F3 4H 1-5-9 NY | 10,437 | -0.084 | -0.003 | -6.56 | 4,103 | -0.079 | +0.021 | -4.14 | 44.0 | -0.37 |
Placebo (same trigger on random days in the same direction; F3 random-day 09:01 NY entries): F1 -0.04..-0.11 R, F2 -0.01..-0.03 R, F3 -0.12..-0.13 R. 0 of 3 cells pass; negative in 2022, 2024, 2025 in every cell. The CRT context makes the lower-timeframe trigger WORSE than the same trigger on random days (F1 -0.098 vs placebo -0.04..-0.11; F2 -0.119 vs -0.01..-0.03), i.e. no information in the daily formation, as in CRT_RESULT.
By class: the only positive DEV corner is F1 on indices (+0.130 R, 270 trades), -0.041 in VAL. Gold: F1 +0.144 R on 45 trades (DEV), -0.316 on 8 (VAL); F2 19 / 3 trades: too few to read.

Reading: with the lower-timeframe confirmation, the weekly key level, or the 4-hour New York form, CRT still loses about 0.1 R a trade on MT5 broker prices 2022-2025, and is zero or negative before costs. The tight stop (0.2% of price) and the far target (3.4R) give the 31% win rate and the -1R median that make single recaps look spectacular. 5 CRT variants tested in this window, none passes. Closed; HOLD sealed.
