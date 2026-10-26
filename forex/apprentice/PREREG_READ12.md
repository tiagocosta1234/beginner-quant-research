# PREREG_READ12: a 1:1 read trained and tested on recent gold (2026)

Written 26 Oct 2026 ~00:1x local (local clock), before any 2026 day was drawn or seen by Claude. the trader 26 Oct: "you should train in recent price action" (read as his OK to use the sealed 2026 hold-out, except his blind batch 2).

## Why
- READ11 (trained on 2023, tested on 2019 / 2024 / 2025) failed. Gold in 2026 trades at about 4,000 with a different volatility; a read learned on recent days may differ.
- Honest prior: low. The 2025 pool of READ11's test (the most recent) also showed nothing (H2 pool G: mean R -0.003, excess +0.097, P 0.25).

## Data
- Databento GC 1-minute, which ends 25 Sep 2026. A day is playable only if every bar 07:45-10:00 local exists.
- **Excluded:** the 30 days of the trader's blind batch 2 (`ea_research/ema12/BLIND_BATCH2.csv`), and January 2026 (his read days). Nothing about any day is told to the trader.
- **Training pool (40 days):** weekdays 2026-02-02..2026-05-29, drawn with seed 20261026 + 1. Each day revealed after its call; lessons in `READ12.md`.
- **Test pool (sealed): every playable non-excluded weekday 2026-06-01..2026-09-25**, in calendar order, drawn only after `READ12.md` is frozen.

## The read and the bracket
- Starts from MANUAL_READ lessons 1-20 and READ11 lessons T1-T6 (frozen READ11.md), with the v9 constraints (30-minute trend side only, signal 08:02 or later, one trade a day or none).
- Bracket fixed now, same as READ11: 1:1 at X = v9 stop distance (manual_bracket level distance / 0.53, else 2.5 ATR / 0.53); desk costs; flat 20:00.

## Bar (one look, after the last test call)
- **Supported iff** excess over the mirror >= +0.10 R, sign-flip P <= 0.03, mean R > 0, mean R > always-long (08:02, same bracket, every test day) and n >= 30.
- Also reported, no bar: naive 08:00 30-minute trend with the same bracket; longs and shorts apart; realised win / loss ratio.
- Power is low (about 35-40 trades expected; SE of the excess about 0.15): about 30% at a true +0.25. A fail is the likely outcome and will be accepted.
- If supported: forward paper calls from the next London session, logged before the outcome. Real money stays the trader's decision; Claude places no real orders.
