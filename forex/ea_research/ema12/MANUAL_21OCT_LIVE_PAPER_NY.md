# 21 Oct 2026, live TradingView paper trade, XAUUSD long (NY open + 14 min)

Written 14:5x local (local clock). Read-only: nothing was clicked on his TradingView. the trader: "check out the trade im in on trading view right now, its paper trading".
Position read at 14:47:43 (TradingView's own clock) while it was still open: `MANUAL_21OCT_LIVE_PAPER_1447_chart.png` (chart only), `MANUAL_21OCT_LIVE_PAPER_1448_full.png` (full window). It was stopped out in the 14:48 candle, about 3 minutes after the fill: `MANUAL_21OCT_LIVE_PAPER_1449_after.png` (14:49:01).

## The position (TradingView Paper Trading, OANDA:XAUUSD 1m, read from the chart and the account bar)
| item | value |
|---|---|
| side / size | Buy 740 oz (7.4 lots) |
| fill | 4136.600; marker sits on the 14:45 candle (inferred from the screenshot, the order time was not read) |
| stop | 4134.751 = 1.849 pts, -1,368.26 USD |
| target | 4141.953 = 5.353 pts, +3,961.22 USD, so 2.90 R from the fill |
| at 14:47:43 | bid 4137.570, unrealized +717.80 USD (+0.52 R), buy / sell 4137.970 / 4137.570 (spread 0.40 on TradingView) |
| paper account | balance 71,435.08, equity 72,152.88, realized +21,435.08, margin 30,618 (1:100) |

The drawn box (TradingView id `Pa0kLb`, long position tool) starts on the 14:44 candle with entry 4137.455 (the close of 14:44), stop 2.704 and target 4.498 away: it shows 1.66 R, but the stop and target prices equal the broker order's, so from the 4136.600 fill the real bracket is 1.849 / 5.353 = 2.90 R.

## Candle read (EMA 12 recomputed from the 40 bars read from TradingView; it matches TradingView's 4136.303 on the 14:46 bar)
- 14:43: EMA12 cross candle (opened 0.65 under, closed 1.31 over), body +1.96, upper wick 1.54 (0.79 of the body): fails "small close wick" and "body > sum of the wicks" (1.96 < 2.18).
- 14:44: body +0.54, wicks 0.31 / 0.56: not a strong accepted-next candle.
- 14:45: body +0.08, lower wick 2.46 (low 4134.99, 0.24 above the stop). The fill happened inside this candle, around the EMA12 (4136.2-4136.3), so it looks like a pullback buy at the EMA after the 14:43 cross, not a candle-close entry. Inferred, order type and time not read.
- The stop sits 0.004 under the 14:39 low (4134.755), but the 14:41 and 14:43 candles had already traded under it.

## Costs and odds of this bracket
- Spread 0.40 (TradingView) = 0.22 R of this stop; MT5 broker's gold spread 0.48 = 0.26 R. His logged stops have median 5.97 and minimum 1.66.
- In bid terms at the fill (bid about 4136.2) the stop is 1.45 away and the target 5.75: a random walk reaches the target first about 20% of the time, break-even is 25.6% (1 / (1 + 2.90)), so no-skill expectation is about -0.22 R per trade.
- On MT5 broker: 7.4 lots needs about 205K margin against the 3.1-lot cap; at this stop the cap is USD 573 of risk. For USD 100 risk the size would be 0.54 lots.

## Outcome (read at 14:49:01, after the screenshots above)
- Stopped out: the 14:48 candle ran 4136.91 -> 4132.73 (range 4.18, body -3.22; the nine candles before it had a median range of 2.29, the stop was 1.85). The paper broker closed at 4134.560 (marker "740 @ 4134.560"), 0.19 under the 4134.751 stop.
- Result -1,509.60 USD = 740 x -2.040, i.e. -1.10 R of the planned stop (balance 71,435.08 -> 69,925.48, realized PnL +21,435.08 -> +19,925.48).
- It was never near the target: the best price after the fill was 4138.085 (14:47 high), 3.87 short of 4141.953.

## Status for the logs
Not scorable anywhere: 14:44 is NY, the forward log is London 08:00-08:15 and starts Thu 22 Oct, the blind replay is a replay. It is a live, broker-stamped paper trade, so unlike the hindsight boxes the outcome is clean, but n = 1 says nothing about an edge (a bracket like this loses about 4 times in 5 even with no skill).
