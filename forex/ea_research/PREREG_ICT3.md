# PREREG_ICT3 - the ICT concepts not yet tested, as complete strategies on every MT5 broker symbol (written 2026-10-15 local clock 18:24, before any P&L)
the trader: "(original wording omitted)". Searching "until one is found" guarantees a false positive, so this round is bounded: it is the LAST ICT round unless the trader supplies his own written model. Bars are corrected for this round plus ICT_GRID (33,120 cells, 3,575 pools in the family).

## Data, clocks, structure
As ICT_GRID: 46 MT5 broker symbols, MT5 broker M1 bid/ask 2021-12..2026-10-02, longs at the ask / shorts at the bid, M5 structure from mid prices (fractal swings known after the second right bar closes), New York killzones LKZ 02:00-05:00, NYAM 08:30-11:00, SB 10:00-11:00, NYPM 13:30-15:55; exits by 15:55 New York capped 22:55 server (nothing in server hours 23 / 0). New levels: midnight open MO = mid at the first minute at or after 00:00 New York; 20-day range = high / low of the 20 server days before today (01:00-22:55 bars); CBDR = the previous New York day's 14:00-20:00 range (>= 60 M5 bars), width W.

## Models (long side; shorts mirror). One trade per symbol x killzone x model x filter x day (first filled signal passing the filter); initial stop >= 2 spreads.
- JUDAS (LKZ, NYAM): the day's low since 00:00 NY is below MO and an M5 bar closes back above MO (previous close at or below) -> long at the next open; stop below the lowest bid since 00:00 NY.
- SBDOL (SB only): the first fair value gap formed 10:00-11:00 whose direction points to the draw on liquidity (the nearer of prior-day high / low measured from the 10:00 price) -> limit at the gap's near edge for 12 bars; stop beyond candle 1.
- OTE (LKZ, NYAM, SB, NYPM): sweep of the prior-day or Asian low (bar trades below, closes above), then within 12 bars an M5 close above the highest high of the 6 bars before the sweep (MSS); leg = sweep extreme -> highest high from the sweep to the MSS bar; limit at the 70.5% retracement of the leg for 12 bars; stop below the sweep extreme.
- BREAKER (same killzones): the same sweep + MSS; breaker = the last up-close M5 candle among the 6 before the sweep bar; limit at its high for 12 bars; stop below the sweep extreme.
- TURTLE (same killzones): an M5 bar trades below the 20-day low and closes back above it -> long at the next open; stop below the lowest bid since the killzone opened.
- CBDR (LKZ only): limit buy at CBDR low - 2W during the killzone; stop at CBDR low - 3W.

## Filters (3): NONE; MO (long only if the entry is below the midnight open, short only above: ICT discount / premium vs the daily open); DOL (long only if the prior-day high is nearer than the prior-day low from the entry).
## Targets (5): 1R, 2R, 3R, LIQ (prior-day high for JUDAS / SBDOL / OTE / BREAKER / TURTLE; CBDR midpoint for CBDR; skipped if < 0.5R away), TIME (15:55 New York).
JUDAS 2 x 3 x 5 = 30, SBDOL 15, OTE / BREAKER / TURTLE 3 x 4 x 3 x 5 = 180, CBDR 15: 240 rules x 46 symbols = 11,040 cells; pools rule x class: 1,200.

## Null, periods, tests
Matched random trade per rule trade (same day and killzone, random minute and side, same stop distance and target multiple). DEV 2022-24, VAL 2025, 2026 extra look.
1. Cell pass: DEV+VAL t >= 4.67 (one-sided 5% over 33,120 family cells), > 0 in DEV, VAL, 2026, above the null. 2. Pool pass: daily-mean t >= 4.19 (over 3,575 family pools), same conditions. 3. Walk-forward best of 240 per symbol on DEV -> VAL / 2026; luck ceiling from the null. 4. Out of time HistData 2020-21 at today's MT5 broker spread for every passer and for each class's DEV-best pool rule that is positive in both VAL and 2026 (gate t >= 1.96 / number of picks, both years positive). A survivor then needs MT5 broker real ticks and an MT5 broker-rules simulation before it is called a candidate.

## Honest prior
ICT_GRID: every model negative every year; the remaining concepts are variations on the same price patterns. Expected: 0 passes. If so, the ICT family is closed for mechanical rules.
