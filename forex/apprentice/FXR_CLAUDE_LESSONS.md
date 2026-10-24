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

## Session ae16da37 closed (25 Mar - 24 Apr 2026 replay days; FX Replay day limit) - written 24 Oct 2026
**Numbers:**
- FX Replay balance 50,000 -> 48,072.32.
- My traded calls: 3 W / 7 L. The wins were 26 Mar, 1 Apr and 21 Apr (the v4 fade). The losses were 27, 30, 31 Mar and 10, 13, 14, 17 Apr.
- My skipped days (paper side): 2 W / 9 L, so skipping avoided about 7R of losses.
- the trader's own read on blind batch-2 days, all sessions: 7 trades, **5 W / 2 L, +3R**: the best result in the project.

**What I learnt:**
1. **Skipping no-setup days is the most valuable rule I have.** The paper side lost about 80% of the time (all sessions: 2 W / 18 L).
2. **Location beats direction.** Most of my losses traded INTO a level within about 1 x risk (12, 13, 20, 30 Mar, 10, 14, 17 Apr). The level held and the trade died there.
3. **A level touched 2-3 times with wick rejections is strong, even against the trend.** 17 and 21 Apr (4768-4770) and 24 Apr (the 4658-4668 triple bottom): the fade won each time. On 24 Apr I passed on the fade because of the daily down-trend, and gold rallied about 70 pts. My "fade only with the bigger trend" filter was too strict.
4. **"The 1h wins" (v2) was wrong, and "agree" alone is a coin flip** (about 50%).
   - The 15m-side test on disagree days (H2) went 1 W / 3 L under v4: not confirmed.
5. **Stops at 0.5 x ATR15 beyond a swing still get wicked on slow days** (10 Mar, 17 Mar, 13 Apr, 14 Apr; often by under 1-2 pts).
6. **Execution check:** the green box sits on the target side (11 Mar was placed reversed).

**What I will do next time (v5, judged only on fresh days):**
- At 8:00, first: the daily trend, the multi-day range edges, and a COUNT of touches and wick rejections at the nearest levels.
- **Trade only two setups:**
  - (A) **the FADE of a 2-3-touch level** with wick rejections (stop beyond the level + about 1 x ATR15; target 1:1 or the next level);
  - (B) **timeframes agree + a clean path** to a 1:1 target.
- Everything else is NO TRADE (paper side logged).
- Track A and B separately; judge each after 20 calls. No new rules on fewer calls than that.
- **On batch days the trader goes first with his own levels.** My call is a second opinion. His read is the edge we are testing.
- **Next session:** start at 27 Apr 2026 07:30. Next batch day: 29 Apr. Remaining batch days: 29 Apr, 1 May, 11 May, 12 May, 8 Jun, 9 Jun, 17 Jun, 18 Jun, 23 Jun, 25 Jun, 9 Jul, 22 Jul, 24 Jul, 6 Aug, 12 Aug, 26 Aug, 14 Sep, 28 Sep.

### 27 Apr 2026 (session 52a21e9a), v5
- 08:00 NO TRADE (TF disagree, mid-range). Paper 15m-side SHORT 4712.8 / 4724 / 4701.6 tagged its target at 10:15 by 0.15: +1R paper; the skip cost 1R.
- Intraday long trigger (wick into the 4700-4705 shelf + green close > 4707) never fired by 11:00: closes 4706.8 / 4705.3 / 4702.4 / ... / 4702.1, the 11:00 wick to 4707 rejected. Skip day.
- Tally of disagree days by the 15m side: this one won. Keep counting before changing the rule.

### 28 Apr 2026, v5
- 08:00 NO TRADE: all timeframes DOWN after the 4658-4668 base broke (06:00 crash to 4624), but a short sold INTO the 4623-4625 double low. Paper SHORT 4629 / 4645 / 4613: chopped 4614-4640 for 2.5 h (two sweeps under the lows, reclaimed), then broke down 10:15-11:00 to 4604: +1R paper.
- The retest short at 4640-4658 never came (highs 4639.6 / ~4636).
- Second day in a row the skip cost 1R. Both times the "level in the way" (4701 shelf on 27 Apr, 4623 double low on 28 Apr) BROKE in the trend direction.
- Hypothesis to count (not a rule change yet; v5 is judged after 20 calls): a level under price does not block a short when the daily + 1h + 15m all point down and the level is a fresh intraday low (hours old) rather than a multi-day base. Running tally: blocked-by-fresh-level skips 2, paper wins 2.

