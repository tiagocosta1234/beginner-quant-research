# Pre-registration EURUSD-LAB2: four new-information families on EURUSD (written 2026-10-14 before any run)
the trader: "try everything to find a profitable strategy on EURUSD". EA1 (price-state archetypes, 24 cells) closed with 0 survivors. LAB2 adds families that use information the price rules did not: the MT5 calendar timing, cross-pair relative moves, tick volume, and prior-day pivot levels. One shared noise ceiling; 36 cells; EURUSD only.
Honest prior: about 3% that any cell survives all gates.

## Data, clock, execution (common)
MT5 broker M1 bid/ask for EURUSD (and GBPUSD, AUDUSD, NZDUSD for family X), server clock (Europe/Athens). MT5 calendar `data\data_macro\mt5_calendar.csv` (UTC; converted to the server clock via Europe/Athens), M1 tick volume `data\ticks_vol\EURUSD.parquet`.
Entry at the OPEN of the stated M1 minute at the ask (long) / bid (short); exit at the open of the M1 minute `hold` minutes later at bid / ask; slippage 0.1 bp per side; the result is net basis points per trade (no stop, no target). Nothing is entered or exited in server hours 23 and 0; a trade whose entry or exit minute has no bar is skipped. Only data before the entry minute is used. Script loads 2022-03-01..2025-12-31 unless `--hold`.

## Families and cells (36)
- C (calendar timing, 12 cells): every distinct release time of importance 3 events for currency USD (C-USD) or EUR (C-EUR), 2022-03.., one trade per release time. Let m = mid(t+10 min open) / mid(t-1 min open) - 1 (the immediate reaction of EURUSD). Active if |m| >= 4 bp. Direction "cont" = trade in the sign of m, "fade" = against. Entry at t+10 min; hold 60 min, 240 min, or to 23 hours later at the same minute (skipped if it falls in server hours 23/0 or has no bar). 2 currencies x 2 directions x 3 holds = 12.
- X (cross-pair relative, 8 cells): at the 10:05 and 16:05 server minutes, Mon-Thu. s = r_EUR(L) - mean(r_GBP(L), r_AUD(L), r_NZD(L)) over the last L hours (L = 6 or 24) from mid at xx:05. z = s / rolling std of s over the previous 250 observations of the same decision slot; active if |z| >= 1.0 (AMENDMENT A1 before any P&L: 1.5 gave only 40-73 entries in four years, below the n >= 100 gate). "cont" = trade EURUSD in the sign of s, "fade" = against. Hold 240 min. 2 slots x 2 L x 2 directions = 8.
- V (tick-volume surge, 8 cells): at 10:05 and 16:05, ratio = tick volume summed over the last L hours (L = 3 or 6) / median of the same-window sum on the previous 20 weekdays; active if ratio >= 1.25 (AMENDMENT A1 before any P&L: 1.5 gave 34-66 entries). Sign = sign of the EURUSD return over the same window. "cont"/"fade". Hold 240 min. 2 slots x 2 L x 2 directions = 8.
- P (prior-day pivot, 8 cells): P = (H + L + C)/3 of the previous server day, R1 = 2P - H, S1 = 2P - L; at 10:05 price p (mid close of the 10:04 bar). Active if |p - R1| < 0.25 x ATR14(daily) (signal +1, resistance) or |p - S1| < 0.25 x ATR14(daily) (signal -1, support), or (group P0) |p - P| < 0.25 x ATR14(daily) with signal = sign(previous-day close - P). "cont" = trade in the signal's sign, "fade" = against. Hold 240 min or 23 hours. 2 level groups x 2 directions x 2 holds = 8.

## Periods and gates
DEV 2022-03-01..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-09-30 (sealed; tick volume and the calendar end 2026-08-15).
Multiple-testing count: 36 cells + 27 earlier tests on this data = 63 tests, so a DEV t of 3.4 or more is required.
- G1 DEV: mean net > +1.0 bp, t >= 3.4, n >= 100. G2 VAL: mean > 0, t >= 1.65, n >= 40. G3 positive in at least 3 of 4 calendar years.
- G4 placebo: 500 permutations of each cell's signal sign across its active entries; the real best DEV t must exceed the 95th percentile of max |t| over the 36 cells.
A survivor is audited (year, hour, spread at entry, +1 minute latency) before recording; the HOLD is then opened once. No variants, no threshold tuning after any run; amendments only before any P&L, written here.
Output: EURUSD_LAB2_RESULT.md, ledger row, checkpoint Update.
