# Pre-registration: gold-trend risk switch for the pair (written 2026-10-12, before any switched series was built)

the trader: "(original wording omitted)". Motivation (`FOLLOWUPS_2026-10-12.md`, point 3): without a gold trend (2022-23) the live x1.5 size doubles the drawdown against x1.0 and adds no profit; the MT5 broker buffer is 8,000 USD.

## Rule (one, fixed now)
Pair size multiplier for server day D: **x1.5 if the gold daily close of day D-1 is above its 200-day simple average (of closes up to D-1), else x1.0.** Gold daily closes: `forex/early_mt5/data/XAUUSD_D1.parquet` (server days, from 2004, so the average exists from the first day of both pools). Everything else as the live system: guard 1,500, CPI news-flat, ManualDip 500 USD day risk (x0.75), pass70 rules, start +560 counted on 2026-10-12, MIX = 50/50 of the MT5 broker 12-month and FT 2022-26 pools.
Construction: the switched daily series takes (V, B, Hi) of day D from the x1.5 series when the filter is ON and from the x1.0 series when OFF (both come from `combo_grid.pair_series`). Approximation, declared: a position that is open across a regime change keeps the size of the series it was drawn from for that day only.
Descriptive output too: share of days ON in each pool, and the pair's P&L, max drawdown and worst day by regime.

## Acceptance (adopt as a candidate if ALL hold)
1. MIX P(pass) by 22 Dec is not lower than the live x1.5 by more than 1.5 points, and by 30 Nov not lower by more than 1.5.
2. Breach by 31 Jan is lower than live by at least 0.5 points OR the FT pool's 2022-23 max drawdown (realised cumulative) is at least 25% lower.
3. FT 2024-26 net is at least 85% of the live x1.5 net (the switch must not give away the trend years).

## Caveat fixed in advance
There is no separate hold-out: the filter is tested on the same 2022-26 history that revealed the problem, and gold is above its 200-day average in most of 2024-26. A pass is a planning candidate with one declared, untuned parameter (200 days); it would be a risk-control choice, not an edge, and the trader decides. The live config is not touched by this round.

## Honest prior
Moderate that it lowers the 2022-23 drawdown (the filter is slow but 2022-23 had long stretches below the average), low that it costs nothing in pass speed. Trial RS1.
