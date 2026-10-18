# PREREG BRK_FVG - an unmitigated fair value gap between entry and stop as a confluence for box breaks and bounces

Registered 2026-10-16 20:28 local (local clock, second PC PC-2), before any P&L of these trials was computed.
the trader: "add a confluence of having to exist an unmitigated fair value gap between the entry and the stop loss". FVGs were
tested before only as ENTRIES (ICT grid / ICT3: limit orders at the gap, every model negative in every year). An FVG used as
a filter that "protects" the stop of a box trade has not been tested.

## Events and trades (identical to BRK_TWOWAY, `brk_twoway.py`, cache `C:\work\scratch\brk_twoway_events.parquet`)
First touch of the London (08:00-08:30 local) or New York (09:30-10:00 NY) 30-min box high / low, 38 non-crypto MT5 broker,
2022-01..2026-10-16; decision at the close of the touch minute, entry at the next minute's open, symmetric bracket of one box
width W (stop and target W from the entry), exit at the session end. FOLLOW = trade in the touch direction; FADE = the
opposite. Net R of both legs is already in the cache (computed with real bid/ask, zero-spread minutes repaired).

## The confluence (fixed a priori)
- FVGs on 5-minute MID candles on the server-clock 5-min grid. Bullish FVG at candles (c-2, c-1, c): low[c] > high[c-2],
  gap = [high[c-2], low[c]]. Bearish: high[c] < low[c-2], gap = [high[c], low[c-2]]. An FVG exists from the close of candle c.
- Only FVGs formed today: candle c closes at or after 00:00 local and no later than the start of the touch minute.
- Minimum size: gap height >= the median spread of the box (W / box_spread).
- Unmitigated: from the FVG's formation to the end of the touch minute, no M1 mid low below the top of a bullish gap / no M1 mid
  high above the bottom of a bearish gap (price never traded into the gap).
- FOLLOW confluence: an unmitigated FVG in the touch direction lying entirely between the stop and the level, i.e. inside
  [box low, box high] (bullish for an up-touch, bearish for a down-touch).
- FADE confluence: an unmitigated FVG in the fade direction lying entirely between the level and the fade stop, i.e. inside
  [box high, box high + W] for an up-touch (bearish) / [box low - W, box low] for a down-touch (bullish).

## Trials (4)
LDN-FOLLOW-FVG, LDN-FADE-FVG, NY-FOLLOW-FVG, NY-FADE-FVG: the leg is traded only on events with its confluence.
Yardsticks (not trials): the same leg on all events, and on the events without the confluence.

## Periods
DEV 2022-01-01..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-10-16 (one look, only for a trial passing DEV and VAL).

## Acceptance
- DEV: n >= 300; mean net R > 0 with day-clustered t >= 2.5 (Bonferroni, 4 trials); mean above the same leg on the events
  WITHOUT the confluence, difference t >= 2.0 (Welch, trade level); positive in >= 2 of the 3 DEV years.
- VAL: mean > 0, t >= 1.65. HOLD: mean > 0, t >= 1.65.
- Account environment (standing rule): for a full passer, NSDQ + XAUUSD at $250 a trade from 95,472 (MT5 broker rules,
  `usdjpy_account_env.account`), usable only if P(pass) > P(breach) by 30 Jun 2027; the account view is printed for every trial.

## Descriptive
Share of events with each confluence; win rate (target first) and R with / without; by class and year; how many FVGs were
mitigated before the touch (the "unmitigated" condition's bite).

## Dry run (no P&L)
`python -m forex.ea_research.brk_fvg --dry-run`: counts of events with each confluence by box and period; truncation test of the
flags (cut the data at random times on 3 markets: flags and FVG coordinates before the cut day identical); hand check of 3
flagged events with the gap printed.

## Honest prior
About 5%. FVGs are a price-only pattern; BRK_TWOWAY found direction unpredictable from 22 price features (AUC 0.51-0.53), and
the ICT rounds found FVG entries negative everywhere.

## Window
FVG-confluence family: 4 of 40 variants.

## Amendments
(none yet)
