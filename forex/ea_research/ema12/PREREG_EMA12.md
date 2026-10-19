# PREREG_EMA12: mechanical version of the trader's "12 EMA at the session open" on MT5 broker gold and Nasdaq (2022-2026)

Written 2026-10-19 (local clock, main PC) BEFORE any P&L of this test was computed. the trader asked: "verify if the 12 ema would have worked in gold and the nasdaq".
His exact rule is not written down; this is the version inferred from his 30 gold trades (`infer_rule.py` on `replay_mt5.csv`): entries come in the first
15 minutes after the session open (median 3), at the moment the 1-minute price crosses its EMA12 (77% already on the trade side, median 1 minute after the cross);
the target is always 0.525 R of the stop; the stop is NOT a simple function of one indicator (median 2.5 x the 1-minute ATR14, range 1.3-6.5). So the stop
and the reward ratio are the two free choices; they are tested as a small registered grid, nothing else is tuned.

## Rule (all on MT5 broker M1 bid/ask, server clock = Europe/Athens, EMA12 of 1-minute mid closes over the whole series)
- Sessions: London = 08:00 Europe/London, NY = 09:30 America/New_York, converted to the server clock per day. One trade per market, session and day.
- Signal bar t = first 1-minute bar with open offset 0..14 whose mid close is on the other side of the EMA12 than the previous bar's close. Long on a cross up, short on a cross down.
- Entry at the open of bar t+1: ask for longs, bid for shorts (real spread). No trade if there is no cross in the window.
- Stop (risk R in price units): ATR25 = 2.5 x mean(1-minute mid range of the last 14 bars up to t); SW15 = distance to the lowest low (longs) / highest high (shorts) of the last 15 bars up to t, at least 1 x ATR14.
- Target = r x R with r in {0.525, 1.0}. Exits on the real side of the book (long: bid; short: ask). If both levels fall in one bar the stop counts. Time exit after 60 bars at the close (bid/ask side).
- R of a trade = (exit - entry) / R, signed. Win = target hit.
- Zero-spread minutes (sp <= 0, under 1%) get the market's median spread of that year.

## Trials: 16 (2 markets x 2 sessions x 2 stops x 2 reward ratios): XAUUSD and NSDQ, London and NY, ATR25 / SW15, r 0.525 / 1.0.
Periods: DEV 2022-01-01..2024-12-31, VAL 2025, HOLD 2026-01-01..: HOLD is not computed in the default run; it is opened once, only for a trial that passes DEV and VAL.
## Acceptance (Bonferroni over 16 trials, two-sided 0.05 -> |t| >= 2.96)
A trial is a candidate only if DEV: n >= 300, mean R >= +0.05 and t >= 2.96; AND VAL 2025: mean R > 0 with t >= 1.65. Otherwise it fails. A candidate then gets ONE look at 2026.
Descriptive extras (not acceptance): by year, by direction, the share of the trader's 30 session-days on which the gold rule fires in his direction.
## Honest prior
Low, about 5-10% that one of the 16 passes. Reasons: the trader's 30 trades give +0.22 R (t 1.93) in four weeks of one regime; the reel-17 version (first 5-minute candle vs EMA12, trailing stop)
failed on NSDQ (0 of 4, `REELS_16_17_RESULT.md`); the LEO EMA pullback on SP/NSDQ/DOW had a gross edge of about zero (`LEO_EMA_PULLBACK_RESULT.md`). A fail here means the
MECHANICAL version has no edge; it does not prove his discretionary trades have none.

## Amendment 1 (2026-10-19, written after the dry-run and BEFORE any P&L of this test was computed)
Reason: the dry-run showed that the first-cross rule fires on 28 of the trader's 30 gold session-days but in HIS direction on only 14 (a coin flip), while his direction agrees with the sign of
the move over the previous 30 minutes on 23 of 30 (against it: 11 of 30), with the move since the session open on 23 of 30 (`infer_direction.py`, descriptive, no P&L). His trades follow
short-term momentum. Changes:
1. A direction filter is added as a second registered family: F0 = as registered; F30 = only a cross in the direction of sign(mid[t] - mid[t-30]) counts (the first such cross in the
   0..14 window). Trials become 32 (2 markets x 2 sessions x 2 stops x 2 reward ratios x 2 filters); Bonferroni two-sided 0.05 / 32 -> |t| >= 3.16 for DEV.
2. DEV starts 2022-01-01 (the code first also included the 18 + 21 + ... stub days of December 2021; no P&L was looked at).
3. Caveat written now: the trader's 30 trades are April-May 2025, i.e. inside VAL; choosing F30 from them makes VAL not independent for the F30 trials. For F30 the acceptance rests on DEV and
   the 2026 hold-out; VAL > 0 is still required but proves little.
Acceptance otherwise unchanged (n >= 300, mean R >= +0.05, t >= 3.16, VAL mean R > 0 and t >= 1.65, then one look at 2026).
