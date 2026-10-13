# Pre-registration: Family CD, dip reversal in MT5 broker's crypto CFDs (written 2026-10-11 ~15:00, before any code or result)

Idea: the confirmed index dip-reversal (Round 286, 1990-2017, 8 of 8 indices; DIP_ADDON on MT5 broker) comes from forced / panic selling after a
fast multi-day fall. Crypto has the same mechanism in stronger form (liquidation cascades of leveraged perpetuals) and trades every day,
so it would give many more signals. Never tested here (crypto rounds were trend / TA / weekend / cross-section). Costs are large (median
spread 2025: BTC 6.5, XRP 8, BNB 13, ETH 14, ADA 28, SOL 30, BCH 31, LTC 45 bp), so only a large rebound can pay.

## Rule (the index rule, unchanged except the clock)
Daily decision at the 12:00 server minute (every day, crypto trades on weekends on MT5 broker). dec = bid close of that minute.
sigma60 = std of the last 60 daily returns of dec (min 40); z3 = ln(dec_t / dec_t-3) / (sigma60 x sqrt 3).
Entry at the open of the next minute at the ask (long) / bid (short); exit 24 hours later at the open of the same minute at the bid / ask;
stop 3 x sigma60 from the entry, checked on M1 bid lows (long) / ask highs (short), filled at min/max(stop, bar open).
Shorts' P&L = (entry - exit) / entry. Slippage 0.1 bp each side. Result in bp per trade; daily = mean over that day's trades.

## Variants (3, fixed now)
- CD1: LONG when z3 <= -2.0, all 8 coins (BTC, ETH, LTC, XRP, ADA, BCH, BNB, SOL).
- CD2: CD1 on BTC and ETH only (the liquid, cheap pair).
- CD3: SHORT when z3 >= +2.0, all 8 coins (does a crypto spike revert too?).

## Periods and acceptance
DEV 2022-01-01..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-09-30 (one look, only for passing variants).
Accept for the hold-out: DEV daily t >= 2.4, DEV mean > 0, VAL mean > 0, >= 60 DEV signal days.
Then for the account: correlation with the pair <= 0.3 and pass70 MIX uplift >= 3 points by 22 Dec with at most +1 point breach.
