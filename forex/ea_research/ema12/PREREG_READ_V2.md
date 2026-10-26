# PREREG_READ_V2: the trader's London read with the v2 rules, on 40 unseen 2025 days + live

Written Mon 2026-10-26 evening (local clock), after the Look 2 verdict of PREREG_BLIND2026 (NOT SUPPORTED, P 0.257) and BEFORE any v2 trade
exists. the trader: "maybe you could help me upgrade my trading to increase the win rate" -> forensics of his 88 blind trades
(`trade_forensics.py`, `forensics_check.py`, post-hoc) -> the trader chose "every v2 rule and you backtest it" and "40 random 2025 days + live".

## Where the rules come from (post-hoc, hence this fresh test)
- Stops under 3x the pre-entry noise: 37% wins, -0.21 R; 5-8x: 68% wins, +0.36 R. What-if minimum stop 5x noise with a 1:1 target on his
  88 trades: +0.109 R (mirror -0.132), P 0.14 (in-sample, the multiple was chosen after looking).
- Targets above 1.7 R won 18%; 1.2-1.7 R did best. Chasing (> 3x noise in the last 5 minutes): 1 win in 4.
- "Target reached later after the stop" is NOT evidence of direction skill (his side 64%, mirror 61%).

## The v2 rules (enforced by the MGC Blind Replay app; GC futures 1m, local clock)
1. **Noise** = median (high - low) of the 1-minute bars 07:00-07:59 of the day (known at 07:59). **Minimum stop distance = 5 x noise.**
2. **Target between 1.0 R and 1.5 R** of his stop distance.
3. **No chase:** an entry is refused if price moved in the trade's direction by more than 3 x noise over the last 5 minutes
   (close of the last visible candle minus the close 5 minutes earlier).
4. **One minute at a time** while the last visible candle is 07:59-08:13 (no +5 / +15 jumps in the entry window).
5. Unchanged from PREREG_BLIND2026: bias at 07:59 before any step; one market entry while the last visible candle is 07:59-08:14
   (fill at the next minute's open, one tick worse); stop and target never moved; 08:15 without a trade = no-trade day; calendar order,
   no skip, no rewind; the trade is logged before the next bar is served.

## Days
40 weekdays drawn now from 2025 with numpy default_rng(202610262) from the 214 days with full GC data 07:00-08:14, excluding his first
replay sample (2025-04-14..2025-05-12) and the 2025 practice days he has seen (04-17, 06-16, 08-20). List `BLIND_V2_2025.csv`
(sha256 7a3deeba934f3e7626adfb8fb730028d653b71cb991af3bf932082d567861ae1), played in calendar order. Leak note: 2025 precedes 2026
prices he has replayed (he knows the year's big picture); this cannot shape a 1-minute London-open call much, but it is a limit.
Practice (unscored) moves to 2026-01-02..2026-07-24, a period he has already replayed, so practice adds no new leak.

## Scoring (single look after the 40 days; primary)
GC futures, the app convention: fill at the next minute's open one tick worse; stop exit one tick worse; target at its price; stop and
target in the same minute = stop; open at 17:00 = closed at that minute's close. R = signed (exit - fill) / stop distance.
Random-side P: 20,000 sign flips of each trade to its mirror (same distances, other side; the mirror pays -R minus two ticks in R).
**Read v2 supported iff mean R >= +0.10 AND random-side P <= 0.05.** n = 40 days (no-trade days count as 0 trades; trades only are scored).
Power is limited at this n: a true +0.15 R passes roughly half the time. "Not supported" = not shown, not "no skill".

## Live (secondary)
London calls on BrokerAPI Practice under the same v2 rules, logged before entry (DEMO log); scored with the same convention, reported
separately, never pooled into the verdict above.

## Descriptive backtests (never change the verdict)
(a) v2 applied to his 88 past blind trades (in-sample what-if). (b) v2 brackets on 2019-2026 GC with mechanical sides (the indicator's
candle colour, the 15m EMA12 bias, a random side): shows what the bracket rules do with no skill at all.

## RESULT (single look, scored Mon 2026-10-26 20:38 local clock)
Plan hash at scoring: sha256 f58d617f2ea87712421294ac1b86a5f84799c0fc4b31a307b5de8e248ee93555 (unchanged since 19:30). The 40 days were played in the app 20:05-20:37 (median under a minute a day).
**34 trades, 6 no-trade days: 14 wins (41%), mean R -0.047, sum -1.61 R, random-side P 0.558 (about -$2,220 at $750 risk). Bar: mean R >= +0.10
and P <= 0.05 -> NOT SUPPORTED.** Side = 07:59 bias on 25 trades (10 wins), against it 9 (4 wins). Median stop 5.8 pt (v2 floor applied), median target 1.49 R.
