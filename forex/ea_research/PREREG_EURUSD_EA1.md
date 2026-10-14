# Pre-registration EURUSD-EA1: a disciplined search for a better EURUSD rule (written 2026-10-14 before any run)
the trader: "find a better EA for EURUSD and only pass to the next pair once done with EURUSD". EURUSD only; this family is closed (pass or fail) before USDJPY / GBPUSD start.
Honest prior: the repo has no EURUSD edge after ~14 closed families; chance that any of these 24 cells survives all gates is about 3-5%.

## Data / clock / execution
MT5 broker EURUSD M1 bid/ask, server clock; H1 and D1 bars from M1 (mid for signals; real bid/ask for fills). Decision at the open of the 10:00 server H1 bar, Mon-Thu, 2022-03-01..2025-12-31 (the script refuses to load 2026 unless `--hold`).
All signals use only bars before the 10:00 bar (daily features from the previous completed day). Rollover rule: nothing is decided or executed in server hours 23 and 0 (24 bars from 10:00 ends at 09:00 next day).

## Signals (6 archetypes, each in two directions = 12 sides; features known at the decision)
- S1 daily stretch: z = (last daily close - daily EMA20) / ATR14(daily); active if |z| > 0.8.
- S2 daily RSI(2) (Wilder smoothing, alpha 1/2, daily closes; AMENDED A1 before any P&L: the first version, a 2-day simple average, was active on 32% of days because it reads 0/100 whenever two days move the same way): active if RSI2 < 10 (up signal) or > 90 (down signal).
- S3 prior-day close location CL = (close - low)/(high - low): active if CL > 0.8 (up) or < 0.2 (down).
- S4 overnight move: return from the open of the 02:00 server bar to the close of the 09:00 bar, active if |ret| > 2 x ATR14(H1).
- S5 last-24h move: return over the 24 H1 bars before the decision, active if |ret| > 1.0 x ATR14(H1) x sqrt(24).
- S6 weekly stretch (Tue-Thu only): (last H1 close - open of the first H1 bar of the week) / ATR14(daily), active if |.| > 1.0.
Direction "cont" = trade in the sign of the signal, "fade" = against it (S2: up signal = oversold, so "cont" buys oversold).

## Geometry (2)
G1 stop = max(20 pips, 2 x ATR14(H1)), target 1.5 R, exit at the close of the 24th H1 bar otherwise. G2 no target, stop = max(30 pips, 3 x ATR14(H1)), exit at the close of the 24th bar. Stop first if both are touched in one bar. R = result / stop.
Total cells: 6 x 2 x 2 = 24 (plus the 3 trials of FX3_TRENDBRACKET on the same data: 27 tests counted for the multiple-testing bar).

## Periods and gates
DEV 2022-03-01..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-09-30 (sealed; EURUSD 2026 was seen descriptively for the FX3_TRENDBRACKET rule only, this family's HOLD is unread, and a survivor also needs the forward log).
- G1 DEV: mean R > 0, t >= 3.0 (27 tests), n >= 100 trades.
- G2 VAL: mean R > 0, t >= 1.65, n >= 40.
- G3 positive in at least 3 of the 4 calendar years (2022 partial).
- G4 placebo ceiling: 500 permutations of each cell's signal sign across its active days; the real best DEV t must exceed the 95th percentile of the max |t| over the 24 cells.
Kill rule: no variants beyond these 24; no threshold tuning after any result; a survivor is audited (by exit hour, by year, spread, +1 bar latency) before it is recorded, then the sealed HOLD is opened once.
Output: EURUSD_EA1_RESULT.md, a ledger row, an Update in the checkpoint; survivors go to multi_fx_ea/candidates, not the top level.
