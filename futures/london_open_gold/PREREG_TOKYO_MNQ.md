# PREREG_TOKYO_MNQ: is there a mechanical edge in the Tokyo session on NQ (MNQ stand-in)?

Written Tue 2026-10-27 ~21:4x (local clock) BEFORE running anything below. the trader asked for "a really good Tokyo indicator for MNQ". Base rate stated first:
the most likely result is NO edge after costs (every other session and rule family tested so far came back negative). Not for use as a trade tonight
whatever the result (a single look is a lead, not a validated rule).

## Data and session
`futures/data/databento/futures_NQ.F_1m.parquet` (NQ front month, 1m, UTC, 2019-10 .. latest). Tokyo session = 00:00-06:00 UTC
(09:00-15:00 JST, no DST). Trades flat at 06:00 UTC at the latest.

## Three frozen hypotheses (nothing else is searched)
- **H1 follow**: first 15m candle (00:00-00:14) direction; enter at the open of the 00:15 bar in that direction; stop = the opposite extreme of the candle; target 1R.
- **H2 fade**: same candle; enter the opposite direction; stop = the candle's extreme on the side of its direction; target 1R.
- **H3 breakout**: range of 00:00-00:29; enter at the close of the first 1m bar after 00:30 that closes beyond the range, in that direction; stop = the opposite end of the range; target 1R.
Skip a day if the stop distance S < 8 NQ points, if the candle is a doji (H1/H2), or if bars are missing. Ties (stop and target in the same 1m bar) = stop.
Costs: 0.86 NQ points per round trip (MNQ all-in fee + 1 tick slippage, same constant as `london_open_indicator.pine`), net R = gross R - 0.86 / S. Unfilled / missing bars: skip.

## Scoring (single look)
DEV = 2019-10 .. 2022-12 (descriptive only; nothing is tuned: no free parameters). TEST = 2023-01-01 .. latest, scored once.
Bar for a "lead": on TEST, n >= 150 AND mean net R > 0 AND one-sided bootstrap P(mean <= 0) <= 0.0167 (0.05 / 3 hypotheses). For H1 / H2 also report the random-side
P (coin-flip side each day, 5,000 draws). Also report the share of positive years. If the bar is not met: "NOT SHOWN: no Tokyo edge in this form", closed.
If it is met: it is a lead that needs a new pre-registered forward paper test; it is NOT a live rule.

## Not allowed
Re-tuning, adding variants after the look, using the TEST result to change S, costs or hours.

## RESULT (single TEST look, Tue 2026-10-27 21:4x local clock; `tokyo_mnq.py` -> TOKYO_MNQ_OUTPUT.txt; the .sha256 covers the text above this line)
TEST 2023-01 .. 2026-09 (965 days): H1 follow n 750, mean net R -0.051, boot P 0.92, random-side P 0.43; H2 fade n 305, -0.009, P 0.56; H3 breakout n 937, -0.021, P 0.77.
DEV: H1 -0.008, H2 -0.079, H3 -0.004. Bar (mean > 0 AND P <= 0.0167): none met. **NOT SHOWN: no Tokyo edge in these three forms on NQ. Closed; no re-tuning.**
