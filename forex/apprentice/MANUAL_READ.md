# the trader's read, as the apprentice learns it (v1 written 22 Oct 2026 ~21:5x, before playing any of his days)

Source for v1: his own words in `forex/ea_research/ema12/MANUAL_WHY_ENTRIES.md` and the rules card. Each played day ends with a comparison against his real call.
Disagreements become numbered lessons here, and the version number goes up when the read changes.

## v1: what I will look for, in this order
1. **Time:** the first minutes of the London open. 34 of his 50 entries came within 2 minutes of 08:00, so the earliest good candle wins.
2. **Family A, displacement at the EMA:**
   - the candle opens at or touches the EMA 12 (a wick through it counts) and closes strongly on the trade side;
   - body at least about 1 ATR and bigger than the sum of its wicks;
   - small close-side wick (a big wick is fine when it is a rejection of a 1-minute gap);
   - a close beyond the previous 5 candles (BOS) adds confluence;
   - the trend helps but is optional.
3. **Family A2, continuation:** a strong candle in the trend right after a wick pullback to the EMA. It need not be a cross.
4. **Family B, sweep reversal:** the candle takes out the previous hour's (60-candle) extreme and reverses, even on the wrong side of the EMA. Confirmation is a gap in the reversal direction or a displacement candle (BOS).
5. **Skip:**
   - candles that are not big enough;
   - closes inside a 1-minute rejection block or an untouched gap remainder;
   - a touched FVG in the wrong direction;
   - no strong candle or no clear bias in the first 15-30 minutes (his no-trade rule).
6. **Bracket:**
   - target = the nearest structural level (an untouched 1-minute gap edge, equal highs / lows, a 5-minute gap edge, the session high / low);
   - stop = target distance / 0.53 (his ratio);
   - exception, a "protected low": stop at the signal candle's extreme inside a rejection block, target 0.5 R.

## Lessons from experience
(added after each block of days; agreement = same decision, same side, signal candle within 2 minutes)

**Block 1 (K001-K008; K003 excluded because I could identify the day from the January list).** 7 counted days:
- trade / no trade 7 / 7, side 7 / 7, full 4 / 7;
- my R on GC +0.07 (5 W 2 L... see the log), the trader's R on GC similar.

1. **Target = a significant level, not the nearest small one** (K001). His target was the big untouched 07:12 gap (1.7 wide), about 5.7 points away; mine was nearby equal highs.
2. **Sweep reversal: he takes the reversal candle itself, without waiting for a BOS or gap confirmation** (K004: his long 08:05 on the reversal candle; I waited until 08:09). Matches MANUAL_WHY_ENTRIES: his past sweep entries came before the confirmation.
3. **His brackets are wide** (K006: same 08:04 candle, he won with a 7.35 stop, I lost with 2.6).
   - Targets about 2-3 ATR away (Jan 2026 median about 4 points), stops about 4-5 ATR (target / 0.53).
   - v2 bracket: the nearest significant level at least 2 ATR away, else at least 0.8 ATR.
4. **The close-side wick must be small; a long far-side wick is a rejection and he likes it** (K007: his 08:01 short had a 5-point upper spike rejected, close-side wick 0.1; my scanner skipped it because the body was smaller than the biggest wick). v2 scanner fixed.
5. (Tentative, n = 1, K005) After a huge first candle (2.6 ATR at 08:00) he did not chase; he entered at 08:14. Watch for more cases.

**v2 in force from K009:** lessons 2-4 applied (scanner, bracket, take the sweep reversal candle).

**Block 2 (K009-K019; K009 excluded by mistake: it was 8 May 2025, not a January day).**
6. (K010) His bias comes from the opening push; he bought the first dip / EMA wick after the push up, where I saw chop.
7. **(K011) Opening-push continuation:** after the opening displacement, he enters on the first candle that resumes the push after a small pullback. No EMA touch is needed.
8. (K012) A sweep made by the opening push itself is not a reversal signal for him; family B means reversing the move before the open.
9. (K013, his only January no-trade day) Pushes in both directions at the open = no clear bias = no trade.
10. (K014) On the first decisive push after a flat open he takes the push candle itself, even with a bigger close-side wick.
11. (K015) In a strong trend (about 3+ ATR in 30 minutes) the trend wins: he sells the end of the bounce. A family B reversal needs a strong displacement through the EMA (as in K001).

From K016 the v3 lessons gave full matches on K016, K017 and K018. Status at the usage cut (22 Oct ~22:0x): 19 of 33 days played (17 counted).

**Block 3 (K019 onward; v4 scanner from K021).**
12. **(K019) A high-volume pin bar at the open is a family B entry for him.** The 08:00 candle had a body of 0.08 ATR, a lower wick of 1.5 (above 1 ATR), volume 5x the median, and it rejected the 07:49 equal low and closed above the EMA. He bought it at 08:00 (stop 3.68, target 1.89). I never saw it: the scanner took the side from the candle's colour (red = short) and needed a body of 0.5 ATR or more.
    - v4 scanner: a far wick of at least 1 ATR and at least twice the other wick and the body sets the side.
    - Such a pin is a candidate when it closes on the trade side of the EMA with volume at least 1.5x the median.