### 29 Apr 2026 (BATCH DAY), v5
- the trader: SHORT 4584.67 / 4593.48 / 4575.72 -> target hit on the 08:15 candle (low 4569.5). +1R, balance 50,509.87.
- Claude: NO TRADE (paper 15m-side SHORT, same levels) -> +1R paper. The 4576 overnight low "in the way" broke on the first push.
- 3 days in a row the v5 "level in the way" skip cost 1R; all 3 levels were hours-old intraday/overnight lows, broken in the daily-trend direction. Tally: fresh-level skips 3, paper wins 3. the trader's batch-2 own read: 8 trades, 6W/2L, +4R.

### 30 Apr 2026, v5
- 08:00 NO TRADE (daily down / 1h + 15m up, extended into the 4600-4611 range top). Paper 15m-side LONG 4589.66 / 4575 / 4604.32 hit at 08:45: +1R paper.
- The 4600-4611 short trigger: the 08:45 wick to 4605.6 closed 4598.4 (0.4 above the line) = no trigger. The 09:00 candle went +20 to 4629.8 (close 4618.8) = range top broken. The strict trigger SAVED 1R (a short with stop 4611 would have been stopped).
- 08:00 15m-side paper results 27-30 Apr: 4/4 wins. Tally it (n tiny) before acting.

### 1 May 2026 (BATCH DAY), v5
- the trader: SHORT 4594.93 / 4610.61 / 4578.53 -> target hit 08:45 (low 4575.9). +1R, balance 51,034.67. His stop sat above the broken 4606 low + the 06:45 lower high (better than my paper 4605).
- Claude: NO TRADE (paper 15m-side SHORT) -> +1R paper. The 4584-4593 breakout base broke on the first push.
- 08:00 15m-side paper: 5/5 (27 Apr - 1 May). v5's "level in the way" veto: 0 saves, 4 costs (+1 save on 30 Apr from the strict intraday trigger). the trader's batch-2 own read: 9 trades, 7W/2L, +5R.
- Candidate v6 (judge at 20 calls, not now): at 08:00 take the 15m side (price vs EMA + last-2h swing direction) unless price sits ON a multi-day (2+ day) level; ignore hours-old levels.

### 4 May 2026, v5 (v6 shadow logging starts)
- 08:00 NO TRADE (1h + 15m down, short INTO the 4575-4584 multi-day base). Paper SHORT 4588.97 / 4599 / 4578.94 hit at 08:45: +1R paper; v6 shadow +1R.
- Long trigger at the base (close > 4588) never fired: 4574 held 4 times (4574.3 / 4574.05 / 4573.85 / 4572.1 at 10:45) but highs capped ~4585. Skip day.
- 08:00 15m-side paper: 6/6.

### 5 May 2026, v5 setup A -> LOSS
- SHORT 4548.34 / 4558.79 / 4537.84 fading the 4547-4552 3-touch cap with the daily trend, against 1h + 15m up. Stopped on the 09:45 candle (high 4559.57): -1R, balance 50,532.97.
- v6 shadow (15m side LONG) would have won. 08:00 15m side: 7/7 since 27 Apr.
- The faded cap was hours old (formed 03:30-07:45). Same pattern as the vetoes: hours-old levels break in the direction the 1h + 15m are moving.
- Head-to-head so far: v5 calls/skips 27 Apr - 5 May: live -1R, paper-side +6R. v6 shadow formally: 2 days (4 May +1, 5 May +1).
- Keep v5 live until 20 calls per its own rule, but this is the strongest pattern in the whole log. Revisit at 20.
- CORRECTION (same day): the full paper-side record on skip days is 2 Apr - 24 Apr 2W/9L, 27 Apr - 4 May 6W/0L = 8/17 (47%); with 5 May's v6-shadow win 9/18 = 50%. The "15m side" is a coin flip that ran hot this week, not an edge. v6 is shelved as a streak artifact; do not promote it.

### 6 May 2026, v5 setup B -> WIN
- LONG 4669.46 / 4655.92 / 4683.34: 1h + 15m up with no level overhead. Target ~09:45 (ran to ~4720 at 12:00, then a 50-pt dump to 4670 by 13:15). +1R, balance 51,046.53.
- v5 live calls this session: 5 May A -1, 6 May B +1.

