# PREREG_HALFR_FXR: does the FX Replay half-R plan beat the 0.5R baseline on unseen days?

Written Tue 2026-10-27 night (local clock). Status: TEMPLATE. Fill section 1 BEFORE the first scored trade, then hash it (see the end). Nothing in sections 1-3 changes once the first scored trade is logged.

Base rate first: the most likely result is no edge. A random 0.5R bracket wins about 65% of the time (mechanical test, `HALF_R_GROSS_OUTPUT.txt`), so a high win rate alone proves nothing. The first block (36 trades, 27W / 9L, 75%, +$5,037, 24 May - 21 Jun 2023) is consistent with true win rates from about 69% (no edge) to 80%. Earlier blind tests of 1:1 reads came out at 40-45% wins (no edge).

## 1. The plan (the trader's answers, 27 Oct 2026 night; filled in before trade 1)
- Instrument / account in FX Replay: the trader's usual one in FX Replay (gold, as in the 24 May - 21 Jun 2023 session xa - aa87); recorded per session in the log.
- Sessions: London and New York (never Tokyo). Exact windows: the setup at each open.
- Bias / entry rule: discretionary, a simple mechanical setup at the open. the trader keeps the rule to himself and commits to apply the same rule on every trade; it is not scored by Claude, only the logged results are.
- Stop rule: the trader's own stop for the setup; 1R = the stop distance.
- Target: 0.50R net of costs. the trader sets the gross target at about 0.51 to 0.55R so that net R after trading costs is about 0.50R.
- Risk per trade (fixed, USD): 1,000.
- Max trades per day / what ends the day: as in the first session (one or two a day, London and New York).
- Spread and commission: NOT in FX Replay (no costs applied there). The scorer subtracts 0.05R from every trade (`--cost-r 0.05`, the trader's estimate: commissions about 5% of R).
- Days used: paste the FX Replay session ID of each finished session in `HALFR_LOG.csv` (column `fx_session_id`); never replay a day already played.

## 2. Test design
- Days: unseen days chosen by FX Replay's random start, no skipping, no abandoning a day; play in the order shown.
- Blocks: block 1 = 100 trades, block 2 = 100 more trades on new days (200 total). Block 1 gives a progress read only, no verdict.
- Every trade logged before the next bar: date, session, side, entry, stop, target, risk in USD, result in USD. A no-trade day is logged as a no-trade.
- Stop rules: no changing the plan between trades; a change restarts the count.

## 3. Bar (single look at trade 200, `score_halfr.py`)
SUPPORTED only if all hold: n >= 200 AND win rate >= 74% AND mean R > 0 AND one-sided bootstrap P(mean R <= 0) <= 0.05. Reported, not gating: win rate against the 65% random baseline (exact binomial), per-block win rate, 95% interval of mean R.
Not met = "NOT SHOWN: no evidence of an edge over the 0.5R baseline", the plan is closed or restarted from scratch, not tuned.

## 4. What passing buys
Passing is a lead, not a licence. Next: 20 paper trades in real time (delay, slippage, platform), then a paid eval only with money earned outside trading.

## Hash (run after section 1 is filled in)
`Get-FileHash PREREG_HALFR_FXR.md -Algorithm SHA256` -> save in `PREREG_HALFR_FXR.sha256`.
