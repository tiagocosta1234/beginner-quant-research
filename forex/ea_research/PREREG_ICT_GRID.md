# PREREG_ICT_GRID - every combination of the core ICT concepts on every MT5 broker symbol (written 2026-10-15 local clock 18:15, before any P&L)
the trader: "(original wording omitted)" (after "(original wording omitted)").
Earlier ICT rounds (ICT_SCAN 0/154, ICT2 SMT / 2022 model / NWOG, CRT, CRTF, OTE, ORB11_ICTSTOP) found no edge; this round composes the concepts into complete strategies.

## Data and clocks
46 MT5 broker symbols, MT5 broker M1 bid/ask 2021-12..2026-10-02; longs at the ask, shorts at the bid. Structure on M5 bars (server clock) from mid prices; swings are 2-left / 2-right fractals known only after the second right bar has closed. Trading day = server day (starts 17:00 New York). Prior-day open / high / low / close / midpoint from server-day bars 01:00-22:55. Asian range = New York 19:00-24:00 of the previous evening (>= 30 M5 bars). Killzones in New York time: LKZ 02:00-05:00, NYAM 08:30-11:00, SB (silver bullet) 10:00-11:00, NYPM 13:30-15:55. Every trade exits at the latest at 15:55 New York, capped 22:55 server: no decision in server hours 23 or 0.

## Entry models (a signal is evaluated at an M5 close inside the killzone; market entries fill at the next minute's open)
- SWEEP_PD / SWEEP_AS: an M5 bar trades beyond the prior-day low (high) or the Asian low (high) and closes back inside -> long (short) at the next open; stop beyond the sweep extreme (lowest bid / highest ask since the killzone opened).
- MSS_PD / MSS_AS: after such a sweep, within 12 bars, an M5 close beyond the highest high (lowest low) of the 6 bars before the sweep bar (market structure shift) -> market entry; stop beyond the sweep extreme.
- MSSFVG_PD / MSSFVG_AS: the MSS leg's latest fair value gap (bar c low above bar c-2 high, c between the sweep and the MSS bar) -> limit at the gap's near edge for 12 bars (buy limit fills when the ask low reaches it); stop beyond the sweep extreme known when the order is placed.
- FVG: any fair value gap formed inside the killzone -> limit at its near edge in the gap's direction for 12 bars; stop beyond candle 1 (bid low / ask high of bar c-2).
- OB: break of structure (first M5 close beyond the last confirmed swing high / low of the previous 24 bars) -> limit at the order block (the last opposite-colour M5 candle among the 6 before the break: its high for a long) for 12 bars; stop beyond the order block.
One trade per symbol x killzone x model x bias x day: the first signal that fills and satisfies the bias. Initial stop >= 2 spreads.

## Bias (3)
NONE; DAILY (side = direction of the prior server day, close vs open); PD (premium / discount: longs only below the prior-day midpoint, shorts only above).

## Targets (5)
1R, 2R, 3R, LIQ (opposite liquidity: prior-day high / low for PD-based, FVG and OB models; Asian high / low for AS models; skipped when it is less than 0.5R away), TIME (15:55 New York). Stops fill at the level or the minute's open if gapped; same-minute stop and target: stop first.

8 models x 4 killzones x 3 biases x 5 targets = 480 rules x 46 symbols = 22,080 cells; pools rule x class (5 classes) = 2,400.

## Null
Every rule trade gets a matched random trade: same day and killzone, random minute inside the killzone, random side, the same stop distance and target multiple.

## Periods and tests
DEV 2022-24, VAL 2025, 2026-01..10-02 (an extra look; earlier ICT rounds used DEV / VAL only).
1. Cell pass: DEV+VAL t >= 4.59 (one-sided 5% over 22,080), mean > 0 in DEV, VAL and 2026, above the matched null.
2. Pool pass (rule x class, daily-mean t): t >= 4.07 (over 2,400), same conditions.
3. Walk-forward: best of 480 per symbol on DEV -> VAL / 2026; luck ceiling = the same search on the matched null.
4. Out of time (HistData 2020-21, today's MT5 broker spread): every passer, plus the best rule per class chosen on DEV if it is positive in both VAL and 2026; gate t >= 1.96 / number of such picks (Bonferroni) and both years positive.

## Honest prior
Every earlier ICT test on these markets was negative; a sweep / FVG / OB entry is a pattern on price alone, which the 2026-10-10 confluence panels showed carries almost no information after costs. Expected: 0 passes; the walk-forward picks lose out of sample.
