# READ11: the 1:1 read (training log; frozen with `python read11.py freeze` before the test draw)

Base: `MANUAL_READ.md` lessons 1-20 and the v9 constraints (with the 30-minute trend, signal 08:02 or later). Bracket fixed by `PREREG_READ11.md`: stop and target both X = v9 stop distance (about 4-5 ATR), so a trade needs room for a move of X in its direction before X against it, often over hours.

## What changes with a 1:1 at X (thinking before training)
- At 0.53:1 a trade only needed the first push to the nearby level; at 1:1 it needs the move to travel about twice as far. The question is no longer "does the next level get hit" but "is this the day's direction".
- So day-level bias matters more than candle quality: the trend since 06:00, which side of the session range the open is on, and whether the session extreme in the trade direction is likely to break.

## Lessons from training (R001-R040)
Running tally after R005: 4 trades... see `READ11_TRAIN_CALLS.csv`; R001 W +0.84, R003 W +0.85, R005 L -1.07; none on R002 and R004 (both would have won with the trend).

- **T1 (R002, R004) Too picky at 1:1.** Two "no bias" days where a with-trend EMA candle went on to win. At 1:1 the question is the day's direction, not a clean open: a rejected spike (R002) or a down-then-up open (R004) is not "no trade" when a full-size candle then closes back through the EMA with the 30-minute trend and the day's structure (since 06:00) agrees. Tentative, n = 2.
- **T2 (R003) The day's direction beats the 30-minute trend.** Down since 06:00 with bear gaps overhead: the short after the bounce stalled under the gaps won, the naive 30-minute long lost. Keep lesson 19.
- **T3 (R005) Do not buy the first pullback after a news-like spike (5+ ATR in two candles at the open).** It retraced the whole spike in 20 minutes and stopped the 1:1. Tentative, n = 1.
- **T4 (R001) Small-ATR days cost more:** a 2.1-point X turned a 1:1 win into +0.84 R after costs.

**Halfway score (R001-R023, `python read11.py train score`, 26 Oct 00:00 local clock):**
- read11: 16 trades, 8 W, mean R -0.132, excess +0.064 (P 0.36); realised 0.77:1 (avg win 0.87, avg loss 1.14).
- naive 08:00 30-minute trend, same 1:1 bracket: 23 trades, 15 W, mean R +0.144, excess +0.306 (P 0.061).
- always long 08:02: mean R -0.136, so the naive result is not long drift in 2023.
- read minus naive on the read's own days: -0.055.

- **T5 My discretion is subtracting value against the naive rule.** On 6 of my 7 no-trade days the naive side won, and my filters (lessons 9, 13, 19, T2) skipped or flipped days the plain 30-minute trend got right. Tentative fix for R024 on: trade the first allowed candle (08:02+) on the 30-minute-trend side unless a hard reason applies (a news-like spike, T3; or the side runs straight into the session extreme within 0.5 ATR). Do not stack soft reasons.
- **T6 (R021, R015) Brackets under about 1.2 points are noise plus costs:** R021's trade and its mirror were both stopped.
- Lessons T1 and T2 failed their next tests (R012, R013); they stay in the log as history but are not rules.

**Final training score (R001-R040, 26 Oct ~00:3x local clock):**
- read11: 31 trades, 15 W, mean R -0.169, excess +0.005 (P 0.44), realised 0.76:1. Always-long 08:02: -0.171. No skill shown.
- naive 08:00 30-minute trend: 40 trades, 23 W, mean R -0.006, excess +0.183 (P 0.10), realised 0.73:1. It fell from +0.144 at R023.
- T5 (trade the first allowed candle with the 30-minute trend) made R024-R040: 8 W 7 L, about -0.2 R. The "new session high = no wall" clarification went 1 / 3 (R001 W, R031 L, R035 L).
- T6 (X under 1.2 points is noise) held on R033 (naive -1.37 at X 0.57).
