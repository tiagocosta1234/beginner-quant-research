# Pre-registration: intraday session scan on the 28 MT5 broker FX pairs (family FXS) (written 2026-10-12, before it was run)

the trader: "(original wording omitted)". The daily library found nothing in FX (`SETUP_SCAN_RESULT.md`); FX has its own structure by SESSION (Asia range, London open, New York), so this is the dedicated, intraday scan. 8 variants x 28 pairs = 224 tests, fixed rules, no tuning.

## Data and execution
MT5 broker M1 bid/ask (`data_mt5`, 28 pairs, 2021-12 .. 2026-10-02, swap-free). All times UTC (server Athens clock converted with EU DST). Spread: ask = bid + max(spread, the pair's median spread of the real-tick period 2025-10 .. 2026-09) in every year (earlier years are tester-modelled and too tight). Long enters at the ask and exits at the bid; short enters at the bid, exits at the ask; stops/targets checked minute by minute (bid high = max(bid-open, bid-close) of the minute, stop before target in the same minute, a gap through the stop exits at the open); a signal is read at the close of an H1 bar (the minute :59 bid close) and traded at the NEXT minute; return in bp of the entry price.
## The 8 variants (one trade per pair and day unless stated)
- ASIA_BRK: Asian range = high/low of 00:00-07:00 UTC (>= 300 minutes). The first H1 close from 07:00 to 11:00 beyond the range -> trade in its direction; SL = the opposite range boundary, TP = 1.0 x the range from entry, forced exit 16:00.
- ASIA_FADE: the same signal, the OPPOSITE direction, SL = 1.0 x range beyond the entry, TP = 1.0 x range, forced exit 16:00.
- LON_MOM: the 07:00-08:00 move (open to close) -> trade in its direction from 08:00, no stop/target, exit 12:00.
- LON_REV: the same, the opposite direction.
- NY_MOM: the 07:00-13:00 move -> trade in its direction from 13:00, exit 17:00.
- NY_REV: the same, the opposite direction.
- PDHL: previous UTC day high/low; the first H1 close from 07:00 to 11:00 beyond it -> trade in its direction, no stop/target, exit 16:00.
- H4RSI2: 4-hour bars (UTC), Wilder RSI(2) < 10 -> long, > 90 -> short at the bar close; exit when the close crosses its SMA(5) back (long: close > SMA5, short: close < SMA5) or after 5 bars; one position at a time.
## Windows and the rule that makes a "setup"
DEV = entries 2022-01-01 .. 2024-12-31; VAL = 2025; HOLD-OUT = 2026-01-01 .. 2026-09-30 (one look, survivors only).
SURVIVOR: DEV >= 100 trades; DEV mean >= +1.5 bp per trade after the spread (FX per-trade moves are small); DEV one-sided p (mean > 0) passes Benjamini-Hochberg across all 224 tests at q = 0.10; VAL >= 30 trades with mean > 0; then HOLD mean > 0.
Reported: tests nominally positive vs luck, top by DEV t, and the pooled mean by variant over all pairs (DEV / VAL / HOLD) since FX pairs are highly correlated.
## Honest prior
Low. FX session patterns are heavily arbitraged and the MT5 broker spreads (1-3 pips on majors, more on crosses) leave little room; a pooled variant that is positive in all three windows would be the real finding. Nothing goes live from this round.
