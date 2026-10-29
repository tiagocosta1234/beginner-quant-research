# PREREG_ORB11_ENTRY - can a different ENTRY fix the trader's 30-minute London / NY ORB? (written 2026-10-15 17:31 local clock, before any P&L; commit time = registration time)
the trader: "(original wording omitted)" (after ORB11_GRID showed the exits are not the problem: the breakout entry is only 0.02-0.04 R better than a random entry, less than the spread).

## Box, sessions, data (unchanged from ORB11)
30-minute box 08:00-08:30 London and 09:30-10:00 New York (local clocks), session end 17:00 London / 15:55 New York, capped 22:55 server. All 46 MT5 broker symbols, MT5 broker M1 bid/ask, 2021-12..2026-10-02. Longs fill at the ask, shorts at the bid; exits on the other side. No decision in server hours 23 or 0 (the 22:55 cap guarantees it). Trades with stop distance R < 2 spreads are skipped (as in ORB11).

## Entry triggers (6)
- T1 TOUCH: ORB11 baseline, first touch of the box high (ask) -> long, of the low (bid) -> short; stop at the opposite edge.
- T2 C5: first 5-minute bar (local-clock bins from the box end) whose mid close is outside the box; enter at the next minute's open; stop at the opposite edge.
- T3 C15: the same with 15-minute bars.
- T4 HOLD15: after the T1 touch, enter 15 minutes later only if the mid close of the 15th minute is still beyond the edge; stop at the opposite edge.
- T5 RETEST: after the T1 touch, a limit at the broken edge for 60 minutes (a buy limit fills when the ask low reaches it, at min(edge, ask open)); stop at the opposite edge.
- T6 FADE: after the T1 touch, the first minute whose mid close is back inside the box -> enter the OTHER way at the next open; stop at the breakout extreme so far (highest ask high for a failed upside break, lowest bid low for a downside one).

## Filters (6, all known when the box closes or at entry, from earlier data only)
- F0 none.
- F1 TREND: trade side agrees with sign(prior server-day mid close - its 20-day SMA of closes).
- F2 WIDE: box >= 40 median spreads (median ask-bid inside the box).
- F3 SQUEEZE: box / ATR20 of prior days' mid ranges is in the bottom third of this symbol-session's previous 60 boxes (at least 20 needed).
- F4 BOXDIR: trade side agrees with the box's own direction (mid at the box end vs at the box start).
- F5 TREND+WIDE.

## Exits (2)
- X1 the trader's 1:1: target 1R, stop R. X2 HOLD: stop R, no target, exit at the session end. Same-minute stop and target: stop first. Stops fill at the level or at the minute's open when it gapped through.

6 x 6 x 2 = 72 rules x 2 sessions x 46 symbols = 6,624 cells; pooled cells per rule x session x class (72 x 2 x 5 = 720) and rule x session (144).

## Null
One random entry per symbol-session-day (random minute after the box, random side, stop = box width, the same two exits). A rule is compared with the random entries on the days it traded.

## Periods and tests
DEV 2022-01..2024-12, VAL 2025, 2026-01..2026-10-02. 2026 is ALREADY OPEN for the breakout family (ORB_TREND_2026, ORB11, ORB11_GRID): a non-clean extra look only.
1. Pooled pass: DEV+VAL daily t >= 3.81 (one-sided 5% over 720 + 144), mean > 0 in DEV, VAL and 2026, and above the random entries on the same days.
2. Cell pass: DEV+VAL t >= 4.33 (one-sided 5% over 6,624), mean > 0 in DEV, VAL, 2026, above the random entries.
3. Walk-forward: per symbol-session and per session-class, choose the best of the 72 rules on DEV only; report its VAL and 2026 means and how many stay positive. The same search with each rule's trades replaced by the random entries on the same days (same exit) gives the luck ceiling for the highest t.
4. Anything that passes: real MT5 broker ticks (data/ticks, server clock) for 2025-10..2026-10 and a HistData 2020-21 out-of-time check before it is called a candidate.

## Honest prior
Today's rounds already tested retest (worse), failed-breakout reversals (random-like), volume, tick confirmation, trend (helps indices only, dies in 2026), wide box (necessary, not sufficient), squeeze, and a meta-labeling model (about 0). Expected: no passing cell or pool; this round is the consolidated answer on the trader's exact rule. The day's variant count is far above the 40-variant window; the Bonferroni bars above are the protection.
