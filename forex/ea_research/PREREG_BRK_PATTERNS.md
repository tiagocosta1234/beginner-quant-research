# PREREG BRK_PATTERNS - classic chart-pattern breakouts (never tested in this repo)

Registered 2026-10-16 ~17:20 local (local clock, second PC PC-2; frozen by sha256 at 18:07:40), before any P&L of these trials was computed.
the trader: "backtest every type of breakout" -> told that ~35 breakout families are already closed (`BREAKOUT_KNOWLEDGE.md`:
session/opening ranges, Donchian/turtle, squeeze, flags, round numbers, retests, SAR, pyramiding, weekly/monthly boxes,
NR4/NR7, inside days, ICT models, Asian range, tick-volume, volatility regime, news/trend filters, ML meta-labels; 0 pass)
-> chose "new patterns, on the second PC this weekend". The only breakout types with no test anywhere in `forex/ea_research`
are the geometric chart patterns and the 52-week high. This round tests them, once, with fixed textbook definitions.

## Data
MT5 broker's own M1 bars (bid OHLC + bar spread, ask = bid + spread), 46 markets, 2021-12-01..2026-10-16, pulled read-only from the
second PC's MT5 broker terminal on 2026-10-16 (`forex/ea_batch/mt5data_m1_export_laptop.py`, the trader's OK 17:10). Same schema and source as
the main PC's `forex/data_mt5/*_M1_rates.parquet` used by every earlier round. Server clock = Europe/Athens.

## Pattern bars and pivots (fixed a priori, no tuning)
- Pattern timeframes: H1 and H4 (server-clock boundaries) for patterns 1-7; D1 (server day) for pattern 8. Bars are built
  from M1 MID prices ((bid + ask) / 2). ATR = 14-bar ATR of the pattern timeframe (20-bar on D1).
- Swing pivots: bar i is a swing high if its high is > the highs of the 3 bars before and >= the highs of the 3 bars after;
  swing low mirrored. A pivot is KNOWN only after bar i+3 has closed (causal). Consecutive pivots of the same type are merged
  keeping the more extreme one, so the pivot list alternates high / low.
- A pattern is evaluated on each closed bar c using only pivots known at c; if valid, the stop order(s) are working during
  bar c+1 at the level computed at c+1 (line value projected to bar c+1). Pattern pivots must lie within the last 60 bars.
- "Flat" line: |slope| <= 0.02 ATR per bar. "Rising" / "falling": slope > +0.02 / < -0.02 ATR per bar.
- A pattern is armed only while the bar-c mid close is still on the inside of its breakout level(s) (not yet broken), and
  each pattern instance (its defining pivots / box) is traded at most once, whatever the outcome.

## The eight patterns
1. **TRI_SYM** symmetric triangle: upper line through the last two swing highs falling, lower line through the last two
   swing lows rising, height at bar c > 0 and < the height at the first of the four pivots. Buy stop at the upper line AND
   sell stop at the lower line (first to fill wins, the other is cancelled). SL = the opposite line at the fill bar.
   TP = measured move: entry +/- the height at the first pivot.
2. **TRI_FLAT** ascending / descending triangle: flat upper line + rising lower line -> buy stop at the upper line;
   flat lower line + falling upper line -> sell stop at the lower line. SL = opposite line at the fill bar; TP = measured move.
3. **WEDGE**: both lines slope the same way and converge (as in 1). Rising wedge -> sell stop at the lower line; falling
   wedge -> buy stop at the upper line. SL = opposite line at the fill bar; TP = measured move.
4. **TLINE** trendline break: falling line through the last two swing highs (>= 10 bars apart, no mid close above the line
   from the first high to bar c) -> buy stop at the line, SL = the last swing low. Mirror: rising line through the last two
   swing lows -> sell stop, SL = last swing high. No TP.
5. **HS** head and shoulders: the last five pivots are H-L-H-L-H (left shoulder, trough, head, trough, right shoulder) with
   head >= max(shoulders) + 0.5 ATR and |left - right shoulder| <= 1 ATR; neckline through the two troughs -> sell stop at
   the neckline, SL = right shoulder high, TP = neckline - (head - neckline at the head bar). Inverse H&S mirrored -> buy.
   Valid for 30 bars after the right shoulder.
6. **DARVAS** box: top = a bar high that is the highest of the previous 20 bars and is not exceeded by the next 3 bars;
   bottom = the lowest low after the top, not undercut by the next 3 bars, with the top still intact. Once both are set,
   buy stop at the top, SL = bottom, no TP; valid 20 bars. Mirror (20-bar low, short) -> sell stop.
7. **VCP** volatility contraction: close > 50-bar SMA; the last three swing-high -> next-swing-low pullbacks shrink, each
   depth <= 0.75 x the previous one -> buy stop at the last swing high, SL = the last swing low, no TP. Mirror below the
   SMA (three shrinking rallies) -> sell stop at the last swing low.
8. **HI52** 52-week high / low on D1: buy stop at the highest high of the previous 252 D1 bars; sell stop at the lowest
   low of the previous 252 D1 bars; SL = 2 ATR(20) from the entry; no TP. First signal needs 252 days of history
   (data from 2021-12 -> signals from about 2022-12).

