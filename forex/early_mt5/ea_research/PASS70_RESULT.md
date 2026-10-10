# Can P(pass the MT5 broker test) reach 70%, and by when? (2026-10-10, local local clock)

the trader (2026-10-10 14:40): "precisamos de 70%, trabalha ate atingirmos um numero equivalente ou superior", after being told that P(pass by 30 Oct) is about 4%. Script `pass70.py` (question and method written in its docstring before the run), output `PASS70_OUTPUT.txt`. A planning simulation, not an edge trial: no ledger rows, nothing tuned on the 2026 hold-out.

State (read-only `live_state`, 14:40): counted closed profit +99.68, four gold longs floating +460 (not counted). Rules as live: guard loss cap 2,000 a day, MT5 broker's counted-profit rule min(day, 2,000), breach = in-day low <= -2,500 or equity <= 92,000, the counted-equity pass lock at 8,100, and the no-hedge rule (skips 9.8% of the 12-month trades and 17.2% of the 2022-26 trades, the same shares as `NOHEDGE_RESULT.md`; x1.2 reproduces its 3.9% / 31.8% / 50.4% against 4.0% / 31.6% / 49.2%). Pools: 12M = last 12 months on MT5 broker real ticks (gold in a strong trend), 2022-26 = MT5 broker trades scaled to MT5 broker prices, MIX = 50/50; stationary block bootstrap, 20,000 paths.

## 1. The ceiling: any size, chosen every day by dynamic programming
| deadline (business days from Mon 12 Oct) | live x1.2: MIX (12M / 2022-26) | best dynamic sizing, losing the account NOT penalised: MIX (12M) | its breach MIX (12M) | dynamic sizing with breach penalty 0.3: MIX (12M), breach MIX |
|---|---|---|---|---|
| 30 Oct (15) | 3.9% (6.9% / 0.8%) | 13.3% (17.4%) | 10.9% (15.5%) | 13.0% (17.0%), 4.5% |
| 30 Nov (36) | 31.8% (49.2% / 14.4%) | 41.6% (54.0%) | 14.8% (18.6%) | 42.0% (55.4%), 4.9% |
| 22 Dec (52) | 50.4% (72.7% / 28.1%) | 57.0% (73.6%) | 11.0% (11.3%) | 57.6% (74.7%), 4.0% |
Policies designed on one regime and evaluated on the other give the same picture (30 Oct at most 13.3% MIX, 17.4% 12M). Every dynamic policy trades above x1.2 on many days, which exceeds MT5 broker's "1% risk per trade idea" guideline (the SDB already risks 1.14% per trade at x1.2): these are ceilings, not proposals.

## 2. When does the live setup reach 70%? (constant size, first business day with P(pass) >= 70%; holidays ignored)
| size | 12M regime | MIX | 2022-26 regime | breach within a year 12M / 2022-26 |
|---|---|---|---|---|
| x1.0 | 28 Dec 2026 | 19 Feb 2027 | 3 May 2027 | 0.4% / 1.5% |
| **x1.2 (live)** | **18 Dec 2026** | **29 Jan 2027** | **30 Mar 2027** | 0.6% / 3.3% |
| x1.5 | 21 Dec 2026 | 25 Jan 2027 | 10 Mar 2027 | 4.5% / 7.4% |
| x1.8 | 13 Jan 2027 | 11 Feb 2027 | 2 Mar 2027 | 21.3% / 12.8% |

## 3. What edge would 70% need? (every day of the x1.2 series shifted up by delta USD, same day-to-day variability, the guard still floors a day at -2,000)
| 70% by | 12M regime | 2022-26 regime | MIX (extra USD/day; % of the account a month) |
|---|---|---|---|
| 30 Oct | +423/day: mean day 623 vs 199 now (3.1x), daily Sharpe 0.76 vs 0.24 | +521/day (7.8x), daily Sharpe 1.06 | +479/day (+10.1% a month) |
| 30 Nov | +71/day (1.4x), daily Sharpe 0.33 | +183/day (3.4x), daily Sharpe 0.46 | +140/day (+2.9% a month) |
| 22 Dec | already 72.7% at x1.2 | +105/day (2.4x), daily Sharpe 0.32 | +62/day (+1.3% a month) |
Any zero-edge strategy (a pure gamble, whatever its size or shape) is capped by optional stopping at P(pass) <= (100 + 8,000) / (8,000 + 8,000) = 50.6% with MT5 broker's static floor as the loss room (45.5% with our 6.5% guard floor), even with no deadline; MT5 broker also prohibits gambling-style bets.

## Reading
- **70% by 30 Oct cannot be reached with this edge, whatever the size.** The ceiling is 13% (17% if gold keeps the last-12-months trend), and it costs an 11-15% chance of losing the account. A 70% would need the pair to earn about 600 USD a day, three times its best 12 months, a daily Sharpe of 0.76 (about 12 annualised). Nothing tested in this repo comes close: the pair's daily Sharpe is 0.24 in its best regime, and about 100 registered trials since 2026-10-08 found no second edge.
- **30 Nov: also out of reach.** At most 42% in the mix (55% in the 12M regime) with sizes above MT5 broker's guideline. It needs about +140 USD a day more (+2.9% a month).
- **22 Dec: 70% only if the gold trend of the last 12 months continues** (72.7% at the live x1.2). In the mix it is 50%, at most 57.6% with dynamic sizing.
- **With the live setup, 70% arrives around 18 Dec 2026 (12M regime), 29 Jan 2027 (mix) or 30 Mar 2027 (2022-26 regime).** Breach stays under 1% (12M) to about 3% (2022-26) over a year.
- **The one lever that brings 70% to 22 Dec in the mix is a second, independent edge worth about +62 USD a day (+1.3% of the account a month) after costs.** This is a realistic research target, unlike the +479 a day October would need. The shift model keeps the pair's variability, so a real extra leg must add that mean without adding much variance: daily sd well under the pair's 565-815 USD and correlation with the pair at or under 0.3. Every candidate still goes through the registered protocol and the 2026 hold-out.
- Caveat: both pools are in-sample and the 12M one is flattered by the 2025-26 gold trend; the mix is the honest planning number.
