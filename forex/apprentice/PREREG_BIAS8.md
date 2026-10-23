# PREREG_BIAS8: Claude's 08:00 long / short bias on gold, and which targets get hit before a 1R stop

Written 23 Oct 2026 (local clock, time in the commit), before the draw and before any of these days was seen.
the trader: "lets focus on going long or short at 8:00, try to see if your bias getting better and better, then you focus on what
targets get hit the most before 1:1 stop loss".

## Why
- Every rule-based read so far lost or just missed (rubric -0.114 R, v8 +0.019 R, v9 +0.093 R at P 0.038, TRENDOPEN -0.191 R).
- This test strips it down to one decision a day: long or short at the 08:00 local open. Two questions:
  1. Is the bias better than a coin and better than dumb rules, and does it improve with feedback?
  2. Given the side, which target (in R of a fixed stop) is hit most often before the stop, and does any target make money?
- Unlike tests 1-3, the outcome is shown right after each call is locked: learning is the point. Calls cannot be changed.

## Honest prior and power
- Prior: a discretionary 4-hour direction call on gold is about a coin flip; a true 53-55% would already be good.
- 200 days. One-sided P <= 0.05 against 50% needs 112 / 200 (56%).
  - Power: about 13% at a true 53%, about 40% at 55%, about 85% at 58%.
- A learning trend over 200 days is hard to see unless it is large. A null here does not prove there is no learning.

## Days
- Databento GC 1-minute (`futures/data/databento/futures_GC.F_1m.parquet`), local clock.
- Pool: weekdays 2019-07-01 .. 2025-12-31, minus:
  - every day the apprentice was shown before, one by one (test 1-3 orders, `APPRENTICE_LOG_GC`, `APPRENTICE_SHADOW_GC`, `MANUAL_READ_LOG`, `MANUAL_CALLS`, `LIVE_LOG`);
  - the desk's reserved windows (Jan-Sep 2026, Apr-May 2025, 28 Nov - 27 Dec 2023, 28 Feb - 29 Mar 2025);
  - all of 2026.
- The rubric backtest and TRENDOPEN read some pool days by code only, as aggregate results; they were never shown one by one.
- Playable: every 1-minute bar from 07:00 to 16:59 exists, the previous weekday's 08:00-21:59 exists, and no minute-to-minute jump above $8 from 00:00 to 16:59 (roll).
- 200 days drawn with `numpy.random.default_rng(20261025)`, ids B001-B200.

## What I see before the call (`bias8.py show`)
- Date hidden; prices rebased so the 07:59 close = 1000.00.
- Previous weekday 08:00-21:59 in 30-minute bars; today 00:00-07:44 in 15-minute bars; 07:45-07:59 in 1-minute bars.
- Levels: previous high / low / close, Asia high / low (00:00-07:59), and S = ATR(14) of the 15-minute bars ending 07:59.
- Nothing at or after 08:00.

## The call
- `bias8.py call L|S CONF "reason"`. CONF is 1-3 (1 = lean, 3 = strong). There is no "none": the call is forced every day.
- Hashed (SHA-256) and written with the PC time before `reveal`. One call per day, in id order.

## Fills (desk conventions)
- Entry at the 08:00 open, 1 tick (0.1) worse.
- 1R = S. Stop at entry -/+ S, filled 1 tick through.
- A target fills only if traded 1 tick through.
- A bar that reaches both stop and target counts as the stop.
- Commission 0.15 points a round turn.
- No position past the cutoff: exit at the cutoff bar's open.

## Measures (one look, after B200)
- **Bias outcome:** the sign of (11:59 close - 08:00 open). A call is correct when the side matches. A zero move counts as wrong.
- **Primary 1, bias:** hits out of 200. **Passes iff hits >= 112 (one-sided binomial P <= 0.05) AND more hits than every baseline on the same days:**
  - always long;
  - the previous day's direction (21:59 close vs 08:00 open);
  - overnight direction (07:59 close vs 00:00 open);
  - the last 30 minutes (07:59 close vs 07:30 open).
- **Primary 2, learning:** correlation of day index with correct, permutation P (20,000 draws, seed 7).
  - **Improves iff P <= 0.05 (one-sided, positive) AND block 5 (B161-B200) > block 1 (B001-B040).**
- **Primary 3, targets:**
  - Grid: targets 0.5 / 1 / 1.5 / 2 / 3 R, cutoffs 12:00 and 17:00 = 10 configs, all at the 1R stop.
  - For each config: hit-first rate and mean R after costs.
  - **DEV = B001-B100: pick the single config with the best mean R.**
  - **VAL = B101-B200: it passes iff mean R > 0 with one-sided bootstrap P <= 0.05 (20,000 draws, seed 7).** One look, no re-pick.
- **Secondary, no bar:**
  - hit rate by block and by CONF;
  - the same target table for the mirrored side (does my side add anything?) and for always long;
  - stop-hit rate;
  - mean R against the trader's live bar of +0.5 R a trade.

## Rules
- No change to this file, the script or the grid after the draw. Amendments only before B001 is shown, written here with the reason.
- If it fails, it is logged in the ledger as a fail and not re-tuned. If the bias passes, the next step is forward paper calls at 08:00, logged before the open.
- Lessons I write after each reveal go in `BIAS8_LESSONS.md` (allowed: the test measures learning).
- Paper only. No real orders.
