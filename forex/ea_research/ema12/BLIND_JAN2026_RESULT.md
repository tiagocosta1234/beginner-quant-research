# Blind replay, batch 1 (January 2026, London, the trader's own entries): gate passed, no verdict yet, 2026-10-19

Pre-registration `PREREG_BLIND2026.md` (current sha256 5638e3f2e31742634a36e927d517c0b0dc9154c7a3a6d7f72cd4fba5f61f676b, Amendment 4 included). Log `BLIND_LOG_JAN2026.csv`, scorer `blind_score.py`, output `BLIND_JAN2026_SCORE_OUTPUT.txt`, format check `blind_check.py`.

## How the log was made (read this before the numbers)
- the trader replayed the 21 January weekdays in calendar order in one FX Replay session (2 Jan 07:30 to 30 Jan) and finished all of them: 20 trades and one no-trade day (20 Jan).
- In Notion he filled only Direction, Result and a screenshot per day. I read Entry, Stop, Target and the box-start minute (= the last visible candle, local clock) off the 20 screenshots; the 6 Jan stop is not visible and was estimated from the bottom of the box (4451.5, error about 0.2). Every logged entry sits within 0.4 USD of the MT5 broker mid close of the logged minute (basis +0.05; two minutes corrected by price: 21 Jan 08:03, 29 Jan 08:01). His reported Win / Loss agrees with the MT5 broker replay on 20 of 20 trades, so the reconstruction is faithful.
- **Caveat on "logged before the result":** the screenshots were taken after each trade ended (the charts run to the exit), so they do not prove the boxes were drawn before the result. the trader attested in chat (19 Oct, about 19:00): "i didnt recognized any day, always executed every drawn box before playing". The log carries flag 0 and pre 1 on his word. For the next blocks the proof should be built in: a screenshot taken right after drawing the box and BEFORE pressing play shows no future candle, so it is its own time stamp.

## Result (MT5 broker bid/ask, entry at the open of the candle after the last visible one, his stops and targets, same-minute stop and target = loss)
| n | his side | mirror | random side | excess over random | P(random >= his) |
|---|---|---|---|---|---|
| 20 | 13 wins, mean R +0.008 (t 0.05, 95% CI -0.30..+0.32) | -0.224 | -0.107 | **+0.115** | 0.255 |
- With 0.30 USD extra cost: his side -0.029, excess unchanged. Entry shifted +1 minute: +0.008 (same). Entry shifted -1 minute: +0.316 (excess +0.348, P 0.016), but that enters at the open of the candle he had already seen close, a price he did not have, so it is not a tradable reading; it only shows how much a one-candle move matters when the target is 0.54 R.
- Win rate 13 of 20 = 65%; the break-even for this reward / risk (0.54) is about 65%. The April-May 2025 sample had 24 of 30 (80%).

## Decision (PREREG_BLIND2026, rules unchanged)
- Futility rule after batch 1: stop if scorable n >= 12 and excess < +0.05. n = 20, excess +0.115: **not stopped, go to batch 2.**
- This is a gate, not evidence: the mean R of +0.008 is no better than break-even, the excess has P 0.26, and the 95% interval of his own mean R spans -0.30..+0.32. January fits both "no skill" and "a real +0.15 R edge".
- Next: batch 2 = the 30 sealed days (`BLIND_BATCH2.csv`, shown to the trader now, 30 rows created in the old Notion list with Teste = "Replay cego fev-set 2026", view "Replay fev-set 2026"), then Look 1 at about 44 scorable trades: supported iff mean R >= +0.10 and P <= 0.03 over the pooled trades. For the pooled mean to reach +0.10 at n = 44, batch 2 needs about +0.17 R on average.

## Correction of 20 Oct 2026 (FX Replay's own trade records)
FX Replay's Trades page (app.fxreplay.com, `FXREPLAY_TRADES_2026-10-20.csv`, check `fxr_check.py`, output `FXR_CHECK_OUTPUT.txt`) records entry, stop and target of every trade. All 20 January trades match this log except the stop of 6 Jan: FX Replay recorded 4451.068, the screenshot estimate was 4451.5 (+0.432). Rescored with that stop (`BLIND_LOG_JAN2026_FXR.csv`): his side 13 wins, mean R +0.007 (95% CI -0.30..+0.32), mirror -0.224, random side -0.108, excess +0.115, P 0.273 (before: +0.008, +0.115, P 0.255). The decision (futility stop not triggered, batch 2 goes ahead) is unchanged. Also found there: a second, unlogged Buy on 30 Jan at 08:39:55 (outside the entry window; not scored).
