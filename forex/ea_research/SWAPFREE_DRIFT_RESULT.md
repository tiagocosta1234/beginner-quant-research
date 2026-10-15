# SWAPFREE_DRIFT_RESULT - long-only risk-balanced book on MT5 broker's swap-free terms (2026-10-15, local clock 15:15)

> **2026-10-15 15:52: the account numbers in this file are SUPERSEDED by `D2_MT5RULE_RESULT.md`** (MT5 broker's daily line is set from the day-start BALANCE, so a held book carries floating losses into the line, and only realised profit counts, at most +2,000 a day). The edge results (DEV / VAL / OOT / HOLD / ticks) are unaffected.
Pre-registration: `PREREG_SWAPFREE_DRIFT.md` (commit cb25fd63, Amendment 1 before any P&L). Code: `swapfree_drift.py`, `swapfree_ticks.py`, `swapfree_mt5sim.py`. Rows: `D:/finance/si_ledgers/SWAPFREE_*.csv`.

## Verdict
**D2 (inverse-vol long book with a 200-day trend filter) and D4 (D2 + volatility target) pass every pre-registered edge bar: they are profitable on MT5 broker after MT5 broker's real costs.** D1 / D3 (always long) narrowly miss the t bar. **But they do not help the account from today:** alone, breach is larger than pass at every size; next to the gold EA pair they add 3-4 points of pass by 22 Dec for 3-7 points of breach. A Sharpe-1 beta book cannot climb +10,292 while staying above a floor 5,708 away.

## Why it can work only here
Account <acct> pays no swap, no commission and no fee (deal history re-checked today: gold held 5 nights incl. a weekend, Nasdaq held overnight, swap 0.00), although the symbol specs list swaps (XAUUSD+ -65 points a lot long, indices -3% a year). On a normal CFD account financing of about 3-7% a year would remove most of this book's +10%/year gross return. The only cost here is the spread on the buys: 10-20 USD a year per 100k gross with the weekly no-trade band.

## Numbers (USD a day per 100k gross notional, net of MT5 broker bid/ask)
| variant | OOT 2020-21 (HistData) | DEV 2022-24 | VAL 2025 | DEV+VAL t (bar 2.24) | HOLD 2026 (one look) |
|---|---|---|---|---|---|
| D1 always long | +94.9 (t 2.69) | +41.0 | +94.0 | 2.08 (fail) | not opened |
| D2 + trend 200d | +24.5 (t 1.03, from Oct 2020) | +30.2 | +87.5 | **2.42 pass** | **+50.6** (t 0.80, Sharpe 0.91) |
| D3 vol target | +71.2 (t 2.23) | +44.4 | +94.6 | 2.21 (fail) | not opened |
| D4 trend + vol target | +24.2 (t 0.91, from Oct 2020) | +36.0 | +95.8 | **2.45 pass** | **+33.7** (t 0.70) |
- Annualised Sharpe of D2 2022-25: 1.19 (DEV 0.87, VAL 2.00). By year (D2): 2022 -10.7k, 2023 +16.7k, 2024 +17.5k, 2025 +22.6k per 100k gross; max drawdown -11.6k (2022). The trend filter did not save 2022 (whipsaw); it did halve the drawdown vs D1 (-20.5k).
- P&L is spread over the five markets (D2 DEV: SP +4.1k, NSDQ +6.3k, DAX +5.6k, NIKKEI +0.2k, gold +7.2k; VAL gold +9.6k of +22.6k; in OOT gold lost -6.4k): not a disguised gold bet.
- Worst day low (conservative sum of each market's worst bid): -5.9k per 100k gross (5 Aug 2024 yen-carry unwind), 8 days below -2.5k per 100k in 2020-25.
- **Real ticks (bar 4):** on MT5 broker ticks 2025-10-01..2026-10-02 (300 ms latency, first tick after 18:00:00.3) D2 earned +14,669 vs +14,664 on the M1 engine (ratio 1.00), D4 +13,327 vs +13,323: a weekly book does not suffer the tick gap that killed the tight-stop breakouts. Spreads at 18:00 on ticks = M1. To 2026-10-13 on ticks: D2 +14,240.
- Daily correlation with the gold EA pair (x1.2, FT pool 2022-26): -0.006 (D2), +0.003 (D4).

## Robustness (descriptive, after the registered result; `swapfree_sens.py`, `SWAPFREE_SENS_OUTPUT.txt`)
All 10 one-at-a-time neighbours of D2 (SMA 100 / 150 / 250, vol window 20 / 40 / 120, decision Wednesday / Friday, decision 16:00 / 20:00 server) are positive in OOT, DEV, VAL and 2026: USD a day per 100k gross OOT +20..+50, DEV +21..+34, VAL +78..+98, 2026 +46..+56; DEV+VAL t 2.13..2.71. A plateau, not a tuned point. (2026 is no longer clean for the neighbours: D2's HOLD was opened.) Consistent with TREND_PORT (2026-10-14): there the long-only vol-parity yardstick had Sharpe 0.94-1.03 over 2021-25 while trend timing added nothing; the 200-day filter here mainly trims the 2022 drawdown (-11.6k vs -20.5k for D1).

## On the account (bar 5, MT5 broker rules from 97,708.08; pass% / breach%)
| book | G | 22 Dec | 31 Mar 27 | 30 Jun 27 |
|---|---|---|---|---|
| D2 alone (2020-25 days) | 50k | 0.0 / 3.3 | 0.5 / 8.8 | 4.9 / 13.3 |
| D2 alone | 100k | 1.6 / 23.9 | 19.1 / 44.8 | 31.4 / 53.1 |
| D2 alone | 150k | 6.2 / 77.3 | 11.3 / 88.2 | 11.5 / 88.5 |
| gold pair x1.2 alone (FT 2022-26) | - | 9.8 / 3.7 | 56.3 / 7.1 | 78.2 / 8.0 |
| pair x1.2 + D2 | 25k | 13.4 / 10.4 | 58.9 / 18.1 | 74.1 / 19.6 |
| pair x1.2 + D4 | 25k | 13.7 / 7.3 | 61.2 / 12.8 | 77.7 / 14.2 |
Nothing passes by 30 Oct (0.0-0.3% at every size). The breach comes from the floor (the 2022-type drawdown is 2-3x the 5,708 buffer at a useful size) and from the conservative day low. The pair-only line is the FT 2022-26 pool alone (no MT5 broker 12-month mix), so it is lower by 22 Dec than PAIR_FROM_TODAY's mix.

## What it means
- It is the first rule today that is profitable after MT5 broker's real costs on every test (pre-registered, out of time, hold-out, real ticks). It is a risk premium (long stocks and gold, sized by volatility, out of a market below its 200-day average), not a forecasting edge, and it lost 10.7% of gross in 2022.
- For the test from 97,708 it is the wrong tool: its pass speed is months-to-years and its drawdown is bigger than the buffer. It could make sense after a pass (on a live account it earns about +8-9% a year on gross 100k with MT5 broker's swap-free terms), or with a fresh test where the floor is 8,000 away and MT5 broker has no time limit; neither is a decision for now.
- Unvalidated as a live strategy: no paper or live record yet; any use is the trader's decision and hands-on step.

## CPPI sizing (descriptive, `swapfree_cppi.py`, `SWAPFREE_CPPI_OUTPUT.txt`)
Gross = min(cap, m x (equity - 92,000 - 500)), pass% / breach%: D2 alone with cap 40k (keeps the worst day above -2,500): 0% / 0% by 30 Jun 27 and 11-14% / 0% by 31 Dec 27; cap 60k, m 10: 11-12% / 6-7% by 30 Jun 27, 34-35% / 9-11% by 31 Dec 27. Floor-safe but far too slow for the test. Next to the pair the simulation adds the two streams' day lows as if simultaneous (and without a shared day guard), so the combined breach numbers (9-16% by 22 Dec) are pessimistic; a real account guard closing everything at the day stop would bound them.
