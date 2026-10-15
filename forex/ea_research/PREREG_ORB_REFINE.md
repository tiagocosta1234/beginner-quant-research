# Pre-registration ORB-REFINE: conditions and regimes for the card's two breakouts (written 2026-10-15 ~10:20 local, before any code or result)
the trader: "maybe we could refine these gold London breakouts and Nasdaq New York breakouts, because breakouts don't work always the same, there will be different patterns through time". The base trades are exactly the two trades of `forex/mt5_DAILY_CARD_WEEK_2026-10-19.md`; this round asks whether a condition known BEFORE the entry, or the strategy's own recent results (regime), separates good breakout days from bad ones.

## Base trades (the card, scale-free so 2022 prices are comparable)
MT5 broker M1 bid/ask, data before 2026-01-01 only (2026 sealed). Box = chart (bid) high/low of the first 30 minutes; buy stop at the box high (fills when the ask reaches it, at the level or at the minute's ask open if beyond), sell stop at the box low (bid); first fill wins, the other order is cancelled; both in one minute = no trade. Stops and targets checked minute by minute on the executable side, stop first if both in one minute, gapped stop at the open. Net R with real bid/ask; gross reported.
- **GOLD (XAUUSD):** box 08:00-08:30 London; orders until 11:00 London; stop = the box height, clipped to 0.12%-0.36% of price (= $5-$15 at 4,150), no trade if the box is above 0.48% of price ($20); target 2R; exit at 14:00 London.
- **NASDAQ (NSDQ):** box 09:30-10:00 New York; orders until 12:00 NY; stop = half the box, clipped to 0.17%-0.34% of price (= 50-100 points at 29,600); target 2R; exit 15:30 NY.

## Features (all known at the fill)
ATR14 and SMA20 from completed server days (bars 01:00-22:59 mid). trend = sign(previous close - previous SMA20); overnight = sign(mid at box start - mid at 00:00 London) for gold, sign(mid at 09:30 NY - previous day's mid at 15:59 NY) for Nasdaq; box_rel = box / ATR14, "small" = below the median box_rel of the previous 250 base trades of that market; fast = filled within 15 minutes of the box end; momentum = mean net R of that market's previous 20 COMPLETED base trades.

## Cells (12) = 2 markets x 6 refinements
A trend-with: trade only if the side equals trend. B small box only. C overnight-aligned: side equals overnight. D fast trigger only. E regime skip: trade only if momentum > 0. F regime flip: if momentum > 0 take the breakout, if momentum <= 0 take the FADE (the opposite side at the same trigger minute, entry at that minute's executable price, stop and target mirrored with the same distances).

## Periods and gates
DEV 2022-01..2024-12, VAL 2025, HOLD 2026-01..09 (sealed; one look only for a passing cell).
1. DEV mean net R >= +0.10 and t >= 2.65 (trade-level, Bonferroni 12, one-sided).  2. VAL mean net R > 0 and t >= 1.65.  3. Positive in at least 3 of the 4 years.  4. Placebo: the cell's DEV mean must beat the 95th percentile of 1,000 random subsets of the base DEV trades of the same size (F: 1,000 random flip assignments with the same number of flipped trades).  5. At least 100 DEV trades.
Reported, not gated: the base card trades per market and year (what the card would have done), win rate, worst losing streak.

## Honest prior
About 5%: single conditions rarely survive out of sample and the base is near zero (ORB_GOLD London +0.007 / +0.086 R, Nasdaq opening range +0.035 R); TRB showed that choosing among many configurations by recent results does not carry forward, so E and F use one fixed rule, not a search.
