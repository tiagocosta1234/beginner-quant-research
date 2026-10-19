# PREREG_MANUALRULE: the trader's own description of his 12 EMA setup, tested mechanically on MT5 broker gold and Nasdaq 2022-2026

Written 2026-10-19 (local clock, main PC) BEFORE any P&L of this rule was computed. the trader, in his words: "I enter when there's a clear candle that opens on one side of the 12 EMA and closes
clearly on the other side, it can't be a small candle, body bigger than the bigger wick it has, then I target an FVG if it's really big, or if it's a small one I target the whole FVG, 0.5 RR."

## Interpretation (registered; every free choice is fixed here)
- Data: MT5 broker M1 bid/ask, server clock; 1-minute mid candles for the signal; EMA12 of 1-minute mid closes over the whole series (as TradingView draws it).
- Window: the first 15 minutes after the London open (08:00 London) or the NY open (09:30 New York), converted to the server clock per day. the trader's 30 trades all entered inside it. One trade per market, session and day.
- Signal candle t (bars with open offset 0..14): mid open and mid close on opposite sides of EMA12 at bar t; direction = the side of the close; body > max(upper wick, lower wick); body >= 0.5 x ATR14 (mean 1-minute mid range of the 14 bars before t) as the "not small" bar.
- FVG = three consecutive 1-minute mid candles with a gap: bullish if high(a) < low(c), bearish if low(a) > high(c); unfilled = no later bar up to t has traded through its far edge. Looked up over the 90 bars before and including t. A long targets a bearish FVG above, a short a bullish FVG below
  (the imbalance price tends to revisit). Usable = its near edge is at least 0.5 x ATR14 beyond the entry. The nearest usable FVG sets the target; if there is none, the candle is skipped and later candles in the window are scanned.
- Entry at the open of bar t+1 (ask for longs, bid for shorts). Target distance d = |target - entry|; stop = 2 d on the other side (0.5 RR). Exits on the real side of the book, stop first if both fall in one bar, time exit after 60 bars.
- Target variants (3): K1 "as described" = far edge (the whole FVG) if the gap is at most 1.5 x ATR14 wide, the middle of the gap if it is wider; K2 = always the near edge; K3 = always the far edge.
## Trials: 12 = XAUUSD, NSDQ x London, NY x K1, K2, K3. Periods: DEV 2022-01-01..2024-12-31, VAL 2025, HOLD 2026 (not computed in the default run; opened once, only for a trial that passes DEV and VAL).
## Acceptance (Bonferroni over 12 trials, two-sided 0.05 -> t >= 2.87)
Candidate only if DEV n >= 200, mean R >= +0.05, t >= 2.87; AND VAL mean R > 0 with t >= 1.65. Win = target hit (+0.5 R), loss = -1 R, break-even win rate 66.7% before costs.
## Evidence already seen (declared, no P&L of this rule): (a) on his 30 dated gold trades, a candle matching "opens one side, closes the other" exists within the last 5 bars before the entry for 17 of 30 (23 of 30 within 10 bars) but 21.7% of all 1-minute bars
satisfy that, so this is close to chance; with body > bigger wick it is 12 / 20 of 30; the target matches an unfilled FVG edge within 0.30 USD for 7 of 17 (far edge 4, middle 2, near 1; matched gaps 0.1-1.7 USD wide). The rule as written therefore does NOT
reproduce his entries well on MT5 broker candles (his OANDA candles and the exact entry minute differ); a negative result here is weak evidence about his discretion, and a positive one would be strong about the rule itself.
## Honest prior: 10-15% that one of the 12 passes (his side beats chance on the 30 trades with p about 0.01; the earlier mechanical 12 EMA tests were 0 of 32; costs and the 0.5 RR structure need a win rate above 67%).
