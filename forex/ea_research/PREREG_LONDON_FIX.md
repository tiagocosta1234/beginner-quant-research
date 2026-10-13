# Pre-registration: Family LF, reversal after the London 16:00 WM/R fix in the USD majors (written 2026-10-11, before any code or result)

Source: Evans, O'Neill, Rime, Saakvitne (2018) "Fixing the Fix? Assessing the Effectiveness of the 4pm Fix Benchmark"; Melvin & Prins (2015)
"Equity hedging and exchange rates at the London 4 p.m. fix". Mechanism: benchmark orders executed in the 5-minute fix window push prices;
the pressure is temporary and reverses after the window. Not tested in this repo (no 'fix' family in the ledger). Daily signal, 7 markets,
unrelated to gold, in liquid London afternoon hours (server ~18:00-19:00, outside the 23:00-01:00 window).

## Data and clock
MT5 broker M1 bid/ask `forex/data_mt5/{EURUSD,GBPUSD,AUDUSD,NZDUSD,USDJPY,USDCHF,USDCAD}_M1_rates.parquet`, server clock converted to Europe/London
with the `.dt` accessor (the NA lesson). London weekdays. mid = (bid + ask) / 2.

## Rule
- Pre-fix move r = mid at the close of the 15:59 minute / mid at the open of the 15:30 minute - 1 (each pair in its own quote direction).
- sigma = std of r over the previous 60 trading days of that pair (min 40).
- Trade AGAINST the move: side = -sign(r). Entry at the open of the 16:06 minute (after the 16:00-16:05 window), at the ask (buy) or bid (sell).
- Exit at the open of the 17:00 minute (LF1, LF2) or of the 19:00 minute (LF3), at the bid / ask.
- Cost: bars' bid/ask + 0.1 bp slippage each side. Result per trade in bp; daily portfolio = mean over that day's trades (0 if none).

## Variants (3, fixed now)
- LF1: every pair every day (no size filter), exit 17:00.
- LF2: only when |r| > 1.0 sigma, exit 17:00.
- LF3: LF2 with exit 19:00.

## Periods and acceptance
DEV 2022-01-01..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-09-30 (once, only for passing variants).
Accept for the hold-out: DEV daily-portfolio t >= 2.4, DEV mean > 0, VAL mean > 0, >= 300 DEV trades.
Then for the account: correlation with the pair <= 0.3 and pass70 MIX uplift >= +3 points by 22 Dec with at most +1 point breach.