### 7 May 2026, v5 retest long -> WIN
- 08:00 NO TRADE (2-ATR breakout to 4750; no chase). Paper 15m-side LONG stopped (the 10:00 wick 4721.8 tagged 4724): -1R paper. The chase rule saved 1R.
- Pre-stated retest trigger (wick into 4715-4727 + close > 4728) fired on the 10:00 candle: LONG 4734.32 / 4718.26 / 4750.55. Chopped 3 h, target 13:30. +1R, balance 51,549.66.
- Break -> retest -> close back over = the cleanest entry type so far (30 Apr's never came; this one did). Live v5 this session: 2W / 1L, +1R.

### 8 May 2026, v5
- 08:00 NO TRADE (mid-range). Paper 15m-side LONG stopped by the 08:15 break of the 4710-4714 base (low 4697): -1R paper. Skip saved 1R.
- Flipped retest-short trigger (red close < 4707 after a poke into 4710-4718) never fired: 08:30 closed green 4708.2, 08:45 doji 4707.9, then 09:00-09:15 green back to 4717.2 (wick 4722.7). Breakdown was a fake-out; skip day.
- Skip-day paper sides 7-8 May: 2 losses (the skips saved 2R).

### 11 May 2026 (BATCH DAY), v5
- the trader: LONG 4678.57 / 4651.95 / 4705.56 (bought the V off 4651 against the 1h + daily down). Stopped ~10:45 by a wick to the stop, then a bounce to 4664: -1R, balance 51,044.03.
- The stop sat ~4 pts above the 06:15 wick low (~4648) = inside the wick zone (flagged before placement). Retests of a V low often wick through the candle body low: stops go beyond the WICK.
- Claude: NO TRADE (paper L) -1R paper; the 4686-4695 short trigger never came (high ~4680).
- the trader's batch-2 own read: 10 trades, 7W/3L, +4R.

### 12 May 2026 (BATCH DAY), v5 setup B -> WIN
- the trader SHORT 4697.09 / 4713.13 / 4680.65 = Claude's locked setup B short. 6 h of chop 4685-4712 (13:30 wick ~1 pt from the stop), target 14:15. +1R, balance 51,553.83.
- The stop beyond the broken floor AND the wicks survived by ~1 pt: the 11 May lesson paid.
- Live v5 calls this session: 3W / 1L, +2R (A -1; B +1, +1; retest +1). the trader batch-2 own read: 11 trades, 8W/3L, +5R.

### 13 May 2026, v5 base-rejection long -> WIN
- 08:00 NO TRADE (mid-range). Paper 15m-side SHORT hit at 10:15 (+1R paper).
- Pre-stated base long (double test 4685.9 / 4686.0, close > 4694 by 0.1): LONG 4694.11 / 4680.64 / 4707.81. Target on the 11:00 wick (~4708.5). The base then broke to 4677.7 by 13:45: take 1:1 and walk.
- Live v5 this session: 4W / 1L, +3R. Balance 52,060.80.

### 14 May 2026, v5 setup A (failed breakout + limit entry) -> WIN
- 08:00 NO TRADE (upper range under the 4705-4712 cap). Paper 15m-side LONG hit by the 08:30 stop-hunt wick to 4718.88 (+1R paper).
- 08:45 red -15.8 confirmed the failed breakout. Market entry would have been a 28.7-pt stop with a target through the 4669 floor, so a SELL LIMIT 4701 / stop 4721.92 (beyond the wick) / target 4680.04 (above the floor). Filled ~09:15, target 14:30. +1R, balance 52,565.93.
- New tool: trigger fires on a 2-ATR candle -> limit order at the 50-60% retrace, stop beyond the wick, target in front of the next level, cancel by a set time.
- Live v5 this session: 5W / 1L, +4R. Setup A record: fading an hours-old level against the 1h -1; fading a multi-day 4-touch level after a failed breakout +1.

### 15 May 2026, v5 (called at 09:00; the replay ran past 08:00)
- Crash day (4680 -> 4539). NO TRADE: a short sold just over the 4558 crash low. Paper SHORT 4570.98 / 4591 / 4550.96 hit at 10:15 (+1R paper); the retest short never came. Skip.
- On trend days with no pullback, "don't sell into the low" misses the move. Skip-day paper sides this session: 27 Apr - 15 May tally kept in the CSV.

### 18 May 2026, v5
- 08:00 NO TRADE (disagree; under the 3-touch 4548-4552 cap). Failed-breakout short set up (08:30 wick 4560.1) but no close under 4545 before the 10:00 cutoff (4546.3 at 08:45; 4544.99 only at 10:15, after the cutoff). Skip. Paper long unresolved at 10:30.

### 19 May 2026, v5
- 08:00 NO TRADE (mid-range, disagree). Short trigger fired at 09:00 (double top 4559.5 + close 4546.6) as a 2-ATR candle into the 2-day floor, so SELL LIMIT 4552.6 / 4562.6 / 4542.0. No retrace; cancelled at 10:30. Price fell to 4536 without us. 0R.
- Limit-entry cost check: 14 May filled (+1R), 19 May missed. Track fill rate.

### 20 May 2026, v5
- 08:00 NO TRADE (strong green into the cap). Paper LONG hit at 08:00 (+1R paper). Failed-breakout short never triggered before 10:00 (chop 4476-4490; 09:30 wick ~4490); the 10:15 red close 4474.3 came after the cutoff. Skip.
- Second day the trigger fired just AFTER the 10:00 cutoff (18 May, 20 May). Keep the cutoff (pre-registered), but track what those late triggers would have done.

### 21 May 2026, v5
- 08:00 NO TRADE. Paper SHORT stopped at 09:00 (+14.6 candle to 4536): the skip saved 1R.
- Rejection short at 4530-4542 never triggered before 10:00 (09:15-09:45 held 4529-4544). Chop to 11:00, then the 11:15 candle dumped -14.4 to 4510.8 (after the cutoff). Skip.
- Late-trigger log: 18 May unresolved, 20 May would have LOST (cutoff saved 1R), 21 May trigger only at 11:15 (90 min late).

### 22 May 2026, v5 conditional short -> LOSS
- Rejection short of the 3-touch 4531 cap inside a 4507-4535 chop (1h leaning down): SHORT 4521.84 / 4534.81 / 4508.36. Dipped to ~4515, then stopped by the 10:45 push to 4535.96. -1R, balance 52,060.02.
- The cap was a chop ceiling, not a trend level; the 1h "lean" was weak. Range-edge fades inside a 25-pt chop have a small edge at best.
- Live v5 this session: 5W / 2L, +3R.

### 26 May 2026, v5
- 08:00 NO TRADE; paper SHORT hit (+1R paper). Short trigger at 09:00 (double top 4539.2) closed ON the 4523-4527 double low, so SELL LIMIT 4534 / 4542.2 / 4525.8: not filled (highs ~4531), price fell to 4518; cancelled 10:30. 0R.
- Limit-after-trigger fill rate: 1/3 (14 May filled +1R; 19 May and 26 May missed; both moves went our way). A 55% retrace is too deep for gold's follow-through; consider ~35-40% or a half-size market entry. Decide at 20 calls, not now.

## SESSION 52a21e9a SUMMARY (27 Apr - 26 May 2026; FX Replay day limit reached)
- Balance 50,000.00 -> 52,060.02 (+2,060.02 = +4.1%). 10 executed trades, 7W / 3L, +4R. Max drawdown from peak ~1R.
- Claude v5 calls executed: 7 (5 May A -1; 6 May B +1; 7 May retest +1; 12 May B +1 (= the trader's batch trade); 13 May base +1; 14 May failed-breakout limit +1; 22 May chop fade -1) = 5W / 2L, +3R.
  - Setup B (trend agree + clean path): 2/2. Pre-planned retest / base / failed-breakout triggers: 3/3. Fades of hours-old or chop-range caps: 0/2.
- the trader batch-2 own read in this session: 29 Apr +1, 1 May +1, 11 May -1, 12 May +1. Batch-2 total: 11 trades, 8W / 3L, +5R.
- Skip-day paper (08:00 15m side): this session 11W / 4L (+ 4 unresolved); 2-24 Apr 2W / 9L. Total 13W / 13L = coin flip. Skipping is not costing an edge.
- Rules that earned their keep: wait for the candle CLOSE on the trigger; stop beyond the WICK; 10:00 cutoff (late triggers: 1 would have lost, others unresolved); take 1:1 and walk (6 May, 13 May reversed right after the target).
- Open questions for 20+ calls: limit-after-trigger fill rate 1/3 (55% retrace too deep?); stop fading chop-range edges.
- Next session: new FX Replay session from 27 May 2026 07:30. Next batch days: 8 Jun, 9 Jun.

### 29 May 2026 (session 2eb6e1df; Claude is the trader in replay)
- LDN LONG 4516.32 / 4502.59 / 4530.32 (with the 1h; through the 4521-4525 triple top): target ~11:00. +503.81.
- NY BUY LIMIT 4527 / 4514 / 4540 (retest of the broken triple top), filled ~12:15, stopped by a ~4513 wick at 13:30-14:00, then the rally to 4552.7 hit the target zone. -753.54.
- MISTAKE: the swing low that mattered was the 09:00-10:00 wick at ~4510; the stop (4514) sat above it. Rule: on a retest entry, the stop goes beyond the LOWEST wick of the structure being retested (the whole pullback since the last swing), not just the breakout candles.
- 1 Jun LDN SHORT 4501.61 / 4525 / 4477.84 (all TFs down; stop beyond the whole pullback's wick): chopped 6 h up to ~4513, then crashed through the 4490-4497 base. +760.74. The wider stop is what kept us in.

### 4 Jun 2026: both shorts stopped by one spike (-1,002.94)
- LDN SHORT 4467.87 (0.24 lots, ~$504 risk) and the NY SELL LIMIT 4483 (~$450) were the same idea (fade 4480-4492 supply, daily down). The 12:45 candle spiked +20 to 4514.8 and took both in one bar.
- The day lost $1,002.94: OVER a $1,000 daily loss limit (slippage/fill on top of a planned $954). Fixes:
  1. Combined open risk cap = $900 (not $1,000), leaving room for slippage.
  2. The NY order must not be the same bet as an open LDN trade (same side + same level = double size on one idea). If LDN is still open at 12:00 and the NY idea is the same, skip NY.
  3. Check the economic calendar for 12:30-15:00 releases before placing the NY order (the spike came at 12:45 / US data time).
- 9 Jun: the short (the trader's and Claude's, same levels) was right on direction but a 15:00 news-style spike to ~4363 took the 4355.8 stop before the crash to 4258. Second US-data spike in a week (4 Jun 12:45, 9 Jun 15:00). Unmanaged brackets sit through US releases: check the calendar at 08:00 too, and on red-folder days put the LDN stop beyond the day's likely news range or skip.

### 9-11 Jun: stops swept by a hair, then the move went our way (9 Jun short; 11 Jun long)
- Stops placed ~5 pts beyond the obvious wick get swept: the market runs the stops sitting just past swing lows/highs, then reverses.
- Proposal for the trader (not a rule change until he agrees): stop = the wick +/- 0.5 x ATR15 (about 8-12 pts on gold now), sized down to keep $750 risk.
- EVAL CHECK: session 2eb6e1df peak EOD balance 50,518.76 (3 Jun); a Broker 50K trailing $2,000 EOD floor = 48,518.76. The 10 Jun close (48,020.56) is BELOW it: this session would have FAILED a 50K eval on 10 Jun (four of the losses were Claude's forced calls, 28 May - 5 Jun).
- 12 Jun: LDN long with the WIDER stop (wick - 8.5) won; the NY long with a stop 1 pt under the base bodies got swept (~4177) and then recovered to 4235. Third sweep-then-reverse loss in 4 days (9, 11, 12 Jun). The wider-stop rule (wick +/- ~0.5 ATR, sized to $750) should be standard for both slots.

### Target-size check (24 Oct 2026, `rr_target_test_jun2026.py`, GC 1m data, 27 replay market entries 29 Apr - 23 Jun, exit at target / stop / 21:00)
- Sim at 1R: 13/27 wins (replay actual 14/27: the sim matches), mean +0.00R.
- 1.5R: 11/27, mean +0.12R, total +3.2R. **2R: 10/27, mean +0.21R, total +5.7R.** 3R: 5/27, mean +0.08R.
- Same entries and stops; only the target changes. In this volatile regime winners run past 1R (6 May, 1 Jun, 3 Jun, 19 Jun, 23 Jun). In-sample, n = 27, one regime: treat as a hypothesis to test forward, not a proven edge.
- Account catch: a 2R win at $950 risk = +$1,900 in one day, over Broker's 40% / Broker's 50% best-day rule. With 2R targets, size ~$600 (win = $1,200).
