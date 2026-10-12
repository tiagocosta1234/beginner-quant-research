# Pre-registration: the Bollinger + RSI(2) 4-hour rule INVERTED on crypto (written 2026-10-12, before any inverted trade was computed)

the trader: "(original wording omitted)". On MT5 broker's eight crypto CFDs the rule (long when Cutler RSI(2) < 10 AND close > SMA(200) AND close < lower Bollinger 20/2, exit close > SMA(5) OR RSI(2) > 70) lost in both windows (OOS 2022-01..2024-09 -38.5 bp, in-sample 2024-10..2026-09 -29.2 bp, `CORE4_ALL_RESULT.md`).
**Declared problem:** choosing the opposite side after seeing both MT5 broker windows negative is selection on those windows; they cannot be the proof. The proof window is data nobody has looked at: Binance spot 4 h klines 2020-01-01 .. 2021-11-30 (before MT5 broker's data start; the trader's scope rule: 2020 onward).

## The inverted strategy
The SAME entries and exits as the long rule (same signals, bars, indicators; nothing re-tuned), but SHORT: entry at the next bar's open, exit at the open of the bar after the (original) exit signal. Effectively the mirror image of every trade of the long rule: it makes money when crypto keeps falling after an RSI-exhausted dip and rebounds only slowly.
Symbols: BTC, ETH, LTC, SOL (from 2020-08), XRP, ADA, BNB, BCH.
Costs: MT5 broker data: real fills (short entered at the bid-open, exited at the ask-open). Binance window (mid prices, no spread in the data): net = gross - the symbol's median relative MT5 broker spread ((ask - bid) / bid, all minutes of `data_mt5`), charged once per round trip (the long and the short each pay one spread between their two fills).
Observations: trades of the same calendar day averaged into one.

## Windows and acceptance
- PROOF (decides): Binance 2020-01-01 .. 2021-11-30. Accept if >= 40 day-observations, mean >= +15 bp net, PF(day) >= 1.3, one-sided t >= 1.65.
- CONSISTENCY (must also hold, but cannot prove): the same inverted rule on MT5 broker real fills must have a positive mean in BOTH MT5 broker windows (OOS 2022-01..2024-09 and in-sample 2024-10..2026-09).
Reported: trades per year, indicative Sharpe at 25,000 USD per trade, per coin means.
If it passes, a candidate only (short crypto CFDs on MT5 broker, weekend and funding behaviour, stop design, correlation with the pair). Nothing goes live from this round.

## Honest prior
Low. Crypto does trend and a mirror of a losing mean-reversion rule often loses after costs, but a -38 bp mean is large relative to the spread (about 10-30 bp round trip), so some of it may be real continuation. The unseen 2020-21 window (bull market, very different from 2022-24) is a hard test: shorting dips in the 2020-21 bull run should lose. One trial CM1.
