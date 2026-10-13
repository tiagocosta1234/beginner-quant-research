# Pre-registration: automate JJ Simon's "6 PM and 8 PM session" setup on MT5 broker's Nasdaq CFD and test it on an MT5 broker Pro 100K

Written 2026-10-09 ~00:40 local (the NSDQ data export finished 00:37, nothing has been simulated yet), BEFORE any result. Requested by the trader ("(original wording omitted)") after `/watch` of https://www.youtube.com/watch?v=BLvsYJ4sqn8 (channel JJ Simon, "The ONE Setup That Made Me $400,000 in 90 Days (6 & 8PM Session)", 30:34, uploaded 2026-09-17; transcript and frames in `D:\finance\tmp\watch\BLvsYJ4sqn8`). The video is a month of hand-picked, narrated FX-Replay examples on E-mini Nasdaq futures (NQ, 1-minute chart, 1 contract); the presenter says himself that a month is no sample and that his real win rate at 1.5R is "much lower"; the "$400k in 90 days" is an unverifiable claim. Nothing here is believed until the numbers below say so (campaign rule: narrated examples are chosen with hindsight).

## What the video says (the source of every rule)
- Two sessions per evening, New York time: 18:00 (Globex open) and 20:00 (Asian open). The open of the 18:00 session is "fair price"; per session ONE continuation (in the direction of the opening candle, in the first 5 minutes, not away from an opening gap, with the higher-time-frame bias = price vs the 09:30 open of that day) and reversions toward fair price after an "unfair move" of at least 30 points.
- Entry: a displacement candle (body larger than the previous candle's body AND close beyond the previous candle's wick) or a break of structure. Standardised exits: take profit 38 points ($750 on NQ), stop 25 points ($500), 1.5R ("do not copy these numbers"). Exit at break-even when a new session opens. Trade 90 minutes after the 20:00 open (until 21:30), nothing afterwards. At 20:00 fair price becomes the Asian open unless the first move goes straight back toward the 18:00 open.

## Instrument and clock on MT5 broker
- MT5 broker Pro Classic Markets Nasdaq CFD `NSDQ+` (contract 5: 1 lot = 5 USD per index point, tick 0.01, min 0.01, max 50 lots; 1 lot = 1/4 of one NQ contract; 4 lots = 20 USD per point = one NQ). Trading hours 01:05-23:55 server time (closed 23:55-01:05 = 16:55-18:05 New York).
- MT5 broker server clock = New York + 7 hours all year (EEST/US-DST aligned). New York 18:00 = server 01:00, 20:00 = 03:00, 21:30 = 04:30, 22:00 = 05:00, 09:30 = 16:30. All evening trades fall on ONE server day, the same day for MT5 broker's 00:00-server daily reset.
- Data: MT5 broker's own M1 bars exported with `forex/ea_batch/mt5data_m1_export.py` (bid OHLC + bar spread; ask = bid + spread) for 2021-12-01 .. 2026-10-08, file `forex/data_mt5/NSDQ_M1_rates.parquet` (not committed). The account bought is "No Commissions": costs are inside the spread, which is the bar spread of this very account's feed.

## Formalisation (every discretionary element resolved BEFORE running; elements that cannot be automated are dropped, not guessed)
Evenings: New York dates Sunday-Thursday (the Friday evening market is closed), 18:00-22:00 NY.
- **Fair price F1** = bid open of the first bar at or after 18:00 NY (must be before 18:30, else the evening is skipped). Prior close = bid close of the last bar before that bar. Gap g = F1 - prior close. O930 = bid open of the 09:30 NY bar of the latest weekday on or before the evening's date. Bias = sign(F1 - O930).
- **6 PM continuation (at most one per evening):** direction d = sign(close - open) of the first bar (zero = no trade). Skip if bias != d, or if d>0 and g > +10 points, or d<0 and g < -10 points. Market entry at the open of the SECOND bar.
- **Asian fair price F2** (decided at the close of the 20:04 bar, no look-ahead): if sign(close_2004 - open_2000) == sign(F1 - open_2000) (the first move went toward the 18:00 open) fair stays F1, else fair = open of the 20:00 bar.
- **Asian continuation (at most one per evening):** d = sign(close - open) of the 20:00 bar; no bias or gap filter; market entry at the open of the 20:01 bar.
- **Reversion (up to 3 entries per session, 6 PM and Asian counted separately; evaluated at the close of every bar from the 6th bar of the 18:00 session / from the 20:05 bar of the Asian session):** LONG when fair - close >= 30 points and the bar is a bullish displacement (close > open, body > previous body, close > previous bar's high); SHORT when close - fair >= 30 and the bar is a bearish displacement (close < open, body > previous body, close < previous bar's low). Entry at the next bar's open. Fair = F1 until 20:05 and F2 afterwards.
- **One position at a time; no new entry at or after 20:00 for the 6 PM session, at or after 21:30 for the Asian session.** Take profit +38 points, stop -25 points from the fill price. At the start of the 20:00 bar the stop of any open position moves to its entry price (break-even). Any position still open at 22:00 NY is closed at that bar's open.
- Dropped (not automatable without guessing): break-of-structure confirmation, "get out early if the unfair move is not happening", layering several positions, discretionary sizing, news. No news filter is applied (the window 18:00-22:00 NY carries few releases; news trading is outside our standing rules anyway).

