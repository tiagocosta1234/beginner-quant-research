# Pre-registration: intraday momentum on indices (IM) and gold/silver ratio reversion (GS) (written 2026-10-12, before any return was computed)

the trader: "mais ideias de EAs". Two published ideas, rules as in the literature, one parameter set each, MT5 broker M1 bid/ask (`data_mt5`, 2021-12 .. 2026-10-02, swap-free). Own EAs only.
Periods by entry date: DEV 2022-01-01 .. 2024-12-31, VAL 2025, HOLD-OUT 2026-01-01 .. 2026-09-30 (one look, accepted trials only).

## IM: last-half-hour momentum (Gao, Han, Li, Zhou 2018)
SP+, NSDQ+, DOW+. Signal: sign of the return from the previous trading day's 15:59 NY bid-open to 10:00 NY bid-open (first 30 min including the overnight gap). Trade: long if positive, short if negative, enter at 15:30:00 NY (long at ask, short at bid), exit at 15:59:00 NY (long at bid, short at ask). Return in bp of the entry price. Per day the three indices are averaged into one observation.
Accept: DEV mean >= +1.5 bp/day and t >= 2.0 (about 750 days); VAL mean > 0; HOLD mean > 0.

## GS: gold/silver ratio reversion
XAUUSD+ and XAGUSD+. Daily price = the 15:59 NY bar bid-open. ln(XAU/XAG) z-score over the previous 60 trading days (mean and sd of the 60 values up to and including today). z >= +2.0: short gold, long silver; z <= -2.0: long gold, short silver. Exit when |z| <= 0.5 or after 20 trading days. One position at a time. Legs dollar-neutral, each entered and exited at ask/bid (spread paid on all four fills); return in bp of one leg's notional = long-leg return - short-leg return. Trades indexed by entry date.
Accept: DEV >= 20 trades, mean >= +30 bp/trade, t >= 1.65; VAL mean > 0; HOLD mean > 0.

## Honest prior
IM: low to moderate (documented on SPY 1993-2013, weaker later, spread 1-2 bp). GS: low (the ratio trended hard in 2020-26, mean reversion is unstable and few trades). Nothing goes live from this round; the pass-speed gate is a separate question. Trials IM and GS (DEV, VAL).
