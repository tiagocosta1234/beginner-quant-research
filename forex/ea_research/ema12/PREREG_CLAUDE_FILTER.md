# PREREG_CLAUDE_FILTER: does Claude's take / skip call on the trader's setups separate winners from losers?

Written Mon 2026-10-26 evening (local clock), after Read v2 (NOT SUPPORTED, 41% wins) and BEFORE any trade of this test exists. the trader: "this is why
you need to be on my side to tell me if i should take each setup based on past performance" -> Claude: an honest test of that filter -> the trader: "yes".

## Design (double blind: no outcome exists for anyone until both decisions are locked)
1. **the trader** plays the 40 days of `BLIND_FILTER_2025.csv` (drawn now from the 174 unplayed 2025 days with full GC data, excluding his first sample
   2025-04-14..05-12, the 2025 practice days and the 40 Read v2 days; numpy default_rng(202610263)) in the MGC Blind Replay app, calendar order,
   Read v2 rules enforced (min stop 5 x noise, target 1.0-1.5 R, no chase, 1-minute steps 07:59-08:14), bias first. **When a trade is placed it is
   logged and the day ends: no bar after the entry minute is ever served, no result is computed** (`BLIND_LOG_FILTER.csv`). No-trade days as before.
2. **Claude** then reviews every logged trade from data up to the entry minute only (chart PNG to the last visible candle with his planned stop /
   target drawn, plus the noise, the session levels and the EMA12 states) and writes TAKE or SKIP, a confidence 1-3 and a one-line reason per trade to
   `CLAUDE_FILTER_CALLS.csv`, hashed before any outcome is computed. Claude does not compute or read any outcome of these days before the hash.
3. **Scoring** (`score_filter.py`, after the hash): every trade replayed on GC futures with the app convention (fill at the next minute's open one tick
   worse, stop exit one tick worse, target at its price, ties = stop, 17:00 close).

## Bar (single look)
**The filter works iff** mean R(TAKE) - mean R(SKIP) >= +0.20 AND a permutation P <= 0.05 (20,000 shuffles of the TAKE / SKIP labels over the
same trades) AND mean R(TAKE) > 0. Reported: the trader's mean R on all trades, on TAKE and on SKIP, wins, and the same split by confidence.
If either side has fewer than 8 trades the test is inconclusive. Prior: Claude's own blind reads (READ tests) were coin flips, so "not shown" is
the expected result; the test exists so that the filter has to earn trust before it is used live.

## RESULT (scored Mon 2026-10-26 21:23 local clock, after CLAUDE_FILTER_CALLS.csv was hashed at 21:22:21)
the trader played the 40 days 20:55-21:18 (about 30 seconds a day): 36 trades, 4 no-trade days. Claude: 20 TAKE, 16 SKIP.
Futures outcomes (`FILTER_RESULTS.csv`): ALL 36 trades 15 wins, mean R -0.178; **TAKE 20: 9 wins, -0.111 R; SKIP 16: 6 wins, -0.262 R;
TAKE - SKIP +0.151 R, permutation P 0.366, mean R(TAKE) < 0 -> NOT SHOWN.** Claude's filter does not separate winners from losers at a usable level.
