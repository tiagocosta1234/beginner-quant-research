# PREREG_PHASE3_BLIND: making the early-window +0.4 R believable (DRAFT until the trader says "approved")

Written 25 Oct 2026 (local clock). the trader: "I wanna make that +0.4R believable". The claim: the trader's discretionary entries between 08:00 and 08:15 local averaged +0.40 R (2023, n=19) and +0.29 R (2025, n=19), pooled about +0.34 R before costs, standard error about 0.19. It was a post-hoc slice (about 15 slices looked at), and the mechanical A+ version of the same window averaged -0.04 R over 2019-2026. This test is built so a lucky or hindsight-driven result cannot pass.

## What is tested (rules fixed here; same as `MANUAL_1M_B.md` but ONLY the early window, no extra A+ filters)
- XAUUSD 1-minute chart on FX Replay, local clock, his 12 EMA, news/calendar overlays off.
- Bias = 15-minute trend, written in the log BEFORE 08:00 of each day (long / short / neutral). Neutral = no trade.
- Entry only on a 1-minute candle that CLOSES beyond the 12 EMA on the bias side, with the signal candle opening between 08:00 and 08:15. One trade a day. Planned reward at least 1.0 x risk. Stop beyond an order block or FVG, at least 1.5 points away; target a high / low / order block / FVG. The stop is never moved.
- No setup by 08:15 = a "no trade" row (counts as a day, not a trade).

## Fresh, sealed days (this is what stops hindsight)
- 12 non-overlapping 30-calendar-day windows were drawn by a seeded random generator (seed 20261026) from 2020-01 to 2022-11, excluding every window the trader has already seen or traded (Aug 2021 and Nov-Dec 2022 touched by older battles; 2023, 2025 and 2026 were all used in earlier tests and are not in the pool). The list is in `WINDOWS_SEALED.csv` (hash in `WINDOWS_SEALED.sha256`) and is NOT to be opened by the trader: Claude reveals one window at a time, only the start date.
- Each window is one FX Replay session started at 07:30 local of its start date, played forward only, in calendar order, never revisited. the trader does not look up what gold did on those dates.

## Log (written BEFORE stepping forward after the entry)
`PHASE3_LOG.csv`: session, date, signal candle open (local HH:MM), side, stop distance in points, target distance in points, target type, "logged_before_result" = yes, screenshot ref, notes. Distances, not prices, so the CFD-vs-futures price gap cancels. Rows without "yes" are not scored. Skipped signals are logged as notes, not hidden.

## Independent scoring
`score_phase3.py` scores every logged trade on Databento GC futures (not on the chart he traded): entry = close of the logged 1-minute candle +/- 0.1 point; stop and target = the logged distances; same costs as every other test here (slippage 0.1, target trade-through 0.1, commission USD 1.20 per micro, time exit 17:00 local, same-bar stop and target = stop). Each trade also gets a mirror (same distances, opposite side); random-side P = share of 20,000 draws, each trade independently actual or mirror, whose mean R is at least the actual mean. This separates direction skill from gold's drift.

## Sample size and stopping
Play the sessions in the drawn order until at least 100 scored trades or all 12 windows are used; no early stop for a good or bad run. (With about one trade every second day, 100 trades take roughly 8-12 sessions.)

## Gate (decided now)
PASS = at least 80 scored trades AND mean R net >= +0.15 AND random-side P <= 0.05 AND mean R net >= 0 for longs and for shorts (each with at least 10 trades). Anything else = the +0.4 R was luck, noise or a data artefact; no re-tuning on these days.
- Honest power: with 100 trades the standard error is about 0.12 R. If the true edge is +0.30 R net this gate passes about 80% of the time; at +0.15 R about 50%; with no edge about 5%. So a pass is strong evidence; a fail is not proof of zero but ends the case for buying anything.

## What a pass does and does not do
A pass makes the early-window read a candidate. The checklist and the demo mornings continue, and the purchase decision still needs the live-demo process gate. It still promises no withdrawal.
