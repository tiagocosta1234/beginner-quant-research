# Pre-registration: strategy factory for the 70%-this-month goal (family F, one selection procedure)

Written 2026-10-10 (local clock in the commit), BEFORE any run. the trader: "you need to develop a strategy strong enough to achieve the goal, even if it requires dumping the current strategy". Spec (Update 85): about 500-600 USD a day on the 100K account with a daily Sharpe of 0.5-0.85, alone or replacing the pair.

## Search space (fixed now)
Markets (MT5 broker M1 mid bars): XAUUSD, NSDQ, SP, DOW, DAX, EURUSD, GBPUSD, USDJPY. Timeframes M15 and H1 (bars built from server-clock minutes; decisions at bar close, executed at the next bar's close mid, cost = the market's median quoted spread + 0.2 bp per side).
Rule families, long and short, position held until the opposite signal or a flat condition, forced flat 21:45-01:15 server (no rollover exposure) and on Fridays from 21:00:
- D Donchian breakout: N in {10, 20, 50, 100}, exit on the opposite N/2 channel.
- M moving-average trend: fast/slow EMA in {(10,50), (20,100), (50,200)}.
- R RSI(14) reversion: enter at {20/80, 25/75, 30/70}, exit at 50.
- B Bollinger reversion: N in {20, 50}, k in {2.0, 2.5}, exit at the mean.
- O session momentum: sign of the return since the server-day open after h in {2, 4, 6} hours, held to 21:45.
Each variant sized at a fixed notional giving 1% of the account per 1 ATR(14) move (MT5 broker's 1%-per-idea guideline).

## Selection and validation
DEV 2022-24: daily Sharpe of each variant's net USD P&L. The top 20 variants by DEV daily Sharpe (with DEV daily t >= 2) go to VAL 2025; a variant survives VAL if its 2025 daily Sharpe > 0. Survivors form an equal-weight portfolio (each scaled so that the portfolio's DEV daily sd stays <= 900 USD and every component <= 1% risk). The portfolio is opened ONCE on the 2026 hold-out (Jan-Sep).
Multiple testing: the number of variants is reported; the DEV Sharpe of the best variant is compared with the maximum DEV Sharpe of the same search run on 200 sign-randomised copies of each variant's daily P&L (a reality-check null).
Goal acceptance: on the hold-out the portfolio must show a daily mean >= 500 USD and daily Sharpe >= 0.5, and then the clean simulation must give P(pass by 30 Oct) >= 70% from Monday 12 Oct; anything weaker is reported, not deployed.

## Honest prior
Well under 1% for the goal: the search space is the same kind of price rules that failed all week, at 1% risk per idea a single rule earns tens of USD a day, and a daily Sharpe of 0.5 is about 8 annualised. It is run because the trader asked for the strongest possible attempt and because the reality-check null will show how much of any good-looking DEV number is selection luck.
