# MANUAL_1M_B phase 3 (DRAFT, NOT frozen): one narrower rule on fresh days

Drafted 25 Oct 2026 (local clock) after phase 2 FAILED (`MANUAL_1M_B_PHASE2_RESULT.md`). the trader must approve and Claude hashes it BEFORE the first trade. Until then nothing here is a rule.

## Question
Does the same strategy (15m bias, 1-minute close beyond the 12 EMA on the bias side, target high-low / order block / FVG, stop beyond an order block or FVG) make money when entries are taken ONLY between 08:00 and 08:15 local?

## Why this and nothing else
- Early entries (08:00-08:15) averaged about +0.40 R (2023, n=19) and +0.29 R (2025, n=19); later entries lost in both samples. Pooled: 38 trades, about +0.34 R before costs, standard error about 0.19. The slice was picked after phase 1 and checked on phase 2, so it is a hypothesis, not a result.
- No other change: no new filter, no new target rule, no tuning on seen days.

## Frozen-on-approval rules (draft)
- XAUUSD 1-minute, FX Replay, local clock. Entry window 08:00-08:15 only; a signal after 08:15 is skipped and logged as a skip. One trade a day.
- Bias, entry, target and stop rules as in `MANUAL_1M_B.md` (phase 2 rules). Stop is NOT moved after entry (phase 2 had four zero-R exits).
- Risk: USD 400 per trade planning figure (R is scored from entry / stop / target); futures contract cap noted, not a rule change.
- Log before stepping forward: bias (before 08:00), side, candle time, entry, stop, target, target type, screenshot. Days with no signal get a "No trade" row.

## Days
- Fresh days only: start Tue 2 Jan 2024, forward only, calendar order, never back. Not used in any earlier test according to the project logs; the trader confirms he has not traded or reviewed 2024 gold in FX Replay.
- Stop at exactly 40 executed trades (not before, not after). If 2024 runs out first, the result is "inconclusive", not a pass.

## Gate (draft)
- Mean R >= +0.20 after costs (spread 0.48, desk costs about 0.11 R a trade), about 22 wins of 40 at the phase 1 payoff.
- Honest power: even if the true edge is +0.23 R after costs, 40 trades pass this gate only about half the time (standard error 0.19). A fail does not prove no edge; a pass is evidence, not a promise.
- Pass: the trader may buy ONE evaluation (Broker Flex 50K is the current pick; check price and rules at checkout). Fail: no purchase, and the strategy is shelved or redesigned from scratch, not re-tuned on 2024.
