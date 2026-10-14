# PREREG DAY2K - one setup per day, 1:1, +/-2,000 USD (written 2026-10-14, the trader: "forget the EAs we have, build a whole new strategy that either makes or loses 2000$ every day, any forex pair, one setup per day, 1:1")

## The object
Each trading day one pair out of the 28 FX pairs in `forex/data_mt5` and one side are chosen from information available at the decision time T; entry at market; stop loss and take profit at the same distance D (1:1) from the executable entry price; lots sized so a stop costs 2,000 USD (so a win is +2,000, a loss -2,000: the daily result is +/-1 R, R = 2,000 USD). Any position still open at 21:55 server time is closed there (a partial result, reported as "unresolved"; it is a deviation from "exactly +/-2,000" and its share is a result in itself).

## Honest prior (written before any result)
- 23 registered families before this one found no confirmed edge outside the gold pair; the FX battery (28 pairs, 616 cells) and the FX factor / trend / reversal / confluence families were all negative. P(any cell survives) before looking: under 5%.
- With no skill the result is a coin flip minus costs: R per trade about -s/(2D) (s = spread), P(+8,000 before -8,000) about 48-50%. That is the benchmark; a "pass" from this design with no edge is luck, and MT5 broker lists coin-flip / all-or-nothing betting as gambling. Nothing here is a reason to deploy unless a cell survives every gate below.
- Power: about 800 DEV days, SD of daily R about 1, so SE about 0.035 R: a true mean of +0.10 R (win share 55%) would show at t about 2.9; a true edge below +0.05 R is invisible. State this in the result.

## Data and rules (the project's standing rules, as checks)
- MT5 broker M1 bid/ask bars `forex/data_mt5/<PAIR>_M1_rates.parquet` (server clock, columns t bo bh bl bc sp ao ah al ac), 28 pairs, from 2021-12-01 (the 2020 rule is a lower bound; this is all the MT5 broker price history there is).
- Causal: score at T uses bars with start time <= T-60 s only; ATR20 uses complete previous days only; entry at the open of the bar starting at T+60 s (60 s latency): buy at ask open, sell at bid open; TP/SL checked on the exit side (long exits on bid high/low, short on ask low/high), the entry bar's range counts, a bar touching both levels counts as a loss, forced exit at the open of the 21:55 bar on the exit side.
- No decision, entry or exit at server hours 23 and 0 (rollover; lesson L13/K2): windows are 10:06..21:55 and 16:36..21:55.
- Business days Mon-Fri by server date. Windows: DEV 2021-12-01..2024-12-31, VAL 2025-01-01..2025-12-31, HOLD 2026-01-01..2026-09-30 (never loaded in the main run; opened once, only for a cell that passes DEV and VAL).

## Trials (24 cells + a no-skill baseline)
- Decision time T in {10:05, 16:35} server; distance D = k x ATR20 of that pair (mean over the previous 20 trading days of the daily bid high-low range), k in {0.4, 0.7}.
- Signals (score per pair, normalised by ATR20; the pair with the largest |score| is traded): M5 = p(T) - p(T, 5 trading days earlier); M1 = p(T) - p(T, previous trading day); AM = p(T) - p(01:05 same day). Each traded as continuation (side = sign(score)) or as fade (side = -sign(score)). 3 signals x 2 directions x 2 T x 2 k = 24 cells.
- Baseline "no-skill": the average over all 28 pairs x 2 sides of the same (T, k) outcome (expected result of a random pick).
- Positive control: oracle side chosen from the realised outcome (must score near +0.9 R; proves the engine can see an edge). Calibration gate: the same 24 cells with the score replaced by Gaussian noise, seeds 81-83, must give 0 survivors (at most 1 of 3 worlds may show 1; otherwise the gate fails and nothing is read).

## Acceptance (S1 = survivor)
DEV: mean R > 0 and block t >= 2.86 (blocks of 5 consecutive trading days; one-sided 5% / 24 trials) AND mean R above the baseline of the same (T,k); VAL: mean R > 0 and block t >= 1.65 with >= 200 days. A survivor is then audited (by pair, by side, by hour, by year, ex-best-30-days, spread sensitivity x2), run through the MT5 broker rules on its daily +/-R series (rolling starts), and only then opens HOLD once. Kill rule: no tuning of signals, T or k after any P&L is seen; amendments only before P&L and written here.

## Outputs
`DAY2K_RESULT.md`, ledger rows (`forex/ea_research/LEDGER.csv`, family day2k), checkpoint "Update N", `MT5 broker` P(pass) of the baseline and of any survivor.

## Dry-run record and amendment A1 (2026-10-14, before any cell P&L)
- Server clock confirmed (EURUSD mean spread 3.4 pips at server hour 0, 0.3 elsewhere). Valid pair-days 21.9k of 22.5k at both T. Hand check EURUSD 2023-06-14: long TP reached, SL not: R = +1 as the matrix says.
- A1: the first truncation test failed 4 of 40 because ATR20 was looked up by the day's own index (a partial day dropped by the 600-bar filter gave NaN). ATR20 is now defined as the mean of the 20 complete days strictly before day d whether or not day d exists. After the change the test gives 40/40 identical scores with all bars after T removed. No signal, T, k or rule changed.
- Resolution share (stop or target hit before 21:55), mechanical, from the dry-run: T10:05 k0.4 73.9%, k0.7 31.3%; T16:35 k0.4 39.6%, k0.7 8.8%. So "+/-2,000 every day" is only close to true for T10:05 / k0.4; the other cells close mostly at 21:55 with a partial result. The cells stay as registered; the share is reported per cell.
