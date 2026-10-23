# PREREG_READ_TEST: does the apprentice's frozen read of the trader's setup pick the right side on fresh gold days?

Written 22 Oct 2026 ~22:5x local (local clock), before any test day was drawn or seen. the trader, 22 Oct: "keep training until you have a really good read", then the goal "you get really good at trading".

## Why
- After all 33 of the trader's London days, my calls on GC beat their mirror image by +0.217 R a trade (sign-flip P 0.037, n 27; `MANUAL_READ.md`, `MANUAL_READ_BASELINES_OUTPUT.txt`).
- That result is in-sample:
  - the read was learned on those same days (Apr-May 2025, Jan 2026);
  - each reveal showed the rest of the day;
  - P 0.037 was one of three tests.
- This test plays the read, frozen, on days it has never seen, with no outcome shown until every call is locked.

## Data and days
- Databento GC 1-minute continuous front month (`futures/data/databento/futures_GC.F_1m.parquet`), the `desk.py` / `manual_read.py` frame. The date is hidden, prices are rebased (06:00 local open = 1000), and only candles up to the one being judged are shown.
- **Pools:** weekdays of 2023-01-02..2023-12-29 (pool A, a calmer, rangier regime) and 2025-06-02..2025-12-31 (pool B, the gold bull regime that follows the learning days).
  - Not used: the learning days, Sep-Nov 2024 (the earlier F desk), Jun-Aug 2024 (the trader's training camp C5 window), 2026 (January learned; Feb-Sep the sealed hold-out).
  - A day is playable only if every 1-minute bar 07:45-10:00 local exists. Unplayable days are skipped by code before they are shown.
- **Draw:** 50 days from each pool, `numpy.random.default_rng(20261022)`, the two lists interleaved A, B, A, B, ... (100 days, ids T001-T100). Fixed by `read_test.py` before the first day is shown.

## The frozen read
- `MANUAL_READ.md` lessons 1-20 and `manual_read.py` features v8, as they stand at this file's hash. The sha256 of both files is recorded in `PREREG_READ_TEST.sha256` next to this file's hash.
- No lesson, feature or threshold changes until all 100 calls are locked. New ideas go to a "pending" list and are applied only after the result.
- **Window:** signal candle 07:59-08:14 local, entry at the next candle's open, one trade a day, or "none".
- **Bracket (mechanical):**
  - target = the scanner's the trader-style level for the called side on the signal candle: the nearest level at least 2 ATR away, else at least 0.8 ATR;
  - if there is no level, the target is 2.5 ATR;
  - stop = target distance / 0.53.
  - The call states only the side and the signal candle; `read_test.py` computes the bracket.
- Exits and costs are the desk's: stop / target on 1-minute bars (stop first if both are touched in one bar), 1 tick on the entry and stop plus 0.15 points, flat at the day's end.

## Measures (one look, after T100 is locked)
- **Primary:** excess over a random side = mean over trades of (R - mirror R) / 2.
  - Mirror = same signal candle and distances, other side.
  - One-sided sign-flip P over all trades, 20,000 draws, seed 7, as in `manual_read_baselines.py`.
- **Supported iff excess >= +0.10 R and P <= 0.03.** Anything else is "not shown".
- **Secondary (reported, no bar):**
  - mean R and win rate;
  - no-trade days;
  - each pool alone;
  - the naive rule (08:00 candle in the direction of the 30-minute trend, same mechanical bracket) on the same 100 days, its excess and P, and the read's excess minus the naive excess on the days both trade;
  - the read's calls whose signal is 08:00-08:02 against later calls.
- **Power** (per-trade SD of the paired difference about 0.6, about 80 trades, SE about 0.067): P(supported) about 90% if the true excess is +0.217, about 30% at +0.10, about 3% at none.

## What it would mean
- **Supported:** the read picks sides better than chance on unseen gold days at the London open. That would be the first discretionary-style result in this repo to pass a pre-registered out-of-sample look. It would earn a forward paper log on live London sessions, still not money.
- **Not shown:** the 33-day result was in-sample luck or regime knowledge, like every mechanical form before it.
