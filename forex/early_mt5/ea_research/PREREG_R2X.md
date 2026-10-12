# Pre-registration: the daily RSI(2) dip rule on more markets (family R2X) (written 2026-10-12, before the rule was run on any of these markets)

the trader: "(original wording omitted)". The one confirmed edge outside gold is daily short-term dip buying in US indices (RSI(2) dips SP/NSDQ/DOW: MT5 broker hold-out 2025-26 PF 6.0, 35 distinct days, t 5.4; `FINCEPT_mt5_RESULT.md`). Faster bars killed it (ID family), more US indices are not available, so breadth has to come from the other markets where the same mechanism could live. Rule UNCHANGED from EV1 (no re-tuning), now at each market's own daily close.

## Rule (EV1, long only)
Daily price = bid-open of the last cash-session minute of the market, ask-open for the same minute on entry: DAX 17:29 Europe/Berlin; NIKKEI 14:59 Asia/Tokyo; ASX 15:59 Australia/Sydney; BTCUSD and ETHUSD 23:59 UTC (24/7 markets: the UTC day). Wilder RSI(2) < 10 AND close > SMA(200 days): buy at that close (ask); exit at a later close (bid) when close > SMA(5) OR RSI(2) > 70 OR 5 days held. One position per market. Return in bp, spread paid on both fills, no other cost. MT5 broker M1 bid/ask, swap-free, 2021-12 onward (SMA(200) means signals start about 2022-10).
## Trials (2)
- R2X1 index dips on DAX + NIKKEI + ASX (the three MT5 broker indices outside the US block).
- R2X2 crypto dips on BTCUSD + ETHUSD (the two lowest spreads: 8 and 18 bp median).
Markets of a trial are averaged per entry day.

## Windows and acceptance (by entry date)
DEV 2022-01-01 .. 2024-12-31, VAL 2025, HOLD-OUT 2026-01-01 .. 2026-09-30 (one look, accepted trials only).
Accept: DEV >= 30 day-observations, mean >= +30 bp, PF(day) >= 1.3, one-sided t >= 1.65; VAL mean > 0; HOLD mean > 0.
Reported: trades per year; overlap of entry days with the US RSI(2) days and with ManualDip's signal days (independence); indicative Sharpe at 25,000 USD per trade, alone and pooled with the US block (breadth effect).
A pass is a candidate only (EA with a server-side stop, MT5 broker tester, correlation with the pair, pass-speed gate). Nothing goes live from this round.

## Honest prior
R2X1 moderate: the dip effect is documented in most equity indices, but the MT5 broker DAX and NIKKEI ran negative in every 4 h version tried (DAX -9 / -8 bp, NIKKEI mixed), so it may be an US-only effect. R2X2 low to moderate: crypto dips were a noisy positive earlier (CD1/CD2) and the spreads of BTC and ETH are small against a multi-day hold. Even a pass adds a few dozen entry days a year, far short of the Sharpe 6 a 30-day pass needs; it is a leg, not the system.
