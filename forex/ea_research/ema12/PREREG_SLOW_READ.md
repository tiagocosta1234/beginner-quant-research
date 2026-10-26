# PREREG_SLOW_READ: does the trader's London-open read have an edge when played at a deliberate pace?

Written Mon 2026-10-26 late evening (local clock), BEFORE any trade of this test exists. Context: Read v2 (40 days), the recent-2026 block
(41 days) and the Claude-filter block (40 days) were all ~41-45% wins and NOT SUPPORTED, but every one of them was played at 30-50 seconds a
day, so they measured snap decisions, not a careful read. the trader: "this cant be the end of it, there's people out there doing this for months" /
"why dont you wanna be the 1%?" -> Claude proposed this finite test with an end date; this file fixes it before play.

## Days
`BLIND_SLOW_2024_25.csv`: 100 weekdays drawn with numpy default_rng(202610264) from the 261 weekdays of 2024-2025 with full GC 1m data
07:00-08:14 that appear in none of the trader's replay / blind / practice / live logs (41 files listed by the draw, plus his first sample
2025-04-14..05-12). 66 from 2024, 34 from 2025. Played in calendar order, no skipping, no going back.

## Rules (the MGC Blind Replay app enforces all of them)
1. Read v2 rules unchanged: bias before the first step, minimum stop 5 x noise, target 1.0-1.5 R, no chase (> 3 x noise your way in the last
   5 minutes), one-minute steps 07:59-08:14, market entry only while the last visible candle is 07:59-08:14, at most one trade.
2. **Pace lock (new):** on a scored day no trade, no "no trade" and no step past 08:14 is accepted until **180 seconds** (PC wall clock) after
   the day was started. The decision time of each day is written to the audit trail (`replay_events.jsonl`, field `secs`).
3. The result of each trade is shown after it closes (as in Read v2). the trader may stop and resume between days at any time.

## Scoring (single look, after all 100 days are logged): `score_slow.py`, hashed with this file
Each trade replayed on GC futures with the app convention; mirror = same fill minute and distances on the other side; random-side P from
20,000 random own / mirror assignments.

## Bar
**SUPPORTED iff mean R > 0 AND random-side P <= 0.05.** Fewer than 40 trades = INCONCLUSIVE. Nothing is scored or looked at before day 100.
- SUPPORTED: one account account may be bought, traded live only under these same rules and pace, every call logged before entry.
- NOT SUPPORTED: no account purchases for the London 1-minute read; the question is closed.
Reported as well: wins, mean R, mirror mean, first-half vs second-half mean R, median decision time.

Target end date: about Tue 3 Nov 2026 (about 45 minutes a day for a week).

## Amendment 1 (Mon 2026-10-26 ~21:55 local clock, BEFORE any day of this test was played: no BLIND_LOG_SLOW.csv, no 2024 event)
the trader: "it needs to be done today, im buying an eval tomorrow right before london session". 100 paced days cannot be played in one night
(>= 5 hours), so a ONE-NIGHT SCREEN is added for tomorrow's purchase decision only; the 100-day test, its bar and its single final verdict
are unchanged (the screen is disclosed as an interim look; it never ends the test early).
- **Screen = the first 40 scheduled days (2024-01-04 .. 2024-04-25), played tonight with the same rules and the 3-minute pace lock.**
- **GO iff at least 20 trades AND mean R >= +0.20 (about 60% wins at 1:1) AND the 40th day is logged before 01:00 (local clock).** Otherwise NO-GO:
  no eval is bought tomorrow on this read (Claude's advice; the money and the decision are the trader's). Scored by `screen_slow.py` (own side only,
  same futures convention as `score_slow.py`). With no skill the GO rule is passed by chance about 1 time in 10 (n 20-35, sd ~1 R).
- GO is not proof: it only says the read cleared a bar that a no-skill player rarely clears in one night.