## Costs (the same rules for every variant)
Buy at the ask (bid + the bar's spread), sell at the bid; long take profit when the bid high reaches the level, long stop when the bid low reaches it; short take profit when the ask low (= bid low + spread) reaches it, short stop when the ask high reaches it; if both levels lie inside one bar the STOP is assumed first; stops and market exits fill 0.3 point worse; entries 0.3 point worse; no commission (No Commissions account). P&L in points; dollars = points x 5 x lots.

## Periods (fixed now)
DEV 2022-01-01 .. 2024-12-31, VAL 2025-01-01 .. 2025-12-31, HOLD-OUT 2026-01-01 .. 2026-09-30 (opened ONCE, only for the single configuration that passes DEV and VAL), Dec 2021 = warm-up and mechanics smoke test only.

## Trials (all counted in `forex/ea_research/LEDGER.csv`; only T1 can be accepted)
T1 PRIMARY: exactly the rules above. Sensitivities / decompositions, each run once on DEV and VAL: T2 TP 25 / SL 25; T3 TP 50 / SL 25; T4 TP 38 / SL 38; T5 entries need a close beyond the previous 10-bar extreme as well (structure break); T6 continuation entries only; T7 reversion entries only; T8 6 PM session only; T9 Asian session only; T10 unfair-move threshold 20; T11 threshold 40; T12 no break-even move at 20:00. 12 trials in total, no more before the hold-out.

## Acceptance of T1 (all must hold)
1. DEV: >= 300 trades, net expectancy per trade > 0 after costs, profit factor >= 1.15, t-statistic of the evening P&L (mean / (sd / sqrt(n_evenings))) >= 2.0.
2. VAL: >= 100 trades, net expectancy > 0, profit factor >= 1.10, evening t >= 1.0.
3. Robustness: at least 7 of the other 11 trials have net P&L > 0 on DEV.
4. HOLD-OUT 2026 (one look): net P&L > 0 and profit factor >= 1.10.
If T1 fails 1-3 but another trial has DEV evening t >= 2.64 (Bonferroni for 12) and VAL net > 0, it is only a candidate for a second pre-registered round, never accepted; the hold-out is not opened for it.

## Amendment 1 (2026-10-09 ~01:25 local): inversion, written after the T1-T12 verdict and BEFORE any inverted run
the trader: "tenta inverter". Two further trials, run once each on DEV and VAL: **I1** = the T1 signal exactly as registered (all filters, entries, attempt limits computed from the original direction), then the order direction FLIPPED, same bracket TP 38 / SL 25; **I2** = flipped and the bracket swapped, TP 25 / SL 38 (the exact mirror of T1's price paths before costs). 14 trials in total.
- Honesty about the choice: inversion was chosen AFTER T1-T12 all lost in DEV and VAL, so DEV and VAL are no longer clean for these trials; they count as searched. Acceptance therefore uses the Bonferroni bar for 14 trials: DEV evening t >= 2.69 (not 2.0), DEV >= 300 trades, PF >= 1.15, expectancy > 0; VAL net > 0, PF >= 1.10, evening t >= 1.0. The 2026 hold-out stays unopened and is the only clean look: it is opened once, only for an inversion that passes both periods.
- Expectation written before running: the zero-cost diagnostic of T1 was DEV expectancy -0.28 points a trade and VAL +1.04 against about 2.0 points of cost per trade, so the mirror starts near +0.3 gross minus 2.0 of cost in DEV; a pass is very unlikely.

## MT5 broker test (only if T1 or an inversion is accepted)
(a) Stand-alone on the MT5 broker Pro 100K rules (8% target with the 2% a day counted, 2.5% daily hard breach, 8% static floor, our 2.0% daily cap, swap-free): 4 lots (25 points = 500 USD = 0.5% risk) and 2 lots (0.25%), every start day of 2022-26: pass %, breach %, median days, pass within 42 / 62 business days. (b) Portfolio fit with the gold pair at the locked test lots (SDB 0.12 + 5-minute EA 0.04, MT5 broker-based 2022-26 daily series, swap-free): correlation of the daily P&L, overlap on the pair's 10 worst days, combined pass and breach with the 2.0% cap on the SUM of the daily lows (pessimistic: assumes the lows coincide). Gate: P(pass within 62 bd) up by >= 5 points with breach <= 5%, and breach not worse than the pair alone.
(c) Only then an MQL5 EA (fixed lots, hard stop and target on every order, IOC fills, magic number, AccountGuard-compatible), validated against the Python trades (>= 90% of trades match) in the MT5 broker portable tester; nothing goes near the live account without the trader's go.

## Honest prior
Low. Opening-range style session rules on index CFDs usually lose their edge to spread and slippage, the 38/25 numbers are the presenter's own "do not copy" demo values, and a 1.5R target at his admitted "much lower" win rate needs about 40% wins plus costs. The test is still worth running because the 6 PM/8 PM window is far from the gold pair's loss days and MT5 broker charges the Nasdaq a tight spread.
