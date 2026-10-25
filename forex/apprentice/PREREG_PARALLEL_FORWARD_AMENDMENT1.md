# AMENDMENT 1 to PREREG_PARALLEL_FORWARD.md

Written Sun 25 Oct 2026 (local clock), BEFORE the first test day (Mon 26 Oct). The original file and its hash are unchanged. Reason (the trader: "we need to be efficient and smart"): 40 days is too long for the budget, so a stricter early exit is added.

## Day-20 checkpoint (Fri 20 Nov 2026, 20 trading days logged)
Run `python score_parallel.py`. Then exactly one of:
- **Early pass:** mean daily net R of track A >= +0.45 AND one-sided P <= 0.02. Gate A is met early and the trader may buy ONE account (his decision, never Claude's).
- **Early stop:** mean daily net R <= -0.40 (already in the original). The indicator is dropped.
- **Otherwise** the test continues to day 40 and the original Gate A applies (mean >= +0.25, P <= 0.05).
The 10-day checkpoint (Fri 6 Nov) stays process-only: no pass, no stop, no purchase.

## P-value definition (clarifies the original wording)
Random-side baseline at day level: for each of 20,000 draws, flip a coin per DAY and, on a flipped day, replace all of that day's symbol results with their mirror trades (same stop and target distances, opposite side, mirror net R = -a_R_net - 2 x cost / risk). One coin per day keeps the four symbols' correlation, which is the conservative reading. P = share of draws whose mean daily R is >= the observed one.

## Error budget
Two looks (day 20 at P <= 0.02, day 40 at P <= 0.05) give a worst-case false-pass chance of about 7% if the indicator has no edge at all. That is the price of the shortcut, stated up front.

## Tool
`score_parallel.py` reads `PARALLEL_LOG.csv` and prints days logged, mean daily net R, standard error, the day-level random-side P, track B's mean, and which gate (if any) is met. It changes nothing.
