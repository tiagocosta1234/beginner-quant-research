# PREREG_BEST3M_CYCLE - an MT5 broker evaluation trading every symbol's best recent breakout at the same time (written 2026-10-15 local clock 17:53, before any P&L of this simulation)
the trader: "simula a evaluation cycle where it looks for all those best setups at the same time".

## Trades
The ORB11_ENTRY trade table (D:/finance/si_ledgers/ORB11_ENTRY.parquet, MT5 broker M1 bid/ask, spreads paid, 46 symbols, 144 rules per symbol without FADE: 2 sessions x 5 triggers x 6 filters x 2 exits). Risk per trade X USD (stop = X): P&L = R x X. Sizes X = 100, 200, 300 USD.

## Two versions
- A IN-SAMPLE (what the table shows): the per-symbol best rule of 2026-07-03..10-02 (best3m_lookup.py), traded over that same period, one cycle starting 2026-07-03. Not causal: reported only to show what the look-back table promises.
- B CAUSAL WALK-FORWARD: at the start of every calendar month M (2022-03..2026-10), for each symbol choose the rule with the highest total R over the three previous calendar months (at least 15 trades, total > 0; only trades whose day is before M); trade those rules during month M. Cycles start every 5th business day from 2022-03-01 to 2026-08-31 and run until pass, breach or the end of the data (2026-10-02).

## MT5 broker Pro rules
100,000 start, pass when the counted balance reaches 108,000 (then stop: pass lock), floor 92,000 static, daily loss 2,500 from the day-start balance (hard breach), profit counted at most +2,000 a day. All trades close inside their session, so the account is flat overnight. Intraday paths are not stored, so the daily line is checked two ways: OPTIMISTIC (the day's net P&L) and PESSIMISTIC (the sum of the day's losing trades, i.e. every loser happens before any winner). The truth lies between.

## Outputs
B: pass and breach rates within 30 and 60 calendar days and by the data end, median days to pass, by start year; A: the single cycle's days to pass and worst day. No acceptance bar: this is a simulation of a policy that already failed its walk-forward test in ORB11_ENTRY; it answers the trader's question only.
