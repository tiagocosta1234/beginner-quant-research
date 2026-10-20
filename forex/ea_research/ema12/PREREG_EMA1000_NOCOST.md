# PREREG_EMA1000_NOCOST: the same 1,000 variants with no spread and with limit-order entries (written 20 Oct 2026, local clock; before any result)

the trader, 20 Oct after EMA1000 (0 of 1,000, drag 0.183 R a trade): "run it again but with limit orders, no spread".

## What stays the same as PREREG_EMA1000.md
Signals, the 1,000 variants (seed 20261020), the 46 MT5 broker, DEV 2022-24 / VAL 2025 only (nothing after 2025-12-31 is loaded; the sealed 2026 days stay sealed), target rules, stop multiples, same-minute stop + target = loss, 60 bars maximum, day-clustered t. Code: `ema1000_nocost.py`, importing `ema1000.py`.

## What changes: three fill models, each run for the rule side and for the INVERTED side
- **Z (zero spread, market entry):** every price is the mid of bid and ask (open, high, low, close); entry at the open of the minute after the signal candle closes; no other change. This isolates what the spread costs.
- **L (zero spread, limit entry):** prices are mid. A limit order is placed at the signal candle's close (mid), live for the 5 minutes after that candle closes (same day, no data gap longer than the 5 minutes). Long: filled by the first minute whose low is at or below the limit; short: whose high is at or above it. Fill price = the limit, or the minute's open if it opens through the limit. Bracket fixed on the LIMIT price: target distance d (the variant's rule, computed at the limit price), stop = stop multiple x d. In the fill minute only the stop counts (the target may have been touched before the fill); from the next minute the usual rules. R = side x (exit - fill) / (stop multiple x d). Unfilled = no trade that day (one order a day; a later signal does not replace it). 60 bars maximum from the fill minute, closed at the mid. The inverted side places the opposite-direction limit at the same price with the same distances.
- **Q (extra comparison, real MT5 broker quotes, limit entry):** as L but with the real bid / ask: a long fills when the ASK low is at or below the limit (fill at the limit or the ask open if lower), a short when the BID high is at or above it; exits on the exit side as in EMA1000. This is the only fill model that MT5 broker could offer, and it shows how much of L survives the real spread.

## Reports (descriptive)
Per model and side: fill rate, DEV and VAL mean R per FILLED trade (median over variants, best variant, share above zero, largest day-clustered t), mean R per SIGNAL (unfilled counts as 0), per market medians. Z minus the EMA1000 result gives the cost of the spread; Z's random side (rule + inverted) / 2 gives what is left of the structure drag. Checks before the run: the market path reproduces `EMA1000_MARKETS.csv` for 20 variants on XAUUSD; fill prices are never worse than the limit; a truncation test (data after the fill minute cut gives the same fill); hand check of printed trades.

## Bars and what the result can mean
- Z and L are a ceiling (no spread, a touch is a fill, no queue) that MT5 broker does not offer. They produce NO candidate. A positive Z or L only says the signal carries information before costs and would need a separate, cost-realistic pre-registration.
- Only Q can produce a candidate, and only by passing the EMA1000 bars (DEV n >= 3,000, mean R >= +0.03, clustered t, VAL, each year, best market out) with the t bar raised from 3.72 to 3.99 because the same 1,000 variants now get three looks. The 2026 hold-out is not opened in any case; nothing here goes near the account.
- Limit orders carry adverse selection (they fill most when the market goes against them), which this model includes only through the touch rule; fill rates below 100% are reported rather than hidden.
- Honest prior: Z loses less than EMA1000 by roughly the spread share and is probably still negative; L is the open question; Q is expected negative.
