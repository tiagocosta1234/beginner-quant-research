# Pre-registration BRK-DONCH (breakout day, round 21; written 2026-10-15 12:47 local (commit time), before any code or result)
Intraday Donchian (turtle) breakouts on all 46 MT5 broker, inside each market's main session (round 1 sessions). Bars built from MT5 broker M1 bid/ask on the session clock: M15 and H1 (mid OHLC for channels and ATR, executable prices for fills and exits).
Entry: during the session, the first bar whose mid HIGH exceeds the highest high of the previous N bars (long) or whose mid LOW goes below the lowest low (short), at most one position at a time per market and cell, entries until 2 hours before the session close; the fill = the stop order at the channel level (ask for longs, bid for shorts; at the bar's executable open if it gaps beyond).
Stop: 2 x ATR14 of the bar timeframe at the entry. Exit: the turtle exit = an opposite break of the N/2-bar channel (bar close beyond it -> exit at the next bar's executable open), the stop, or the session close (capped 22:55 server). R = 2 ATR.
Channels may include bars from earlier sessions of the same market (overnight history), never bars after the entry.
Cells (4): M15 N=20, M15 N=55, H1 N=20, H1 N=55.
Gates (DEV 2022-24, VAL 2025, 2026 non-clean): DEV mean >= +0.05 R and t >= 2.5 (daily NW lag 1; Bonferroni 4); VAL mean > 0 and t >= 1.65. Classes reported.
Honest prior: about 4% (UT Bot ATR-trailing breakouts on every symbol x 8 timeframes found nothing beyond noise).
