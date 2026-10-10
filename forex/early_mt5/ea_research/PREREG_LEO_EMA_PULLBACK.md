# Pre-registration: the LeoTrades US500 morning pullback setup, formalized (family L, one rule, three indices)

Written 2026-10-09 16:27 local (local clock), BEFORE any simulation of this rule. the trader ("testa", after the /watch of https://www.youtube.com/watch?v=qBC2gvi5FIM, MT5 broker $200K test episode 2, Dec 2022). Ledger 51 before this trial; this is trial 52 (a further +1 amendment by the trader's instruction); Bonferroni bar: daily t >= 2.5.
What was read from the video (1080p frames, position tables): US500.cash, 300 contracts; first two positions at 1:1 (stop 6.75-6.9 points, target the same distance) later tighter stops 3.3-3.4 points with targets 1:1 or 1:2; entries on a pullback to the 20 EMA of the M1 chart with the M5 20 EMA as bias (down-trend below it, a V-reversal through it for the long); two positions, first closed at the target, stop of the second moved to breakeven; "My Rules": max risk per trade 1%, max daily loss 2%, no trading before 6:35 and after 9:00 (read as Pacific time = 09:35-12:00 New York, the first 2.5 hours of the US cash session). The discretionary part (reading the candle: 'looks strong / weak') cannot be coded; this registration replaces it by the plain mechanical version below. A fail therefore says the MECHANICAL version has no edge, not that his discretion has none.

## Rule E1 (fixed now, no tuning)
Instruments: SP+ (the market he trades), NSDQ+ and DOW+ as replication (MT5 broker M1 bid/ask bars; pooled, equal weight). Clock: MT5 broker server time (Europe/Athens) converted to New York with the real time zones. Window: signal bars from 09:35 to 11:58 New York; every position still open is flattened at the open of the 12:00 New York bar.
Bias (known at the bar's close, no look-ahead): EMA(20) of M5 bid closes (M5 built from M1), using only COMPLETED M5 bars (the previous completed block): bias = +1 if the last completed M5 close > its EMA20 AND EMA20 > EMA20 three M5 bars earlier; bias = -1 for the mirror image; otherwise no trade.
Trigger on each M1 bar close (EMA(20) of M1 bid closes): LONG if bias = +1, the bar's bid low <= EMA20(M1) and the bar's bid close > EMA20(M1) (touch and bounce); SHORT if bias = -1, the bar's bid high >= EMA20(M1) and the bar's bid close < EMA20(M1). One position at a time, at most 2 trades per instrument per day.
Entry at the OPEN of the next M1 bar (long at the ask, short at the bid) with 0.12 bp slippage. R = 0.10% of the entry price. Two legs of half a unit each: leg A target = entry + 1 R (long; mirror for short, on the bid for longs / ask for shorts), leg B target = entry + 2 R; both legs share the stop at entry - 1 R; when leg A hits its target the stop of leg B moves to the entry price from the NEXT M1 bar. Stops checked first inside a bar on bid low / ask high (long: bid low <= stop, fill min(stop, bar bid open) minus 0.12 bp; short: ask high >= stop, fill max(stop, bar ask open) plus 0.12 bp); targets fill at the target price (limit orders). Trade result R = mean of the two legs' P&L / R.
Statistics: trades, win rate, mean R per trade, profit factor on R, mean net bp, pooled daily t (daily mean R of the three instruments over days with at least one trade), mean R per instrument, share of trades by exit type.
Periods: DEV 2022-01-01..2024-12-31, VAL 2025, POOL 2022-2025, HOLD-OUT 2026-01-01..2026-09-30 (one look, only if DEV and VAL pass).

## Acceptance (Bonferroni, 52 variants)
1. DEV pooled: >= 500 trades, mean R > +0.05, profit factor >= 1.10, daily t >= 2.5, mean R > 0 on at least 2 of the 3 instruments.
2. VAL 2025 pooled: mean R > 0, profit factor >= 1.05, daily t >= 1.0.
3. HOLD-OUT 2026 pooled: mean R > 0 (one look).
4. Gate for any use: it is a morning index scalp with a 0.1% stop: correlation with the gold pair <= 0.2; in the clean simulation the leg raises P(pass by 22 Dec) with at most 1 point of extra breach; execution on MT5 broker data in the tester; fixed lots, hard stops, AccountGuard-compatible.
If 1 fails the idea is closed (no hold-out).

## Honest prior
About 3%. A 1:1 / 1:2 scalp with a 0.1% stop and costs of roughly 0.1 R per trade (spread 0.75 bp + slippage against a 10 bp stop) needs a real directional edge of a few percent per trade; the earlier index tests (intraday momentum, trend-pullback on M15) found none, and a 3-day sample of discretionary trades (5 entries) is no evidence.
