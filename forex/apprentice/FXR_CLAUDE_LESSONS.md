# Claude's forced 08:00 calls on FX Replay: lessons and rule versions

Each lesson comes from a logged call (FXR_CLAUDE_TRADES.csv). A rule change applies only from the NEXT call, so the logged calls stay comparable by version.

## v1 (11-17 Mar 2026 replay days): 2 wins / 3 losses, -1R
- Side from the 1h structure; entry at market at 08:00; stop beyond the nearest swing + 0.3 x ATR15; target 1:1.

## Lessons
1. **Stops on or near a level get wicked.** 10 Mar (the trader's own) and 17 Mar (by 0.08 pt under 5000): the wick tags the level, then reverses.
2. **When the 1h and the 15m disagree, the 1h won.** 12 Mar: the 15m higher high ran straight into the 1h lower high at 5184-5191, and the trade lost.
3. **A big level between entry and target stops the move.** 13 Mar: price bounced at the 5062 double bottom, 3 pt before the target. 16 Mar: the target sat in front of 4970 and hit.
4. **A sharp rejection from the high just before 08:00 is a warning.** 17 Mar: "up-ish" after the 06:00 drop from 5045 never got going.

## v2 (from the next call)
- **Stop:** beyond the swing + **0.5 x ATR15**, and never within 1 pt of a round number (x000, x050) on the stop side. Same $ risk, so a smaller size.
- **Side:** when the 1h and 15m disagree, take the 1h side and say "low conviction".
- **Target (1:1):** if a major level (prior day / overnight high-low, double top-bottom) sits between entry and target, say so and grade the trade "B"; grade "A" only with a clean path.
- **Grade every call A / B / C**, so we can check later whether A calls do better (too few trades so far to know).

Caveat: 5 calls is a tiny sample. Some of these "lessons" may be noise. The grades are there to find out.

## Session cce14cd5 closed (FX Replay day limit), stats read 24 Oct 2026
- FX Replay totals: 20 trades, 8 W / 12 L (40%), -$1,876.49 (-3.75%), profit factor 0.68, expectancy -$93.82, max losing streak 7.
- **the trader's own calls (25 Feb - 10 Mar, plus 23 Mar):** 4 W / 7 L, -3R. The pre-filter losses were mostly against or mixed 1h structure.
- **Claude's calls (11 - 24 Mar), as called:** 5 W / 5 L, 0R. v1 2/3, v2 3/2. Executed: 4 W / 5 L (11 Mar was placed reversed).
- **Batch-2 days, the trader's own levels:** 25 Feb +1, 2 Mar -1, 4 Mar +1, 23 Mar +1 = **+2R from 4**. His side calls with Claude's levels: 17 and 20 Mar, both lost.
- Read: 20 trades at 1:1 needs a win rate above about 50% to pay. Nothing here is significant yet. The two leads worth testing on: (1) trade only with a clear 1h structure or a capitulation reversal; (2) the trader's own read on blind days.

## v3 (from the 1 Apr 2026 replay day; the trader: "sure" to switching on 24 Oct 2026)
- Evidence: when the timeframes agree, 4 W / 1 L (+3R); when they disagree, 0 W / 5 L (-5R) (12, 17, 20, 27, 31 Mar). Small samples.
- **Each 08:00 call first tags the 1h and 15m structure: AGREE or DISAGREE.**
  - **AGREE:** trade with both, under the v2 stop / target / path rules. A grade-C flag applies when the last pre-08:00 candle is a rejection wick at a key high or low (lesson of 30 Mar).
  - **DISAGREE:** the call is **NO TRADE**. The day is still logged, with the side v2 would have taken (paper), so the skip can be checked later.
- The broker go/no-go is judged on AGREE calls only: they need a win rate of at least 55% over at least 20 calls before a real combine.

## Post-mortem after 17 Apr (the trader: "its really important you understand why the trade lost and that you should have taken the opposite direction")
- **With a symmetric 1:1 bracket, the opposite trade is the exact mirror:** every loss is an opposite-side win. The useful question is which pre-08:00 clue should have flipped the side.
- GC-data check of all 27 calls (11 Mar - 17 Apr; offsets from the 08:00 open): traded 18, mine -2R / opposite +2R; skipped or paper 9, mine -7R / opposite +7R. GC can differ by a few points (13 Mar: GC says target, OANDA said stop).
- **17 Apr, why it lost:**
  - it sold the bottom of a 2-day 4768-4872 range;
  - two failed breakdowns (long wicks at 4775 and 4768) showed buyers defending;
  - the 4h / daily trend was up (13 Apr gap low 4645 -> 4872).
  - Long was the location-correct side.
- **Hypotheses found AFTER the fact (they need fresh days, not this sample):**
  - **H1 location:** a trade whose path runs into a nearby level (buying under resistance or selling above support, within about 1 x risk) loses. The FADE at that level is the better side. Losses that fit: 12, 13, 20, 30 Mar, 10, 14, 17 Apr.
  - **H2 disagree days:** when the 1h and 15m disagree, the 15m (most recent) side won and the 1h side lost: 27, 31 Mar, 2, 8, 9, 15 Apr = 0 for 6 for the 1h side. This is the opposite of the v2 "1h wins" rule.
  - **H3 context:** always read the 4h / daily trend and where price sits in the multi-day range before calling the side.

## v4 (from 20 Apr 2026)
- Before the side: the 4h / daily trend, and the position in the multi-day range (top / middle / bottom).
- **At a range edge or a nearby level:** call the FADE (buy support / sell resistance with the bigger trend), stop beyond the level + 0.5 x ATR15, 1:1. Do not trade INTO the level.
- **Mid-range, timeframes agree, clean path:** trade with them (A grade).
- **Disagree days:** NO TRADE stays, and log the 15m side on paper (H2 test).
- Judge v4 only on calls made from 20 Apr on. These hypotheses were fitted on 11 Mar - 17 Apr and cannot be validated on those days.