13. **(K020) An extended push is not chased.** Push up 07:59-08:02: the 08:01 candle was 1.34 ATR, the 7th green candle in a row, and opened 1.64 ATR above the EMA. He skipped it.
    - He waited for the pullback (08:03-08:04, two red candles, 0.92 ATR) and bought the first full-size candle resuming the push: 08:07, 1.12 ATR (lesson 7).
    - Lesson 10 (take the push candle itself) applies when the push starts at the EMA. In K014 the 08:06 candle opened 0.5 ATR from the EMA and crossed it with a 1.69 ATR body.
    - Working rule: if the candle opens more than about 1.5 ATR from the EMA after a run of 4 or more candles the same colour, scan on for the pullback and resumption candle.
    - The v4 scanner prints `open_from_ema_atr` and `run_before`.
    - On GC his 08:07 long was stopped (-1.07 R) and my 08:01 long hit the target (+0.53 R). That is luck on one day; the goal is to match his read.

14. **(K021) The pin bar does not need volume; it is his favourite open candle.**
    - Context: an uptrend from 06:00 (+3.8 ATR in 30 minutes).
    - He bought the 08:00 candle: lower wick 1.2 (1.11 ATR) that swept the 07:54-07:58 lows, body 0.3, close above the EMA, volume 1.0x the median. Bracket: stop 1.66, target 0.87, a small one.
    - I skipped the 08:05 counter-trend short (right), but no long candle was flagged, so I had no trade.
    - v4 scanner: a pin closing on the trade side of the EMA is a candidate at any volume.
    - Two of the last three days were 08:00 rejection pins.

15. **(K023) A weak cross that is undone at once is a false break; then he sells the EMA retest.**
    - Pre-open: a sell-off from 1013.7 to 1004.9, then a 07:54 reversal push of +1.50 ATR that closed under the EMA.
    - 07:59 crossed the EMA weakly (0.58 ATR, 44% close wick); I bought it as a family B reversal.
    - The 08:00 candle undid it (-0.94 ATR, back under the EMA, after taking out the 07:59 high).
    - He shorted 08:03: a small green candle whose upper wick reached into the EMA (0.7 against a 0.5 body) and closed under it. That is selling the end of the bounce (lesson 11).
    - Rule: a family B reversal needs a strong push that CLOSES through the EMA. A strong push under the EMA plus a weak cross is not one.
    - v5 scanner: an EMA-retest rejection (wick into the EMA against the 30-minute trend, close back on the trend side, wick at least the body and 0.3 ATR) is a candidate, side from the trend.
    - Both trades hit their targets on GC (mine +0.48 R, his +0.49 R).
16. **(K022, full match) A clean opening push with the trend is taken at 08:00** even with a big close-side wick (83%) when it is not extended (opened 1.0 ATR from the EMA). Same short, a similar bracket, both won.
    - Base rate from the first 21 days: 13 of his 20 trades signal at 08:00-08:02, and he had one no-trade day. I called none 6 times where he traded, so the read must be less picky.

17. **(K024 against K015) He trades the reaction at a level more than the trend.**
    - K024, after a 7 ATR sell-off that based on equal lows (07:56 1003.5): the 08:00 candle retested the low (1003.6) and held with a lower wick. He bought the next green candle, 08:01, under a falling EMA. Target the near edge of the untouched 07:52 bear gap, 1009.7 (2.2 ATR, which my v2 bracket would have picked); stop 7.83.
    - I applied lesson 11 (the trend wins), skipped 08:01 and bought 08:04: same side, 3 minutes late, both won.
    - K015 was different: the crash bounced about 5 ATR straight into the big 07:52 gap and stalled with upper wicks (08:05, 08:08); he sold the close back under the EMA at 08:10.
    - Rule: a held pre-open low or high at the open sets the side. "Sell the bounce" is for a bounce that runs into a level and stalls.
    - v6 scanner: `held` = the previous candle tested the 30-minute low or high (equal within 0.15 ATR, or swept by up to 1 ATR) and closed 0.4 ATR or more off it, and this candle goes the held way.

    - K025 (full match, L 08:02): a family A EMA touch plus a rejection of the untouched 07:56 bull gap in an uptrend, close near the high. Same candle; both won.
    - K026 (tentative, same side, 3 minutes late): after a rally the 08:00 candle rejected the EMA and gap top with a small body (0.44 ATR). He waited for 08:03, the first close above the pre-open range high (986.8) on high volume. In K024 he took a small candle at the level, so this stays a note, not a rule.
    - K027 (full match, L 08:02): two ambiguous candles at a gap under resistance; I waited, and the 08:02 push candle (1.12 ATR, close at the high, the second up push) was his entry too.
