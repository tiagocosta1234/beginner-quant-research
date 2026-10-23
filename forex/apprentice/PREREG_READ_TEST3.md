# PREREG_READ_TEST3: replication of the frozen read v9 on 100 fresh gold days (2020-2021)

Written 23 Oct 2026 08:48 local (local clock), before the draw and before any of these days was seen. the trader: "keep learning"; goal "you get really good at trading".

## Why
- The read v9 (`PREREG_READ_TEST2.md`, `READ_TEST2_RESULT.md`) just missed its bar on 100 days of 2022 and Jan-May 2024: 47 trades, mean R +0.093 after costs, excess over a random side +0.161, P 0.038 against 0.03.
- One near miss is not evidence. The fair next step is to replay the SAME frozen read on days it has never seen, with the same bar, and accept what comes out.
- Honest prior: the true excess is probably smaller than the +0.161 measured; shrinking it halfway gives about +0.08.
  - Power at P <= 0.03 with about 47 trades (SE about 0.065): about 50% at a true +0.16, about 15% at +0.08, about 3% at zero.

## The read (frozen, unchanged)
- `MANUAL_READ.md` lessons 1-20 and the `manual_read.py` v8 scanner, at the hashes in `PREREG_READ_TEST2.sha256` (re-checked: unchanged).
- `read_test3.py` is `read_test2.py` (after its Amendment 1) with only the state folder, the call file, the seed and the pools changed.
- It enforces the same two constraints: the side must match the sign of the 30-minute trend, and the signal candle is 08:02 local or later.
- Calls follow the same practice as test 2:
  - one trade a day or none;
  - the trader-style bracket, desk costs;
  - date hidden, prices rebased, only candles up to the one judged are shown;
  - each call hashed when locked;
  - no outcome shown before T100.
  - Every scan candidate after 08:02 gets its own decision; no multi-step scan loops (the slip of test 2's T078).
- A bracket whose entry is already beyond the target or the stop counts as no trade (test 2's Amendment 1).

## Days
- Databento GC 1-minute. A day is playable only if every bar from 07:45 to 10:00 local exists.
- **Pool A:** 50 weekdays of 2020. **Pool B:** 50 weekdays of 2021.
- Drawn with `numpy.random.default_rng(20261024)`, interleaved A, B, A, B (T001-T100).
- None of these days was played or looked at one by one. The rubric (2020-2025) and TRENDOPEN DEV (2020-2022) read them by code only, as aggregate results.

## Measures (one look, after T100)
- **Primary:** excess over a random side = mean of (R - mirror R) / 2 over trades, sign-flip P (20,000 draws, seed 7).
- **Replicated iff excess >= +0.10 R, P <= 0.03 and mean R after costs > 0.** Same bar as test 2.
- **Secondary (no bar):** mean R, wins, no-trade days, each pool, the naive 08:00 trend rule on the same days, and the read minus naive.
- Also reported, no bar: test 2 and test 3 pooled. This is NOT a pass route; test 2's days were already scored.
- If it fails, v9 is closed on historical days and only forward live calls remain.
- If it passes, the read is a candidate: live paper calls at small size, logged before the outcome. Still no real money without the trader's decision.
