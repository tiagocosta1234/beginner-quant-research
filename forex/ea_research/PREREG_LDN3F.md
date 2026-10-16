# PREREG LDN3F - London breakout with three entry filters, FORWARD test only

Registered 2026-10-16 ~17:15 local (local clock). Requested by the trader ("regista o teste").

## Where the idea comes from (and why history cannot confirm it)
`ldn_features.py` (descriptive, 2026-10-16) split 45,246 London 30-min breakouts (38 markets, 2022-01..2026-10-02) by
twelve entry-time features. Three looked consistent in 2022-24, 2025 and 2026; their combination made
+0.019R (t 0.7) / +0.119R (t 1.9) / +0.081R (t 1.2) per trade after the real spread. The filters were chosen AFTER
seeing all three periods, so every historical number is in-sample. The only honest test left is forward data.

## The rule (fixed; nothing may be tuned during the test)
Markets: the 38 non-crypto MT5 broker (same list as ORBX/BRK2). Clock: local (server = local + 2 h).
1. Box = bid high/low of 08:00-08:30. Spread = median (ask - bid) of the box minutes.
2. First trigger between 08:30 and 10:00: buy stop at box high (fills when ASK reaches it), sell stop at box low
   (fills when BID reaches it). SL = other side of the box; TP = 1 box beyond the entry (1:1); close 17:00.
3. Take the trade only if ALL three hold:
   - F1 box / spread >= 33.3 (spread <= 3% of the box);
   - F2 the trigger minute is more than 8 minutes after 08:30 (08:39 or later);
   - F3 side x (close of day-1 - close of day-6) / ATR20 < 0.59, i.e. NOT a breakout in the direction of a strong
     5-day move (ATR20 = mean daily high-low of the previous 20 days; mid prices; daily = server day).
4. One trade per market per day. Same-minute TP+SL = SL; on the entry bar only the SL counts.

## Forward data and measurement
- Period: from Monday 2026-10-19. Data: M1 rates read-only from the MT5 broker terminal (`ldn3f_forward.py`, MetaTrader5
  API: initialize, symbols_get, copy_rates_range, shutdown only). Ask = bid + bar spread x point (copy_rates gives bid
  OHLC and a bar spread; this approximates the tick-based ask used in the backtests - stated in advance).
- Also logged: the unfiltered base rule on the same days (yardstick).
- Paper only. No live money on this rule before it passes.

## Decision
- Final read when the filtered rule has >= 150 forward trades (expected about April 2027 at ~24 a month).
- PASS: mean net R > 0, day-clustered t >= 1.65 (one-sided 5%), and above the unfiltered base on the same days.
  A pass still needs the MT5 broker pass-speed gate before any live use.
- Futility stop: after >= 75 trades, mean <= -0.10R -> stop and record a fail.
- Monthly status reads are for monitoring only; they cannot produce an early pass.

## the trader's manual version (for FX Replay / Notion)
Notion "Manual backtest" columns: `Caixa ÷ spread` (number), `Min após 08:30` (number), `Tendência 5d`
(A favor / Neutra / Contra, threshold 0.59 ATR20), `3 filtros` (checkbox = all three hold). FX Replay shows no real
spread: use MT5 broker typical spreads (gold ~$0.30, so the box must be >= ~$10). Manual trades are a practice record;
the forward test above is the evidence.

## Honest prior
About 10-15%. The combination was mined from data that has already been seen; most such patterns regress to zero.

## Window
ORB family this window: about 23 of 40 variants (this is one trial).
