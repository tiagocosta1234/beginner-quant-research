# Pre-registration BRK-EXITS (breakout day, round 1; written 2026-10-15 11:29 local (commit time), before any code or result)
Question: do breakouts need room to run? Fixed targets may cut the big winners that breakouts live on. Same entries, nine exits, plus a random-entry control that shows whether any exit can create an edge by itself (it should not).

## Entries (all 46 MT5 broker, data loaded to 2026-10-03)
Each market's main session as in BRK (`breakouts.session`: US indices and crypto NY 09:30-16:00, energy NY 09:00-14:30, DAX Frankfurt 09:00-17:30, NIKKEI Tokyo 09:00-15:00, ASX Sydney 10:00-16:00, FX and metals London 08:00-17:00). Box = chart (bid) high/low of the first 30 minutes; buy stop at the box high (ask reaches it; fill at the level or the minute's ask open if beyond), sell stop at the box low (bid); first fill wins (both in one minute = no trade); orders live until open + 3 h. R = |entry - box other side| (stop at the other side of the box); skipped if R < 2 spreads. Horizon: session close, capped at 22:55 server.
**Control:** the same market and day, a random minute inside the same order window, a random side, the same R distance, the same nine exits.

## Exits (stop at -1R in all of them until moved)
X1 target 1R. X2 target 2R. X3 target 3R. X4 no target (close at the session end). X5 breakeven: at +1R the stop moves to the entry, then session end. X6 trailing 1R behind the best price (from the previous minute's best). X7 trailing 2R behind the best price. X8 partial: half closed at +1R, the other half as X5. X9 time stop: if not at least +0.5R after 60 minutes, close; otherwise hold to the session end.
Stops on the executable side, stop first if stop and target in one minute, gapped stops at the open; net R with real bid/ask.

## Periods, statistics, gates
DEV 2022-01..2024-12, VAL 2025; 2026-01..10-02 reported as a non-clean look (already opened for breakouts). Daily portfolio mean R across markets, Newey-West t lag 1.
An exit "works" only if: 1. DEV mean >= +0.05 R and t >= 2.6 (Bonferroni 9); 2. VAL mean > 0 and t >= 1.65; 3. it beats the random-entry control with the same exit by at least 0.05 R in DEV and VAL. Reported: by class, by year, win rate, average winner and loser in R.

## Honest prior
About 5% that any exit turns the session breakout positive after costs; near 0% that an exit makes random entries profitable.
