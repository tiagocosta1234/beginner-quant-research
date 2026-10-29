# CRT result (2026-10-14 ~22:30): daily Candle Range Theory on 46 MT5 broker - NO EDGE
Pre-registration `PREREG_CRT.md` (commit c83da32a), engine `crt.py`, trades `data\si_ledgers\CRT_trades.parquet`. Source: reel 12 (`reels/12_xauusd_x_alchemist/NOTAS.md`). 2026 never loaded.

Dry-run: truncation test PASS; hand check XAUUSD 2022-06-09 swept the 06-08 low (1,840.01 < 1,844.57), closed back inside (1,847.00), high under 1,859.66 -> long 2022-06-10 01:05.

| cell | DEV n | DEV net R | DEV gross | DEV t | VAL n | VAL net | VAL gross | VAL t | win % DEV |
|---|---|---|---|---|---|---|---|---|---|
| CRT1 (exit end of candle 3) | 10,746 | -0.063 | +0.000 | -4.79 | 3,784 | -0.056 | -0.001 | -2.59 | ~46 |
| CRT5 (held up to 5 days) | 10,746 | -0.084 | -0.017 | -4.96 | 3,739 | -0.072 | -0.009 | -2.79 | ~43 |
Placebo (same geometry on random days, seeds 51-53): DEV net -0.08 to -0.10 R, gross -0.016 to +0.012. Negative every year 2022-2025 in both cells; 0 of 2 pass (only gate 4 is met, because the placebo loses a little more).

By class: nothing positive in both periods except metals in CRT1 (gross +0.033 DEV, +0.206 VAL on 485 / 161 trades); gold alone CRT1 net +0.026 R (239 trades, DEV) and +0.121 R (76, VAL): t about 0.4 and 1.0, inside noise and not a registered cell.

Reading: a day that sweeps the previous day's low (high) and closes back inside does not deliver the other side of the range more often than its geometry implies: the gross result is zero to three decimals on 10,746 trades. The reel's winning example (7-9 Oct 2026 gold) is one draw from a setup that breaks even before costs. Closed; HOLD sealed.
