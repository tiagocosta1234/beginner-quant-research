# Swap and financing: forex/CFDs versus futures

The biggest practical difference found between the two markets was not spreads or fees. It was
the cost of holding a position overnight.

## How each market charges for time

- **Forex and CFDs (MT5).** A position held past the daily rollover (17:00 New York) is charged
  or paid a swap. It is roughly the interest-rate difference of the two currencies (or the
  benchmark rate for an index or metal) plus the broker's markup, and it is tripled once a week
  to cover the weekend. For a long index or gold CFD it is a cost of very roughly 3 to 7% a year
  of the position's size. Some accounts are "swap-free" and charge nothing.
- **Futures.** There is no swap. The financing is already inside the futures price (the basis:
  a future trades above or below spot by about the interest rate minus any yield, for the time
  left to expiry). A long future therefore earns the market's return over cash, with no broker
  markup on top. What you pay instead is rolling: closing the expiring contract and opening the
  next one each quarter (or month), which costs a spread twice.
- **Intraday-only trading** avoids both, but also gives up everything that happens overnight.

## What the research found

### The overnight premium is real but tiny on its own

Holding US index CFDs from 15:55 to 09:35 New York time (`forex/ea_research/OVERNIGHT_RESULT.md`)
made about +2.8 basis points a night against 50 to 90 basis points of night-to-night noise: a
coin weighted about 55/45. It was absent in 2022 and 2025. Without leverage it is worth almost
nothing; with leverage, a single gap can wipe out months of it, and a gap cannot be stopped.

### A slow drift book passed every pre-registered bar, but only because holding was free

The "D2" book (`forex/ea_research/SWAPFREE_DRIFT_RESULT.md`, `swapfree_drift.py`) is long-only:
gold, stock indices and a few other markets, weighted by inverse volatility, and only held while
each market is above its 200-day average. On the swap-free account it made, net of the broker's
spread, in USD a day per 100,000 of gross exposure:

| period | result |
|---|---|
| 2020-21 (out-of-time check, separate data source) | +24.5 |
| 2022-24 (development) | +30.2 |
| 2025 (validation) | +87.5 |
| 2026 (hold-out, opened once) | +50.6 (Sharpe about 0.9) |

That is about +10% a year gross. The only cost was the spread on the weekly rebalancing buys,
about 10 to 20 USD a year per 100,000. On a normal account the 3 to 7% a year of swap would have
removed most of the return, and a version that closed at the end of each day kept only a small
part of it (it is earned overnight and over weekends).

Refinements did not improve it (`SWAPFREE_D2X_RESULT.md`, `D2PLUS_RESULT.md`): adding crypto,
silver or more indices added correlated risk, and different weighting schemes were 0.95 to 1.00
correlated with the original. The edge is the trend-filtered drift itself, not the details.

### Rerun on free data

`python -m drift_book` ([drift_book/](../drift_book/)) runs the same rules on free daily closes from
2010, once for each holding cost. Since 2010 it makes about 7.6% a year swap-free, 6.2% on futures
and 4.3% with a normal CFD swap; 2010-19, which the research never looked at, is weaker (4.9% a
year) but positive. The trend filter cuts the worst drawdown from -25% to -14% and gives up return
for it. The numbers differ from the MT5 ones (index levels without dividends, daily closes), so
the direction matters more than the exact figures.

### What it would take on futures

The same idea on futures pays no swap, so the financing drag drops to the cash rate already
priced into the futures, plus the roll spreads. In other words, a futures version earns the
excess return over cash rather than the full return, minus a few roll costs a year. It is slow
(a Sharpe near 1 is roughly one good year in six bad months), it needs overnight and weekend
holding, and it needs contract sizes small enough to rebalance, which micro futures make
possible.

## Takeaways

1. Check the holding cost before testing any idea that holds overnight. For slow strategies the
   swap can be larger than the edge.
2. "Swap-free" turns small, well-known risk premia (trend-filtered drift, overnight returns) into
   something testable. Futures do the same more fairly, at the cost of rolling.
3. Intraday-only constraints remove exactly these slow edges, which were the only ones that held
   up in this project.
