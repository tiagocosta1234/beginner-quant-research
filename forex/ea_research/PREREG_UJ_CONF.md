# PREREG UJ_CONF - confluences for the USDJPY London-open breakout

Registered 2026-10-17 23:52 local (local clock, second PC PC-2), before any confluence split of these trades was computed.
the trader: "add more confluences to the USDJPY London breakout". Base = the registered rule (`usdjpy_sens.run(E, lc, 8, 30, 17)`:
08:00-08:30 London box, one-cancels-other stops until 11:00, stop at the other side, no target, exit 17:00 London) at TODAY's
cost (every minute's spread floored at 0.6 pip, variant C of `USDJPY_SPREADFIX_RESULT.md`): DEV 2022-24 +0.103 R (t 1.27),
VAL 2025 +0.108 R. The base results are seen; the confluence subsets are not.

## Confluences (9, fixed a priori; each a yes / no flag known at the fill)
- **C1 beyond Asia:** the broken box level is also beyond the Asian session extreme (00:00-07:00 London high for a long / low
  for a short). [a break that also clears the night's range]
- **C2 20-day trend:** side x (yesterday's close - SMA20 of daily closes) > 0.
- **C3 risk-on alignment:** NSDQ's move from 01:00 server to 08:00 London has the sign of the trade (long USDJPY with risk-on).
- **C4 USD-wide alignment:** minus the mean of EURUSD's and GBPUSD's moves from 00:00 to 08:30 London has the sign of the trade.
- **C5 FVG:** an unmitigated 5-min FVG in the break direction inside the box (`PREREG_BRK_FVG.md` definition, through the
  minute before the fill).
- **C6 not a small box:** box / ATR20 >= the 33rd percentile of the DEV events (cut fitted on DEV only).
- **C7 late trigger:** the fill is more than 8 minutes after 08:30 (LDN3F filter F2; NOTE: chosen from a 2022-26 descriptive
  look across markets, so not clean for USDJPY).
- **C8 not stretched:** side x 5-day change / ATR20 < 0.59 (LDN3F F3; same caveat).
- **C9 Asia move aligned:** side x (mid at 08:00 London - mid at 00:00 London) > 0.

## Selection (DEV 2022-24), confirmation (VAL 2025), hold-out (2026)
- Kept if on DEV: R(with) > 0, R(with) > R(without) with Welch t >= 2.0, n(with) >= 150.
- Combined rule = base AND all kept. VAL: mean > 0 with t >= 1.65 and above the base VAL. If it passes: one look at 2026
  (mean > 0, t >= 1.65); then the account view decides (USDJPY at $150 and $250 a trade from 95,472, MT5 broker rules, with and
  without a 0.06 R real-tick haircut: P(pass) > P(breach) by 30 Jun 2027), and the decisive 2020-21 HistData check on the main PC.
- The account view of the combined rule (or the base) is printed in any case.

## Honest prior
About 10%. 9 splits of ~760 trades; the base itself is t 1.3 at today's cost and about zero on real ticks last year.

## Amendments
(none yet)
