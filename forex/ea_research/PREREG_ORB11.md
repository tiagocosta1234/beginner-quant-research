# PREREG_ORB11 - the trader's 30-minute London / New York opening-range breakout with a 1:1 target, all 46 MT5 broker symbols (written 2026-10-15 16:03 local clock, before any P&L)

## the trader's rule (2026-10-15): "wait for the first 30 minutes of the London / New York session; if price touches the high, take a 1:1 long setup with the stop at the low, and the opposite if it touches the low first ... measure the return in R"
- Sessions, for EVERY symbol: LONDON box 08:00-08:30 Europe/London; NEW YORK box 09:30-10:00 America/New_York (the US cash open). Box = bid high / bid low of the 30 minutes (M1).
- After the box: the FIRST touch decides. Ask >= box high -> long at max(box high, that minute's ask open); bid <= box low -> short at min(box low, that minute's bid open). A minute that touches both sides is skipped (side unknown on M1). One trade per symbol per session per day.
- Stop at the other side of the box; R = |entry - stop|; target = entry +- 1R. Stop fills at the stop level or worse (the minute's open if it gapped through).
- Entry window: until the session end. Exit if neither stop nor target: London 17:00 London, New York 15:55 New York; never later than 22:55 server (standing rule: no decisions in server hours 23 / 0); a London box ending after... (all London / NY times map to server 10:00-22:55).
- Skip if R < 2 x the spread at the fill minute (as in the morning rounds).
- Costs: MT5 broker real bid/ask (longs fill at the ask and exit at the bid, shorts the reverse). Result in R per trade, net.
- Fill-minute rule: the M1 engine checks the stop / target from the fill minute itself (pessimistic: that minute's low may precede the fill) and, as a bound, from the next minute (optimistic). Both reported.
- Control: a random entry minute inside the same window, random side, the same R and 1:1 exit.

## Data, periods, tests
MT5 broker M1 bid/ask 2022-01..2026-10-02; DEV 2022-24, VAL 2025, 2026 already opened for the breakout family (reported, not clean). Real-tick replay on MT5 broker ticks 2025-10-01..2026-10-13 (300 ms latency) for every cell.
Cells: 46 symbols x 2 sessions = 92. A cell passes if DEV+VAL t (by day) >= 3.06 (one-sided 5% / 92), mean > 0 in DEV, VAL and 2026, and real ticks keep >= 75% of the M1 mean. Pooled LONDON / NY over all symbols: t >= 2.24.

## Overlap stated
BRK_EXITS (this morning) already had this exit (X1_t1R) for ONE session per market with a 3-hour entry window: London 08:00 box for FX / metals and NY 09:30 for US indices; its 1R target lost to the hold-to-close exit. This round adds the second session for every symbol and the full-session window, as the trader asked. Prior that a cell passes: about 5%.
