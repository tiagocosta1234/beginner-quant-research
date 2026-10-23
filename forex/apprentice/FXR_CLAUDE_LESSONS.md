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
