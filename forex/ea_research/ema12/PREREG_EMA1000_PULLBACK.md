# PREREG_EMA1000_PULLBACK: the same 1,000 variants entered on a pullback limit order (written 20 Oct 2026, local clock; before any result)

the trader, 20 Oct, after EMA1000_NOCOST (limit at the signal close fills 98% of the time, so it was a market order without lag): "test the pullback limit order".

## What stays the same as PREREG_EMA1000.md / PREREG_EMA1000_NOCOST.md
Signals (the first valid signal of each day and market), the 1,000 variants (seed 20261020), the 46 MT5 broker, DEV 2022-24 / VAL 2025 only (nothing after 2025-12-31 is loaded; the sealed 2026 days stay sealed), target rules, stop multiples, same-minute stop + target = loss, 60 bars maximum, day-clustered t, limit fills by touch (a long fills when the low, on real quotes the ASK low, is at or below the limit; a short when the high, on real quotes the BID high, is at or above it), fill at the limit or at the open if it opens through it, the stop (but not the target) counts in the fill minute. Code: `ema1000_pullback.py`, importing `ema1000.py` and `ema1000_nocost.py`.

## What changes: the limit price sits BEHIND the signal candle's close
For a signal with direction s (+1 long / -1 short), signal-candle close c, and depth D, the rule's limit is at c - s x D (a long waits for a dip, a short for a bounce). Four depths, all fixed now:
- **P25, P50, P100:** D = 0.25, 0.5 and 1.0 x the prior 14-bar mean range of the signal timeframe (the ATR the variants already use).
- **PEMA:** D = |c - EMA| at the signal candle's close (a retest of the EMA the variant is built on).
The order is live for 15 minutes after the signal candle closes (same day, no data gap longer than 15 minutes), then cancelled; unfilled = no trade that day (one order a day, a later signal does not replace it). The target distance d is computed by the variant's own rule FROM THE LIMIT PRICE (so a deeper pullback gets a farther target level); the bracket is fixed on the limit price: target c_L + s x d, stop c_L - s x stop multiple x d. R = s x (exit - fill) / (stop multiple x d).
**Inverted side** (reflection, so it is the exact mirror of the rule): direction -s with its limit at c + s x D (the opposite trade waits for ITS pullback), same d. Signals whose target is invalid at the limit price are skipped as in EMA1000.
Each depth is run in two fill models: **Z** (zero spread, mid prices; a ceiling MT5 broker does not offer) and **Q** (real MT5 broker bid / ask; the only model MT5 broker could offer).

## Reports (descriptive) and bars
Per depth, model and side: fill rate, DEV and VAL mean R per FILLED trade (median over variants, best variant, share above zero, largest clustered t), mean R per SIGNAL (unfilled = 0), per market medians, comparison with market entry (NOCOST Z and the original). Checks before the run: fill invariants (never worse than the limit; fill minute 1..15 after the signal candle; the touch really happened; rule and inverted limits sit on the intended sides of c), truncation test (data after the fill minute cut), hand check, fill rates for the baseline variant.
Only Q can produce a candidate: it must pass the EMA1000 bars (DEV n >= 3,000, mean R >= +0.03, VAL mean R > 0 and t >= 1.65, each DEV year > 0, best-market-out mean R > 0 and t >= 2.5) with the DEV t bar raised to **4.19** (the same 1,000 variants now get seven looks: the original, NOCOST Q, and four pullback depths on the rule side plus the inverted side counted inside each; 0.1 / 7,000). Z gives no candidate. The 2026 hold-out is not opened in any case and nothing here goes near the account.

## Honest prior
A pullback limit improves the entry price but is filled most often when the move has turned against the trade (adverse selection), so the fill rate will fall (guess 40-80%) and the per-trade result is not expected to beat the spread; Z (no spread) is expected near zero; Q is expected negative; a candidate is not expected (prior about 1-3%). A positive Z only says the pullback carries information before costs.
