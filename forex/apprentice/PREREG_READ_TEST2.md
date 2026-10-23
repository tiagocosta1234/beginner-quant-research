# PREREG_READ_TEST2: the apprentice's read v9 (v8 plus two coded constraints) on 100 fresh gold days

Written 23 Oct 2026 ~01:3x local (local clock), before the draw and before any of these days was seen. the trader: "keep learning"; goal "you get really good at trading".

## Why
- The frozen read v8 failed its blind test (`READ_TEST_RESULT.md`): excess +0.066 R, P 0.143, the same as the naive trend rule.
- Its exploratory breakdown (post-hoc) showed two things:
  - trades with the 30-minute trend made +0.119 R (69) and against it -0.269 (24);
  - signals at 08:03 or later made +0.188 (23), against -0.037 at 07:59-08:02 (70).
- The mechanical version of "with the trend after a pullback" (TRENDOPEN) failed on DEV 2020-2022 (-0.191 R on 521 trades).
- So the only open question is whether my discretion, restricted this way, picks better entries than that rule. Prior: low, about 10% to pass.

## The read v9
- `MANUAL_READ.md` lessons 1-20 and the `manual_read.py` v8 scanner, frozen at this file's hashes (`PREREG_READ_TEST2.sha256`).
- Two constraints, enforced by `read_test2.py` (a call that breaks them is refused):
  1. **With the 30-minute trend only:** the side must match the sign of (signal close - close 30 candles earlier).
  2. **Signal candle 08:02 local or later:** let the first two candles of the session show their hand. The window still ends at the 08:14 candle.
- Everything else is as in PREREG_READ_TEST:
  - one trade a day or none;
  - mechanical the trader-style bracket (nearest level >= 2 ATR, else >= 0.8 ATR, else 2.5 ATR; stop = target distance / 0.53);
  - desk execution and costs;
  - date hidden, prices rebased, only candles up to the one judged are shown;
  - each call hashed when locked;
  - no outcome shown until all 100 calls are locked.

## Days
- Databento GC 1-minute; a day is playable only if every bar 07:45-10:00 local exists.
- **Pool A:** 50 weekdays of 2022 (a flat-to-down year for gold).
- **Pool B:** 50 weekdays of 2024-01-02..2024-05-31 (an up-trend).
- Drawn with `numpy.random.default_rng(20261023)`, interleaved A, B, A, B (T001-T100).
- None of these days was played or looked at one by one.
  - TRENDOPEN read 2022 by code, aggregate result only.
  - Not used: Jun-Nov 2024, 2023, 2025, 2026.

## Measures (one look, after T100)
- **Primary:** excess over a random side = mean of (R - mirror R) / 2 over trades, sign-flip P (20,000 draws, seed 7).
- **Supported iff excess >= +0.10 R, P <= 0.03 and mean R after costs > 0.**
- **Secondary (no bar):**
  - mean R;
  - wins;
  - no-trade days;
  - each pool;
  - the naive 08:00 trend rule on the same days and the read's excess minus the naive one.
- With about 70 trades (v9 trades less), SE is about 0.07: power about 75% at a true excess of +0.20, about 25% at +0.10, about 3% at zero.

## Amendment 1 (scorer only; written 23 Oct 2026 08:45 local, local clock, after T100 was locked and before any outcome was shown)
- The first `score` run crashed in the naive baseline before printing anything: `desk.simulate` returns None when the next candle's open (plus or minus 1 tick) is already at or beyond the target or the stop, so the bracket cannot be placed.
- Rule, for the read and the naive baseline alike: such a pair (the trade or its mirror) counts as no trade, and the scorer reports how many were dropped.
- The scorer's verdict line had left out the third pre-registered condition. It now reads: supported iff excess >= +0.10 R, P <= 0.03 AND mean R after costs > 0, as written above.
- Nothing else changes: the calls, the bracket, the costs, the measures and the bars stay as they are.