## Fixed trade rule (all patterns)
- Fills on MT5 broker M1 bid/ask: buy stop fills on the first M1 bar whose ASK high >= level, at max(level, ask open); sell stop
  on BID low <= level at min(level, bid open). No fill in the server 23:00-00:59 rollover window (lesson (a)).
- Long exits on bid, short exits on ask; SL / TP gap rule = the open if it is beyond the level; same-minute SL + TP = SL;
  on the fill minute only the SL counts (`orbx.walk` semantics). SL / TP stay live in the rollover window (real cost).
- Time stop: 120 H1 bars, 60 H4 bars, 20 D1 bars after the fill; time exits in the rollover window move to 01:05 server.
- One open position per market per pattern per timeframe; a new entry only after the previous one exits.
- R = net P&L / |entry - SL| at the fill. Net of the real bar spread; account <acct> pays no swap and no commission.
- Trades still open at the end of the data are dropped. All 46 markets (crypto included).

## Trials (15)
TRI_SYM, TRI_FLAT, WEDGE, TLINE, HS, DARVAS, VCP, each on H1 and on H4 (14), plus HI52 on D1 (1). Long and short pooled
inside each trial (by-side tables are descriptive).

## Yardsticks (not trials)
- **Random-entry control (the main yardstick):** for each real trade, 10 entries in the same market, same calendar year,
  same side, at uniformly random pattern-bar opens outside the rollover window, with the same SL and TP distances as a
  share of the entry price and the same time stop. "Pattern information" = real mean R - control mean R.
- Long-only drift: the share of real-trade R earned by longs vs shorts, and the control's long/short split (lesson (b)).
- Width in spreads: distribution of |entry - SL| / spread at the fill (fact 6 of `BREAKOUT_KNOWLEDGE.md`).

## Periods
DEV 2022-01-01..2024-12-31 (selection), VAL 2025-01-01..2025-12-31, HOLD 2026-01-01..2026-10-16 (one look, only for
trials that pass DEV and VAL; none of these patterns has been run on 2026 or on any period before).
HI52's DEV is 2022-12..2024-12 (history requirement).

## Statistics and acceptance
- Net R per trade pooled over markets, t clustered by day (`orbx.ct`).
- DEV: n >= 200, mean > 0, clustered t >= 2.71 (Bonferroni, 15 one-sided trials at 5%), real mean - control mean > 0 with
  t >= 2.0 (trade-level, control averaged per trade), mean > 0 in at least 2 of the 3 DEV years (2 of 2 for HI52).
- VAL: n >= 60, mean > 0, t >= 1.65. HOLD: mean > 0, t >= 1.65.
- A full passer then needs, before anyone calls it usable: an MT5 broker real-tick replay of its 2025-26 trades (300 ms latency),
  the MT5 broker pass-speed gate, and daily correlation <= 0.3 with D2.

## Dry run (before any P&L)
`python -m forex.ea_research.brk_patterns --dry-run`: signal and fill counts per trial, period and market; truncation
causality test (cut the data at random times on 3 markets; every signal and fill before the cut must be identical);
a hand check of 3 random signals per pattern printed with their pivots. The dry run walks exits only because the
one-position rule needs them (and the truncation test compares them for equality); no R or P&L figure is printed.
Amendments only before the run, written below with the reason.

## Honest prior
About 5%. Lo, Mamaysky and Wang (2000) found chart patterns shift the conditional return distribution a little but did
not show profits after costs; Osler and Chang (1995) found H&S profits in 1970s-90s FX that later work saw fade; Bulkowski's
statistics are in-sample. In this repo breakout information is +0.03..+0.05 R against 0.04..0.22 R of spread on intraday
boxes. The one structural advantage here is size: H1/H4/D1 patterns have stops many spreads wide, so the cost per R is small.

## Window
New family (chart patterns). Variants this window: 15 of 40.

Script: `python -m forex.ea_research.brk_patterns --dry-run`, then `--run`.

## Amendments
1. (2026-10-16 ~18:05, after the dry run, before any P&L) **Zero-spread minutes.** The dry run's width/spread column
   showed values like 1.8e9: the MT5 M1 spread field is 0 on many minutes (EURUSD 35% of minutes 2022-26, AUDUSD 31%,
   NZDCHF 19%, USDJPY 15%, USDCAD 12%, USDCHF 9%, NZDCAD 6%, under 3.5% elsewhere), so ask = bid there and a stop filled on
   such a minute pays no spread. Rule: a minute with spread <= 0 gets the median of the market's non-zero minute spreads of
   the PREVIOUS calendar month (causal; the first month, 2021-12, uses itself and precedes all signals), and ask = bid +
   that spread. This changes costs only, never signals. Earlier rounds built on the same MT5 bars carry the same
   optimism (consistent with the ~0.03 R bar-vs-tick gap in `TICK_GAP_RESULT.md`). Crypto spreads are large but real
   (median 15-70 bp, p90 up to ~500 bp on SOLUSD) and are kept as registered.
