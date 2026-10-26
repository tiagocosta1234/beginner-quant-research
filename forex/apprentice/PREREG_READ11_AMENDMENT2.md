# PREREG_READ11 Amendment 2: the naive 1:1 rule as a second hypothesis

Written 26 Oct 2026 ~00:0x local (local clock), after training day R023, BEFORE the test pool is drawn (READ11 not frozen, `state_r11x` empty). the trader: "run it".

## Why
- In training (R001-R023, 2023) the naive rule beat the read: 23 trades, 15 W, mean R +0.144, excess +0.306, P 0.061; the read made -0.132.
- It is mechanical, so testing it on the sealed pool costs no extra calls. It was found on training days, so it needs the sealed test like the read.

## Hypothesis H2 (mechanical, no discretion)
- Every test day: side = sign of (08:00 close - 07:30 close) (the 30-minute trend at 08:00); signal candle 08:00; bracket = `bracket11` at 08:00 on that side (1:1 at X); entry the 08:01 open; desk costs; flat at 20:00. Exactly the `naive_trend30` line already scored.

## Bar (both hypotheses, split for two shots)
- **H1 read11 supported iff:** excess >= +0.10, sign-flip **P <= 0.015**, mean R > 0, mean R > always-long, n >= 40.
- **H2 naive supported iff:** excess >= +0.10, sign-flip **P <= 0.015**, mean R > 0, mean R > always-long, n >= 40.
- P <= 0.015 replaces 0.03 for H1 (Bonferroni over the two).
- If either is supported: live paper calls only, logged before the outcome. Real money stays the trader's decision.
