# PREREG R16_CONF - confluences for reel 16's NY-box breakout (trader 1) on NSDQ

Registered 2026-10-17 23:49 local (local clock, second PC PC-2), before any confluence split of these trades was computed.
the trader: "add more confluences to reel 16". Base rule = R16-T1 of `PREREG_REELS_16_17.md` (box 09:30-10:00 New York, first 5-min
mid close outside the box until 12:00 NY, market entry at the next minute, stop at the other side of the box, target 1 R,
exit 16:00 NY), MT5 broker NSDQ: DEV +0.067 R (t 2.09), VAL +0.024 (t 0.44). Both base results are already seen; the confluence
subsets are not. Trader 2 (retest) is reported descriptively under the same filters.

## Confluences (8, fixed a priori; each a yes / no flag known at the signal candle's close)
- **C1 FVG:** an unmitigated 5-min FVG in the break direction lies inside the box (definition of `PREREG_BRK_FVG.md`: formed
  since 00:00 local, before the signal close, height >= the box's median spread, untouched since). [BRK_FVG: +0.03-0.04 R on follows]
- **C2 20-day trend:** side x (yesterday's close - SMA20 of daily closes) > 0. [the card's Nasdaq-with-the-trend leg]
- **C3 not a small box:** box / ATR20 >= the 33rd percentile of the DEV events (cut fitted on DEV only). [small boxes lose]
- **C4 gap alignment:** side x (mid at 09:30 NY - yesterday's close) > 0. [gap and go]
- **C5 strong signal candle:** the signal 5-min candle closes in its outer 25% in the break direction.
- **C6 above / below the session TWAP:** side x (signal close - time-weighted mean of minute mids since 09:30 NY) > 0.
- **C7 S&P confirms:** at the signal close, SP's mid is outside its own 09:30-10:00 NY box on the same side.
- **C8 volatility expanding:** ATR20 / ATR100 (daily ranges of completed days) > 1.

## Selection (DEV 2022-24) and confirmation (VAL 2025)
- A confluence is kept if on DEV: R(with) > 0, R(with) > R(without) with Welch t >= 2.0, n(with) >= 150.
- The combined rule = base AND every kept confluence. It must then show on VAL: mean > 0 with day-clustered t >= 1.65 and above
  the base on VAL. If it does: one look at HOLD 2026 (mean > 0, t >= 1.65), and the account view (NSDQ, $250 a trade, from
  95,472, MT5 broker rules) decides usability (P(pass) > P(breach) by 30 Jun 2027). If no confluence is kept, the round ends there.
- The account view of the combined rule (or the base, if nothing is kept) is printed in any case, labelled with its period.

## Honest prior
About 10%. Earlier filters on these boxes (trend, box size, FVG, partner index, volatility) moved results by 0.02-0.10 R and
none survived an out-of-time test; the subsets here are 25-75% of ~730 DEV trades.

## Amendments
1. (2026-10-17 23:50, first run crashed before any selection output was complete) Engine fix only: the Welch t returns
   'not computable' when a group is empty. C6 (TWAP side) turned out to be true on every event (a close outside the box is
   always beyond the session TWAP), so it cannot be kept; no rule change.
