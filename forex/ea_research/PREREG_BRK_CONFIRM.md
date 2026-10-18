# PREREG BRK_CONFIRM - does a candle CLOSE beyond the box tell continuation from a bounce better than the first touch?

Registered 2026-10-16 19:34 local (local clock, second PC PC-2), before any P&L of these trials was computed.
the trader: "i wanna know how i can improve the chances of being able to identify if a high or low will continue or bounce
off" -> "pre-register the candle-close confirmation test and run it". Not tested before in this repo: earlier rounds
tested touch entries, buffers beyond the level, retests, first-seconds tick features and late triggers (`BREAKOUT_KNOWLEDGE.md`),
never an entry conditioned on a completed 5- or 15-minute candle closing outside the box.

## Boxes (the trader's two setups)
- **LDN**: box 08:00-08:30 local; confirmation / entry window 08:30-11:00 local; exit 17:00 local.
- **NY**: box 09:30-10:00 New York (DST-aware); window 10:00-12:00 New York; exit 16:00 New York.
- Box high / low = highest bid-high / lowest bid-low of the box minutes (same as `brk2.py` / `orbx.py`). A box needs >= 80%
  of its minutes. Universe: the 38 non-crypto MT5 broker (`orbx.CRYPTO` excluded). MT5 broker M1 bid/ask 2021-12..2026-10-16 in
  `forex/data_mt5`, zero-spread minutes repaired as in `PREREG_BRK_PATTERNS.md` amendments 1-2 (previous month's median non-zero
  spread; months without any spread data take the next month's).

## Entry modes
- **TOUCH** (yardstick, the rule the trader trades): buy stop at the box high (fills when ASK reaches it, at max(level, ask open)),
  sell stop at the box low; first to fill inside the window.
- **C5**: the first 5-minute candle (clock-aligned: 08:30-08:35, ...) whose MID close is above the box high (long) or below
  the box low (short) and which completes inside the window; market entry at the next minute's open (ask for a long, bid for
  a short).
- **C15**: the same with 15-minute candles (08:30-08:45, ...).
- One trade per market, box and day per mode. Trade rule identical for all modes: SL = the other side of the box, no target,
  exit at the session-end minute (bid for longs, ask for shorts); same-minute rule and gap rule of `orbx.walk`; on the entry
  minute only the SL counts. R = net P&L / |entry - SL|.

## Trials (4)
LDN-C5, LDN-C15, NY-C5, NY-C15 (each pooled over the 38 markets). Yardsticks, not trials: LDN-TOUCH, NY-TOUCH, and a
random-timing control per trial (same day, same side, entry at a uniformly random minute of the window after the box, same SL
level and exit).

## Periods
DEV 2022-01-01..2024-12-31 (selection), VAL 2025-01-01..2025-12-31, HOLD 2026-01-01..2026-10-16 (one look, only for trials
that pass DEV and VAL; 2026 touch-entry results of these boxes have been seen before, confirmation entries have not).

## Acceptance (all must hold)
- DEV: n >= 500; mean net R > 0 with day-clustered t >= 2.5 (Bonferroni for 4 one-sided trials at 5% is z 2.24, rounded up);
  mean > the same box's TOUCH yardstick on the same days set (paired difference t >= 2.0, day-clustered); mean > its
  random-timing control; positive in at least 2 of the 3 DEV years.
- VAL: mean > 0 with t >= 1.65. HOLD: mean > 0 with t >= 1.65.
- **Account environment (standing rule):** for any trial passing DEV + VAL + HOLD, the rule is replayed on the trader's two markets
  (NSDQ and XAUUSD, $250 risk a trade) and on all markets it passed on, from the live balance (last known 95,472.14), MT5 broker rules
  (-2,500 day or 92,000 = breach, +2,000 day cap, pass 108,000), 5-day block bootstrap and historical replay; it is reported
  usable only if P(pass) > P(breach) by 30 Jun 2027. The account view for NSDQ and XAUUSD is reported for every trial
  regardless of the verdict.

## Descriptive (answers the trader's question directly, not trials)
- "Bounce" share: fraction of trades whose mid price trades back inside the box within 60 minutes after entry, by mode.
- Continuation share: fraction that reach +1 R before -1 R.
- The same by year and by market class.

## Dry run (no P&L)
`python -m forex.ea_research.brk_confirm --dry-run`: counts per mode, box and period; share of days where the confirmation
fires but the touch did not (and vice versa); truncation causality test (cut the data at random times on 3 markets: every
entry before the cut must be identical); a hand check of 3 random C5 / C15 entries printed with their confirming candle.

## Honest prior
About 7%. Waiting for a close filters some 1-minute pokes (the late-trigger feature was weakly positive in gold and Nasdaq),
but the confirming close also moves the entry further from the stop's level at a worse price, and 94% of breakouts trade back
inside the box within an hour anyway.

## Window
New family (confirmation entries): 4 of 40 variants.

## Amendments
1. (2026-10-16, after the dry run, before any P&L) Engine-only fixes, no rule change: the mid-close array is computed once per
   market (speed), and the dry-run count table used the pandas method `T.mode` instead of the column `T["mode"]` (it printed 0).
   Dry-run counts: about 26,700-28,900 DEV and 9,000-9,600 VAL trades per mode and box; truncation test identical on 3 markets.
