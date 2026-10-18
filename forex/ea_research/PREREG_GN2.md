# PREREG GN2 - gold and Nasdaq breakouts after a pullback (pullback-in-uptrend and dip confirmation)

Registered 2026-10-18 10:55 local (local clock, second PC PC-2), before any P&L of these trials was computed.
the trader: "keep working on getting profitable in gold and nasdaq breakout". GN1 (`GN1_RESULT.md`) showed that long breakouts in
the 200-day uptrend earn what a random long earns on the same days. The two working legs on these markets buy weakness, not
strength: XAU5 is a gold trend-pullback follower, ManualDip buys index dips (z3 <= -1.5). This round asks whether a breakout the
day AFTER a pullback (the market turns back up through the morning box) is better than (a) a random long on the same days and
(b) the GN1 breakout on all uptrend days. The subsets below were never computed; the GN1 bases they come from are seen.

## Markets, data, costs
XAUUSD and NSDQ, MT5 broker M1 bid/ask 2021-12..2026-10-16, zero-spread minutes repaired (`brk_patterns.load`), engine of `gn1.py`
(same boxes, entry window, buy stop filled at the ask, stop at the box low, exit, rollover-window exclusion, fill-minute rule).
Daily closes as in GN1: gold 17:00 London mid, NSDQ 16:00 New York mid. sd = 60-day SD of daily close returns;
z1 = r1 / sd, z3 = log(C / C[-3]) / (sd sqrt 3), all known at the previous day's close.

## Trials (6) - each is a long breakout on the day after the condition, exit at the same day's session end
| trial | market | condition at the previous close | session (box, window, exit) |
|---|---|---|---|
| P1 | XAUUSD | above SMA200 and r1 < 0 (a down day in the uptrend) | London: 08:00-08:30, to 11:00, exit 17:00 |
| P2 | NSDQ | above SMA200 and r1 < 0 | New York: 09:30-10:00, to 12:00, exit 15:55 |
| P3 | XAUUSD | above SMA200 and z3 <= -1.0 (a 3-day pullback in the uptrend) | London |
| P4 | NSDQ | above SMA200 and z3 <= -1.0 | New York |
| P5 | XAUUSD | z3 <= -1.5, any regime (the ManualDip signal on gold) | London |
| P6 | NSDQ | z3 <= -1.5, any regime (ManualDip's signal; NSDQ's own close) | New York |

## Control (decides together with the mean)
On every condition day (breakout fired or not): 5 random longs at uniformly random minutes of the same entry window, at the
ask, stop distance = that day's box width, same exit (the GN1 control restricted to the condition days). Information =
mean R of the breakout trades - mean R of ALL the condition-day controls (unconditional; GN1's day-paired version was biased,
see `GN1_RESULT.md`); its standard error treats the two means as independent (conservative: they are positively correlated).

## Periods
DEV 2022..2024 (the regime trials start about 2022-10 because SMA200 needs 200 closes), VAL 2025, HOLD 2026-01-01..2026-10-16
(one look, only for trials passing DEV and VAL).

## Acceptance
- DEV: n >= 60; mean net R > 0 with day-clustered t >= 2.39 (Bonferroni, 6 one-sided trials at 5%); information > 0 with
  t >= 1.65; information over the GN1 base on the same market and session (all uptrend days) > 0; positive in >= 2 DEV years
  that have >= 15 trades.
- VAL: mean > 0, information > 0, t >= 1.65 on the mean. HOLD: mean > 0, t >= 1.65.
- Account environment (standing rule): every trial is replayed from 95,472 (MT5 broker rules, `usdjpy_account_env.account`, 5-day block
  bootstrap of 2022-25 days) at $250 and $500 a trade; usable only if P(pass) > P(breach) by 30 Jun 2027.

## Dry run (no P&L)
Counts per trial and period, condition frequency, truncation test, hand check of 2 trades per trial.

## Honest prior
About 10%. Pullback conditioning helped the dip legs because they buy the close of the weak day; requiring a breakout the next
morning keeps only the days that already turned up, which may have spent the rebound. The dip trials (P5, P6) will have small
samples (about 15-25 signals a year, about half with a fill), so only a large effect could pass.

## Running count
GN1 5 + GN2 6 = 11 of 40 variants in this research window (9 after amendment 1).

## Amendments
1. (2026-10-18 10:58, after the dry run, before any P&L) The dry run counts P3 44, P4 35, P5 31, P6 28 DEV trades, so none of
   them can meet the n >= 60 bar alone. P3 + P4 are pooled into **P34** (3-day pullback in the uptrend, gold London + Nasdaq
   New York) and P5 + P6 into **P56** (dip z3 <= -1.5, gold + Nasdaq); the day-clustered t combines both markets' trades of
   the same day; the information and the "vs GN1 base" bars use the pooled control and the pooled base (G1 + N1). Trials are
   now P1, P2, P34, P56: Bonferroni bar for 4 one-sided trials t >= 2.24. The n >= 60 bar is kept: P56 has 59 DEV trades, so
   it can only fail or be reported descriptively; the bar is not lowered to fit it. The per-market lines are printed as
   descriptive rows.
