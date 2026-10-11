# Pre-registration: Family NA, "noise area" intraday momentum on index CFDs (written 2026-10-11, before any code or result)

Source: Zarattini, Aziz, Barbon (2024), "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)", SSRN 4824172.
Reported on SPY 2007-2024: about 19.6% a year net, Sharpe about 1.33. Not tested in this repo before (ledger has index_intraday_mom = the
first-30-minutes rule, closed 2026-10-09; this is a different rule).

Why it fits the MT5 broker account: intraday only (flat before the US close, no overnight or weekend gaps), one decision every 30 minutes,
index CFDs that MT5 broker lists with no swap and no commission (checked 2026-10-11), likely low correlation with the gold pair. An EA can do
exactly what the simulation does (implementability rule after the 2026-10-11 clip erratum).

## Data and clock
MT5 broker M1 bid/ask bars `forex/early_mt5/data_mt5/{SP,NSDQ,DOW}_M1_rates.parquet` (server time = Europe/Athens wall clock), converted to New York time.
Session 09:30-16:00 New York. Days with fewer than 300 of the 390 session minutes are skipped. mid = (bid + ask) / 2.

## Rule (as in the paper; every input known at decision time)
- open_d = mid at 09:30 open of day d; close_{d-1} = mid at the 15:59 close of the previous session.
- For each minute-of-session k: move_d(k) = |mid_d(k) / open_d - 1|; sigma_d(k) = mean of move over the previous 14 sessions at the same k.
- Upper band UB(k) = max(open_d, close_{d-1}) * (1 + sigma_d(k)); lower band LB(k) = min(open_d, close_{d-1}) * (1 - sigma_d(k)).
- Decisions only at the close of the minutes 10:00, 10:30, ..., 15:30 New York. Fill at the NEXT minute's open, at the ask (buy) or bid (sell).
- Flat and mid > UB: go long. Flat and mid < LB: go short.
- Long exit (checked at the same half-hour marks): mid < max(UB, VW), where VW = time-weighted average mid since 09:30 (the CFDs have no
  real volume; TWAP replaces VWAP; declared here). Short exit mirrored: mid > min(LB, VW). After an exit the same half-hour mark may open
  the opposite side if its condition holds.
- Everything flat at the 15:59 minute close (fill at the 15:59 bar close bid/ask).
- Sizing in the test: constant notional of 100,000 USD per trade (results reported in bp of notional; the paper's vol targeting is
  NA-V below, not the main test). Cost: bid/ask from the bars + 0.1 bp slippage each side.

## Variants (3, fixed now)
- NA1: the rule above on SP, NSDQ, DOW, equal weight (daily result = mean of the three).
- NA2: NA1 without the VWAP/TWAP part (exit only when mid is back inside the band).
- NA3: NA1 on NSDQ alone.
(NA-V, vol targeting at 2% daily target / 14-day realised vol, max 4x, is a diagnostic only, reported for NA1.)

## Periods and acceptance
DEV 2022-01-01..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-09-30 (opened once, only for variants that pass DEV and VAL).
Accept for the hold-out if: DEV daily t >= 2.4 (3 variants plus the family history), DEV mean > 0, VAL mean > 0, at least 300 trade days in DEV.
Then for the account: correlation of the daily result with the pair (clean_boot_lib.series("MT5 broker", 1.2)) <= 0.3, and an uplift in the
clean simulation with at most 1 point of extra breach. Report negatives plainly.
