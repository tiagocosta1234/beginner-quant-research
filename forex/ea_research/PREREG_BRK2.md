# PREREG BRK2 - which session breakout, and does box tick-volume confirm it?

Registered 2026-10-16 ~16:00 local (local clock), before any P&L of these trials was computed.
the trader: "(original wording omitted)". The London 30-min ORB family closed in ORBX
(news and trend filters 0/3). This round tests the two things not yet tried: a different box (the Asian range) and
new MT5-native information (tick_volume, never used in any breakout test so far).

## Fixed trade rule (same for every box)
- First trigger in the entry window: buy stop at box high (fills when ASK reaches it) or sell stop at box low (fills
  when BID reaches it). SL = other side of the box, TP = 1 box beyond the entry (1:1). Exit at the session end if
  neither is hit. One trade per market per box per day. Same-minute TP+SL = SL; on the entry bar only the SL counts.
  Real bid/ask (MT5 broker M1), R = P&L / |entry - SL|.
- Boxes (server = local + 2 h; no decision in the server 23:00-01:00 rollover window):
  - ASIA: 01:00-07:00 local box, entries 07:00-11:00 local, exit 17:00 local.
  - LDN: 08:00-08:30 local box, entries 08:30-10:00, exit 17:00 local (the ORBX base rule).
  - NY: 09:30-10:00 New York box (DST-aware), entries to 12:30 New York, exit 15:55 New York.
- Universe: the 38 non-crypto MT5 broker.

## Relative box volume (RV)
RV = sum of M1 tick_volume inside the box / median of the same sum over the previous 20 trading days of that market
(causal: today's box is complete before any entry; the median uses earlier days only). Source
`data/ticks_vol/<SYM>.parquet` (MT5 copy_rates, to 2026-08-15). "High volume" = RV >= 1.5 (fixed a priori).

## Trials (4)
- **A**    ASIA box, all days (not yet seen in any test).
- **A_RV** ASIA box, RV >= 1.5.
- **L_RV** LDN box, RV >= 1.5 (the LDN base was seen in ORBX: -0.049R DEV).
- **N_RV** NY box, RV >= 1.5 (the NY base was seen in the 46-market screen).
Yardsticks (not trials): LDN and NY base.

## Periods
DEV 2022-01-01..2024-12-31 (selection), VAL 2025-01-01..2025-12-31, HOLD 2026-01-01..2026-08-15 (one look, only for
trials that pass DEV and VAL; the 2026 LDN/NY base is already seen, the RV-filtered subsets and the Asian box are not).

## Statistics and acceptance
- Net R per trade pooled over markets, t clustered by day.
- Placebo: 500 random same-size subsets of each trial's universe in DEV (per market); real mean must beat the 95th
  percentile. For A (no filter) the placebo is replaced by the requirement mean > 0.
- DEV: mean > 0, clustered t >= 2.5 (Bonferroni for 4 one-sided trials at 5% is z 2.24, rounded up), placebo, >= 300 trades.
- VAL: mean > 0, t >= 1.65, >= 100 trades. HOLD: mean > 0, t >= 1.65.
- A passer then needs the MT5 broker pass-speed gate before it is called usable.

## Honest prior
About 10%. Tick volume on a dealer feed measures quote updates, not traded size; it is correlated with volatility,
which the VR round already found useless for opening ranges. The Asian range is wide, so its spread cost per R is
small, which is the one structural advantage.

## Window
ORB family variants this window: about 18 + 4 = 22 of 40.

Script: `python -m forex.ea_research.brk2 --dry-run`, then `--run`.
