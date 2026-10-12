# Pre-registration: trend on 18 markets (TS), index pairs (PI), cross-market lead-lag (LL) (written 2026-10-12, before any return was computed)

the trader: "testa as três" (ideas 3, 4, 5 from the list after NEW_EAS). MT5 broker M1 bid/ask (`data_mt5`, 2021-12-01 .. 2026-10-02, swap-free), spread paid on every fill, rules as in the literature, one parameter set each.

## TS: time-series momentum (Moskowitz-Ooi-Pedersen 2012)
18 markets: XAUUSD, XAGUSD, WTI, BRENT, SP, NSDQ, DOW, DAX, NIKKEI, EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD, BTCUSD, ETHUSD. Daily price = 15:59 New York bid-open, on the SP trading-day calendar (other markets forward-filled). Monthly rebalance on the first trading day of each month: position = sign(252-day return) x min(10% annual vol target / (60-day daily sd x sqrt 252), 3) / number of markets, held until the next rebalance; cost at each rebalance = |weight change| x half the 15:59 spread. Portfolio return in % of NAV.
Because a 252-day lookback uses the first year of data, DEV = 2023-01-01 .. 2024-12-31 (shorter than the other families; declared). Accept: DEV annualised Sharpe >= 0.5 AND positive in both DEV years; VAL 2025 mean daily return > 0; HOLD 2026 > 0.

## PI: index pair reversion
Pairs (NSDQ, SP), (SP, DOW), (NSDQ, DOW), same machinery as the GS test: z-score of ln(A/B) over the last 60 trading days, enter at |z| >= 2.0 (short the rich index, long the cheap one, dollar-neutral), exit at |z| <= 0.5 or after 20 trading days, one position per pair, 15:59 NY bid-open prices, ask/bid on all four fills. Return in bp of one leg's notional. The three pairs are pooled (their trades overlap in time and are correlated, so t is optimistic).
Accept: DEV 2022-24 pooled >= 25 trades, mean >= +8 bp, t >= 1.65; VAL mean > 0; HOLD mean > 0.

## LL: lead-lag with hours on the server clock (Athens = Berlin + 1 h all year)
- LL1: DAX return from 10:00 to 18:30 server (cash session 09:00-17:30 Berlin) predicts SP, NSDQ, DOW from 18:30 server to 15:59 NY: long if positive, short if negative, long at ask / short at bid in, bid / ask out, the three indices averaged per day.
- LL2: NIKKEI return from 03:05 to 07:55 server (most of the Tokyo session) predicts DAX from 10:00 to 18:25 server, same sign rule.
Accept (each): DEV 2022-24 mean >= +2.0 bp/day and t >= 2.0; VAL mean > 0; HOLD mean > 0. Days without a bar at a required minute are skipped.

## Honest prior
TS: moderate that it is positive over 2023-26 (gold and oil trends, USDJPY), low that DEV clears 0.5 Sharpe honestly with 2 years; it is slow and cannot speed up an MT5 broker pass, it would only diversify away from gold. PI: low (spreads between correlated indices are tiny against 1-2 bp costs). LL: low (information is priced in minutes; documented effects are older). Trials TS, PI, LL1, LL2 (DEV, VAL). Nothing goes live from this round.
