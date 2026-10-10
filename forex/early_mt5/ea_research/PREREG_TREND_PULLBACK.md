# Pre-registration: is "buy the dip in a trend" a general effect, or only the 5-minute EA's luck on gold? (family H, own rule, five markets)

Written 2026-10-09 ~10:35 local (local clock), BEFORE any simulation of this rule. Ledger at 37 of 40; this round is ONE registered trial (H1) plus its replication on four other markets (replication is part of the test, not extra trials); 2 trials stay in reserve. Why: the profile of the 5-minute EA's 1,614 trades (`ea_batch/mt5data/SIZING_LONG_RESULT.md` section 3) shows it is a trend-pullback follower: 81% of its entries go WITH the preceding 4-hour move, 74% go AGAINST the preceding 15-minute move, longs sit high in the 24-hour range, holds last a median 17 hours, and its yearly profit tracks gold's trend. If that structure is a real effect of trending markets, a plain rule built from exactly those three facts (not tuned on any result) should earn on gold and on other trending markets; if it earns only on gold, the pair's edge is gold's bull market and nothing new can be built from it.

## Rule H1 (parameters fixed now from the profile, no tuning)
Bars: M15 built from MT5 broker's M1 bars (server clock); the M15 ATR is the 14-bar average true range of the PREVIOUS 14 bars; the H1 ATR likewise. At the close of each M15 bar, if flat and not in the 4-bar cool-down after an exit:
- Trend: s = +1 if the close is above the close 16 bars (4 hours) earlier AND above the 96-bar (24 hours) simple average of M15 closes; s = -1 for the mirror image; otherwise no signal.
- Pullback: the bar's own return (close vs open) is against s by at least 0.5 x ATR(M15) (a counter-bar in the trend).
- Entry: at the next bar's open, in direction s (long at the ask = bid + the bar's spread, short at the bid), plus the instrument's slippage.
- Exit: initial stop 2.0 x ATR(H1) from the entry fill; chandelier trail updated at every M15 close: highest close since entry - 3.0 x ATR(H1) for a long (lowest close + 3.0 for a short), never loosened; time exit at the open after 96 M15 bars (24 hours); stop first when both fall inside one bar; stops fill with the slippage against us. One position at a time.
Slippage per market fill and stop exit (basis points of the price): gold 0.4, NSDQ 0.12, SP 0.12, BTC and ETH 2.0 (bars' own spreads are in the quotes). Swap-free account.
Statistics per market and period: trades, win rate, mean return per trade in bp of the entry price, profit factor, daily-P&L t-statistic (daily sum of the trades' returns on the day they close, zero otherwise, calendar days with bars), mean R.

## Markets and periods (fixed now)
Primary: `XAUUSD+` (MT5 broker gold M1, the market of the 5-minute EA). Replication: `NSDQ+`, `SP+`, `BTCUSD+`, `ETHUSD+`. DEV 2022-01-01 .. 2024-12-31 (crypto from its first valid day, 2022-04), VAL 2025, HOLD-OUT 2026-01-01 .. 2026-09-30 (one look, only for a passing H1).
## Acceptance (all must hold)
1. Gold DEV: >= 150 trades, mean return per trade > 0, profit factor >= 1.10, daily t >= 2.0; gold VAL: mean > 0 and profit factor >= 1.05.
2. Replication (DEV and VAL pooled 2022-2025 per market): mean return > 0 on at least THREE of the four other markets and daily t >= 1.0 on at least TWO of them.
3. Gold HOLD-OUT 2026: mean > 0 (one look).
4. Gate for any use: correlation of the daily P&L on gold with the pair's <= 0.20 does NOT have to hold for non-gold markets (they are different exposures); for a non-gold market that passes 2, the leg is portfolio-fitted exactly as in `PREREG_JJSIM_NQ_SESSIONS.md`.
If 1 fails the idea is closed (no replication read, no hold-out); if 1 holds and 2 fails, the effect is gold-specific (reported as such).
## Honest prior
Low to moderate. Pullback-in-trend rules are textbook, the Donchian trend leg on gold earned zero after costs, and the 5-minute EA's own 2022-24 profit was small (-152 / +675 / +1,782 USD a year at 0.01 lot), so a plain version may find only the bull years; but a pass on three markets would be the first independent evidence that part of the pair's edge is general.