18. **(K028) A sweep of the session low at the open turns him long, even in a -5 ATR downtrend.**
    - Pre-open: the bounce failed at the 07:44 bear gap, 07:57 displaced down, and price sat 0.5 ATR above the session low (982.0).
    - I shorted the 07:59 continuation into that low.
    - The 08:00 candle swept the low to 980.3 and closed back at 983.8 (2.6 lower wick, high volume). 08:01-08:03 made higher lows with rejection wicks.
    - He bought 08:03 (stop 11.94, about 5 ATR under the sweep, target 6.56) and was stopped; my short hit the target. One day; the aim is his read.
    - Rule: do not trade a continuation into the session extreme at 07:59 when it is within 1 ATR. Let the 08:00 candle show whether it sweeps and turns.
    - v7 scanner: `post_sweep` = a candle in the last 5 made a new 60-minute extreme with a wick of at least 0.5 ATR, and this candle turns the other way without a new extreme. A WARNING prints when a candidate before 08:01 runs into the session extreme within 1 ATR.

    - K029 (full match, L 08:00 vs his 08:02): a high-volume pin at the open (4.7x, 2.0 lower wick into the EMA and the 07:54 bull gap top) in a +6.6 ATR uptrend. Both won.
19. **(K030, like K015) After a crash, he sells the bounce where it stalls under the crash's untouched bear gap.**
    - The session fell 1002 -> 961, then bounced +4.9 ATR in 30 minutes.
    - I bought the 08:03 resumption candle (lesson 7) with the target at the 06:43 bear gap edge 986.2.
    - He waited: 08:04 left a 1.5 upper-wick rejection at 984.6 under that gap, 08:07 made a lower high, and he shorted 08:07. Target the EMA (1.68), stop just inside the gap (3.25). Both won on GC.
    - Rule: when the trend since 06:00 is down and the last 30 minutes is a bounce toward an untouched gap left by the drop, the bounce is the pullback. The trade is the stall under the gap, not the push toward it (mirror image for rallies).
    - v8 scanner: `stall_under_gap` = a rejection wick of at least 0.75 ATR in the last 3 candles within 1.5 ATR of an untouched opposite gap's near edge, then a candle turning away with a lower high / higher low.

20. **(K031, like K024) Do not over-wait: the first candidate that fits the day's bias is usually his.**
    - Uptrend since 06:00. The pre-open drop held the 07:50 bull gap and recovered in one candle. 08:01 touched the EMA and closed back up (0.53 ATR).
    - I passed on it because of the tentative K026 "wait for the range break" note, then shorted the 08:03 displacement after 1011 held four times.
    - He bought 08:01 and was stopped (-1.06 R); my short hit the target (+0.48 R).
    - In K024 too he took the 08:01 candle I skipped.
    - Rule: when the first candidate agrees with the trend since 06:00 and a level just held, take it; the K026 note does not override.

    - K032 (full match, S 07:59 vs his 08:01): a down day, the bounce stalled under the 07:51 bear gap, a wick into the EMA and a close back under. Both won.
    - K033 (full match, S 08:00): a 2.05 ATR opening displacement from near the EMA, with the trend. Both won; lesson 5 (no chase) did not apply.

## Result after all 33 of the trader's days (22 Oct 2026 ~22:4x; `manual_read_baselines.py`, `MANUAL_READ_BASELINES_OUTPUT.txt`)

**Agreement (full match = same side, signal within 2 minutes):**

| Days | Full match | Same side |
|---|---|---|
| K001-K010 | 4 / 10 | 7 / 10 |
| K011-K020 | 3 / 10 | 5 / 10 |
| K021-K030 | 4 / 10 | 6 / 10 |
| K031-K033 | 2 / 3 | 2 / 3 |
| **All** | **13 / 33** | |

- **The learned read does not beat a naive rule at predicting the trader.**
  - "Trade the 08:00 candle in the direction of the last 30 minutes" matches him on 14 of 33 days (9 of 18 on days 16-33, the same as the read); "the move since 06:00" also 14.
  - Most of his read is "trade the trend at the open". The lessons have not yet added predictive power beyond that.
- **P&L on GC (desk costs), each trade against its mirror (same entry and distances, other side):**
  - my 27 trades: mean +0.240 R, mirror -0.194, excess over a random side +0.217 R, 23 / 27 wins, sign-flip P 0.037;
  - the trader's 32: +0.043, mirror -0.224, excess +0.133, P 0.142;
  - naive 30-minute trend at 08:00 with the the trader-style bracket, 33: +0.064, mirror -0.118, excess +0.091, P 0.204.
- **This is in-sample and not evidence:**
  - the read was learned on these same two periods (Apr-May 2025, Jan 2026), whose regime (a strong gold uptrend with violent April days) is shared across days;
  - the reveals showed each day's later chart;
  - P 0.037 is one of three tests.
  - The wide bracket (target about 2 ATR, stop target / 0.53) wins about 65% at random, so the win rate alone means little: only the excess over the mirror counts.
- **Next:** a pre-registered test of the frozen read on fresh blind days from another period, with no outcome shown until all calls are locked (`PREREG_READ_TEST.md`)., then the live London session on 23 Oct with `live.py` (and the v4 read noted here).
