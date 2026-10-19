# PREREG_JAN2026: a descriptive January 2026 look at the two failed mechanical 12 EMA rules (EMA12, MANUALRULE)

Written 2026-10-19 14:2x (local clock, main PC) BEFORE any P&L of this look was computed. Dry-run (counts only) done 14:17: last bar read 2026-01-30 23:58, 21 weekday sessions per market and session.

## Why this exists
the trader asked "have you backtested for the whole 2026 days until today my strategy?". The answer was no: `PREREG_EMA12.md` and `PREREG_MANUALRULE.md` seal the 2026 hold-out (1 Jan-30 Sep) unless a trial passes DEV 2022-24 and VAL 2025, and none did.
Offered a 2026 run, the trader answered: "i mean i'm down for the blind replay ... run a january 2026 run". Read as: his waiver of the sealing rule for **January 2026 only**, as a descriptive look.

## What is run
- The 32 EMA12 trials (PREREG_EMA12 with Amendment 1) and the 12 MANUALRULE trials (PREREG_MANUALRULE), exactly as registered: no new variant, no parameter changed, same engines (`ema12_test.py`, `manualrule_test.py`), MT5 broker M1 bid/ask, XAUUSD and NSDQ.
- Period: 2026-01-01..2026-01-31 only. Enforced at read time in `jan2026_look.py`: rows with time >= 2026-02-01 are never loaded.
- Reported (fixed now): the 44-row table (n, wins, mean R, t, with each trial's DEV and VAL mean R next to it); pooled lines (MANUALRULE gold, MANUALRULE gold K1 = the variant closest to the trader's words, EMA12 gold, both rules on Nasdaq, all 44): mean of the trial means for January against DEV and VAL, and how many trials are above zero.
- Per-day trades are neither printed nor saved: the trader's blind replay of January days (PREREG_BLIND2026) must stay blind, so he only gets aggregates.

## What it cannot do
- No acceptance bar. n is about 20 per trial (a mean R has a standard error near 0.18-0.20), so one month cannot pass or fail a rule and cannot make any trial a candidate. A trial that looks good here is NOT opened further on the rest of 2026.
- Its only use: does January look like 2022-25 (negative) or like the trader's 30 trades (positive)?
- The rules are mechanical stand-ins; his discretionary entries are tested only by the blind replay.

## Prior (written before the run)
Expect most of the 44 trial means to be negative, like DEV (-0.02..-0.15 R) and VAL (about zero). I do not expect January to change the verdict.

## Bookkeeping
The 2026 hold-out for future candidates shrinks to 2026-02-01..2026-09-30; January and 1-16 Oct 2026 become open data. Ledger rows follow (family `jan2026`), then a checkpoint update and START HERE.
