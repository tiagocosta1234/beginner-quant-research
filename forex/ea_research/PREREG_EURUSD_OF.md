# Pre-registration EURUSD-OF: order-flow proxies from real EURUSD ticks (written 2026-10-14 before any run)
the trader picked option 2 ("order-flow structure from real ticks"). EURUSD only. Honest prior for a survivor: about 2%. Related closed work: the HF family (`hf/HF_RESULT.md`, 12 markets, 1-minute decisions, 0/48) used tick counts as features; this family tests dedicated signed-flow imbalances at 15-60 minute horizons on EURUSD alone.

## Data and clock
MT5 broker EURUSD ticks `D:\finance\ticks\EURUSD\<YYYY-MM>.parquet` (time_msc on the SERVER clock, per lesson L13; flags: 2 = bid update, 4 = ask update), 2025-10-01 .. 2026-08-15. The sealed HOLD of this family is 2026-08-16 .. 2026-10-13 (the same untouched ticks the HF family sealed): the script loads no tick after 2026-08-15 23:59 unless `--hold`. Fills use the MT5 broker M1 bid/ask bars (`EURUSD_M1_rates.parquet`): entry at the OPEN of the entry minute at the ask (long) / bid (short), exit at the open of the minute H minutes later, slippage 0.1 bp per side, net basis points per trade.
## Features (minute grid built from ticks; at a decision only minutes before the entry minute are used)
Per minute: tick count n; up = ticks whose mid rose against the previous tick; dn = ticks whose mid fell; aonly = updates that changed the ask only; bonly = updates that changed the bid only.
For W in {5, 15, 60} minutes: I_W = (up - dn)/(up + dn) (tick-direction imbalance); Q_W = (aonly - bonly)/(aonly + bonly) (quote-update skew); active only if n_W >= 30. AMENDMENT A1 (before any P&L; the dry-run showed |I| >= 0.15 is active on 0-1% of slots and |Q| >= 0.15 on 45-60% with a permanent bid-only bias): the feature used by a rule cell is its causal z-score zI_W / zQ_W = (value - mean) / std over the previous 1,000 decision slots (about 15 trading days, current slot excluded, at least 300 observations).
## Decisions and trades
Decision slots: server minute :15, :30, :45 of hours 2..20, Monday-Friday. A trade enters at the open of the slot minute; one position at a time per cell; no entry or exit in server hours 23 and 0 and none in minutes 0-4 of an hour (the quote-boundary lesson of K2/K3).
Rule cells (36): feature in {I, Q} x W in {5, 15, 60} x direction in {cont, fade} x hold H in {15, 30, 60} minutes; active if |z| >= 1.5; cont = trade in the sign of the z-score, fade = against.
ML cells (3): histogram gradient boosting (depth 3, 200 iterations, learning rate 0.05, min leaf 50, L2 1.0) regressing the H-minute mid return (bp) on I_5, I_15, I_60, Q_5, Q_15, Q_60, n_5/n_60, mid return over 5, 15 and 60 minutes, spread at the last minute, hour; walk-forward: train 2025-10..2026-02 -> test 2026-03..05 (VAL); train 2025-10..2026-05 -> test 2026-06-01..08-15 (TEST); trade when |prediction| >= 1.0 bp; H in {15, 30, 60}. No tuning.
## Periods and gates
DEV 2025-10-01..2026-02-28, VAL 2026-03-01..2026-05-31, TEST 2026-06-01..2026-08-15, HOLD sealed.
Tests counted: 39 here + 67 earlier on EURUSD = 106, so DEV t >= 3.6.
- Rule cells: G1 DEV mean net > +1.0 bp, t >= 3.6, n >= 100; G2 VAL mean > 0, t >= 1.65, n >= 40; G3 TEST mean > 0, t >= 1.65, n >= 40.
- ML cells: VAL and TEST each: mean net > +0.5 bp, t >= 2.5, n >= 100 (the first window is training, so the ML cells have no DEV).
- G4 calibration: 300 permutations of the sign across each rule cell's active slots; the best real DEV t over the 36 rule cells must exceed the 95th percentile of the placebo maximum |t|; three placebo worlds for the ML (training labels permuted within days) must show no passing ML cell.
- Reported, not gated: by-hour trade table of the best cell, a +1 minute latency rerun, and the long-only drift yardstick.
Kill rule: no variants after any run; amendments only before any P&L, written here. A survivor is audited and then HOLD is opened once.
