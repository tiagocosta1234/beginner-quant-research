# PREREG_READ11: a 1:1 read, trained on fresh gold days, then tested once on sealed days

Written 25 Oct 2026 ~23:4x local (local clock; hash time corrected before any training day was opened), before any day of these pools was drawn or seen. the trader 25 Oct: "train for 1:1s" (after asking for an average reward:risk above 1:1 before going live; read v9's was 0.53:1 planned, 0.38:1 after costs).

## Why, and what this is not
- Read v9 failed its replication (`READ_TEST3_OUTPUT.txt`: excess +0.085, P 0.167). It stays closed (CLAUDE.md "never re-tune or reopen" list).
- An exploratory re-pricing of the 86 already-scored v9 trades (test 2 + test 3) at 8 brackets, IN-SAMPLE and chosen after looking, is the only reason for the bracket below:
  - 1:1 with both distances = the played stop (target / 0.53): mean R +0.116, excess +0.249, P 0.008;
  - 1:1 at 4 ATR: +0.090, excess +0.209, P 0.023;
  - tight 1:1 (1.5 ATR, or stop = played target): mean R -0.33 / -0.21 (costs).
  - Picking the best of 8 variants on scored days inflates it. Honest prior for the true excess: about a third of +0.249, so about +0.08.
- READ11 is a NEW read: it starts from the MANUAL_READ.md lessons 1-20 and the v9 constraints, adds lessons learned on the training pool below, and is frozen before the test pool is drawn. Nothing here re-scores v9.

## The bracket (fixed now, not tuned in training)
- Entry: next 1-minute open after the signal candle, as before (desk.simulate, desk costs, flat at 20:00 local).
- Distance X = the v9 the trader-style stop distance: nearest significant level (manual_read.manual_bracket v2) distance / 0.53; with no level, 2.5 ATR / 0.53.
- **Stop = entry side - X, target = entry side + X. Planned reward:risk 1:1.**
- A bracket whose entry is already beyond the target or the stop is no trade (test 2 Amendment 1).

## Constraints kept from v9
- One trade a day or none; side with the sign of the 30-minute trend; signal candle 08:02 local or later; every allowed scan candidate gets its own decision (`scan11.py` auto-passes only the forbidden ones).
- Date hidden, prices rebased, candles shown only up to the one judged; each call hashed when locked.

## Pools (Databento GC 1-minute; a day is playable only if every bar 07:45-10:00 local exists)
- Excluded everywhere: 2020-2022, Jan-May 2024 (tests 2-3), Jun-Aug 2024 (C5 camp), Apr-May 2025 and Jan 2026 (the trader's read days), 28 Nov - 27 Dec 2023, 28 Feb - 29 Mar 2025, Feb-Sep 2026 (FX Replay reserve).
- **Training pool T (40 days):** weekdays of 2023 outside the exclusions. After each call the day is revealed (1:1 outcome of the call, its mirror, 15-minute bars to 14:00) and a lesson may be written in `READ11.md`.
- **Test pool (150 days, sealed):** pool E = 50 weekdays Jun-Dec 2019; pool F = 50 weekdays Sep-Dec 2024; pool G = 50 weekdays Jan-Feb and Jun-Dec 2025. Drawn only after READ11.md is frozen and hashed, seed 20261026, interleaved E, F, G.

## Measures (one look, after the 150th test call)
- Primary: excess over a random side = mean of (R - mirror R) / 2, sign-flip P (20,000 draws, seed 7).
- **Supported iff excess >= +0.10 R, P <= 0.03, mean R after costs > 0, and at least 40 trades.**
- Secondary (no bar): mean R, win rate, realised average win / average loss (the trader's "above 1:1" question), each pool, the naive 08:00 30-minute-trend rule with the same 1:1 bracket, and the read minus naive.
- Power at n about 55 trades (SE of the excess about 0.13 at 1:1): about 35% at a true +0.25, about 8% at +0.08. A fail is the likely outcome and will be accepted.
- If supported: live paper calls only, logged before the outcome. Real money stays the trader's decision, and Claude places no real orders.
