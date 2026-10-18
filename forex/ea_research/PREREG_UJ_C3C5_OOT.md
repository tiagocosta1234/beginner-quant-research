# PREREG UJ_C3C5_OOT - USDJPY London breakout + risk-on alignment / + FVG, unchanged, on data never used for them

Registered 2026-10-17 23:56 local (local clock, second PC PC-2; header first said 23:58, a guess, corrected after the run), before any 2026 or 2020-21 subset of these rules was computed.
the trader: "pre-registered test of 'USDJPY breakout + risk-on alignment' and '+ FVG', unchanged, on data they've never seen".
Origin: `UJ_CONF_RESULT.md` (not kept by its own rule, DEV t 1.63 / 1.44; both repeated in VAL 2025 at similar size).

## The two rules (definitions copied unchanged from `uj_conf.py`, frozen 23:53:02)
Base: USDJPY London-open breakout (`usdjpy_sens.run(E, lc, 8, 30, 17)`: 08:00-08:30 London box, one-cancels-other stops until
11:00, stop at the other side of the box, no target, exit 17:00 London), every minute's spread floored at 0.6 pip.
- **UJ+C3 risk-on:** base trades where NSDQ's mid move from 01:00 server to 08:00 London has the sign of the trade.
- **UJ+C5 FVG:** base trades with an unmitigated 5-min mid FVG in the break direction inside the box (formed since 00:00
  local, height >= the box's median spread, untouched through the minute before the fill).

## Part A - the 2026 hold-out (run now, on the second PC): 2026-01-01..2026-10-16
- The base's 2026 result is already known (+0.111 R at the 0.6-pip floor, `USDJPY_SPREADFIX_RESULT.md`); the 2026 subsets of
  C3 and C5 have never been computed. This spends the 2026 hold-out on two rules that did not formally pass development:
  the trader's explicit decision.
- Pass, per rule: mean net R > 0 with day-clustered t >= 1.96 (Bonferroni for 2 one-sided tests at 5%), and the rule's 2026 mean
  above that of the base trades without the flag.
- Expected power is low (about 100 and 70 trades): an effect of the DEV / VAL size (+0.25 R a trade, SD ~1.5 R) gives t ~1.7 /
  1.4 on average, so "not significant" is the likely outcome even if the effect is real.

## Part B - 2020-21 HistData (run on the main PC, where the files are)
- Same definitions on HistData USDJPY M1 (bid/ask, ask floored at the 0.6-pip MT5 broker spread) for 2020-01-02..2021-11-30 and
  HistData NSXUSD for the C3 sign; FVGs from HistData USDJPY 5-min mid candles.
- Pass, per rule: mean net R > 0 with t >= 1.96 and above the base trades without the flag.

## Verdict rule
A rule is called "confirmed" only if it passes BOTH parts. Then, and only then, the account environment decides usability:
USDJPY at $150 and $250 a trade from the live balance (last known 95,472.14), MT5 broker rules, with and without a 0.06 R real-tick
haircut; usable only if P(pass) > P(breach) by 30 Jun 2027. The account view (2022-26 trades, labelled in-sample) is printed now
for information.

## Amendments
(none yet)
