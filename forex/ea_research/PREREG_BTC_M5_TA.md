# Pre-registration: classic technical analysis on 5-minute BTCUSD bars against MT5 broker's real costs (family C, 4 rules)

Written 2026-10-09 15:46 local (local clock), BEFORE any simulation of these rules. the trader (2026-10-09 ~15:45): "(original wording omitted)". The 1-minute version failed on cost (BTC_M1_TA_RESULT.md: gross +1..+6 bp, net -8..-12 bp, MT5 broker round trip about 12 bp). The lab budget is extended AGAIN by the trader's instruction: +4 variants (ledger 48), Bonferroni bar raised (daily t >= 2.6). Crypto stays RESEARCH-ONLY (memory 2026-10-02); nothing goes live without the trader's explicit go.
Cost facts (measured, not on any rule): median BTC spread 7.9 bp of the price, 5-minute return sd about 17 bp, 4-hour sd about 120 bp: at 5-minute bars with holds of hours the round trip (about 12 bp) is 10% of one 4-hour sigma instead of 100% of a 1-minute sigma. This is the fairest chance the intraday-TA idea gets.

## Common mechanics
Bars: M5 built from MT5 broker's BTCUSD+ M1 (bid o/h/l/c, ask o/h/l/c, mean spread), server clock, from 2022-04-01. Signal at the bid close of bar k, fill at the OPEN of bar k+1: long at the ask open x (1 + 2 bp), short at the bid open x (1 - 2 bp); no entry if the gap to the next bar exceeds 600 s. Exits fill on the opposite side with 2 bp slippage; stops checked intrabar (long: bid low <= stop, fill min(stop, bar bid open); short: ask high >= stop, fill max(stop, bar ask open)), stop first. One position at a time, no pyramiding, no martingale, no commission, swap-free.
Stop scale S = ATR48 x sqrt(48) (ATR48 = mean true range of the previous 48 M5 bars; S is about one 4-hour sigma, sized to the hold horizon from the start), measured from the bid-ask mid at the entry bar open (long: mid - k x S, short: mid + k x S).
- C1 Donchian breakout: long if the close is above the highest high of the previous 48 bars (4 h), short if below the lowest low; stop and trailing stop k = 1.5 (trailing from the highest bid close since entry for longs, lowest ask close for shorts, never loosened); time exit after 288 bars (24 h); cool-down 12 bars.
- C2 Bollinger overshoot fade: z = (close - SMA48) / SD48; long if z <= -2.5, short if z >= +2.5; exit at the open after z crosses 0, or after 36 bars; stop k = 2.0; cool-down 6 bars.
- C3 EMA(24)/EMA(96) trend: long on a cross up, short on a cross down; exit at the opposite cross but not before 24 bars; stop k = 2.0; cool-down 6 bars.
- C4 RSI(14, Wilder) extremes fade: long if RSI <= 20, short if RSI >= 80; exit when RSI crosses 50 or after 36 bars; stop k = 1.5; cool-down 6 bars.
Statistics: trades, win rate, mean net result per trade in bp (and gross of the two bar spreads, diagnostic), profit factor, daily-P&L t (sum of bp by close day over all calendar days with bars), share of trades held under 1 minute.
Periods: DEV 2022-04-01..2024-12-31, VAL 2025, POOL 2022-04..2025, HOLD-OUT 2026-01-01..2026-09-30 (one look, only for a rule that passes DEV and VAL).

## Acceptance (per rule; Bonferroni for 48 variants)
1. DEV: >= 300 trades, net mean > +3 bp, PF >= 1.10, daily t >= 2.6.
2. VAL 2025: net mean > 0, PF >= 1.05, daily t >= 1.0.
3. HOLD-OUT 2026: net mean > 0 (one look).
4. Gate before an MQL5 port or any use: share of trades under 1 minute <= 50%; the leg raises P(pass by 22 Dec) of the pair in the clean simulation with at most 1 point of extra breach and stays inside MT5 broker's 2.5% daily loss and 2% daily profit cap; validation on MT5 broker data in the tester; fixed lots, hard stop on every order, magic number, AccountGuard-compatible.
If no rule passes 1 and 2 the family is closed and NO EA is delivered.
## Honest prior
About 3%. Costs are tolerable at these horizons, but 1) the earlier BTC studies (daily trend, H1 pullback) found no durable edge, 2) crypto 24/7 trends are noisy and 3) four textbook rules on one asset leave little room. A pass would be the first non-gold edge; a fail closes BTC intraday TA (1 and 5 minutes).
