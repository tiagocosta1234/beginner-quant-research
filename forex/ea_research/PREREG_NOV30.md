# PREREG NOV30 - the maximum chance of passing by 30 Nov 2026 with the gold EA pair, the dip leg and the USDJPY breakout

Registered 2026-10-18 00:30 local (local clock, second PC PC-2), before any combined number was computed.
Plan approved by the trader: `C:\Users\fisht\.claude\plans\jazzy-mapping-rossum.md`. the trader asked for a 70% chance, keeps the 30 Nov
deadline and allows three legs: the gold EA pair (ManualSDB + XAU5), the ManualDip dip leg, the USDJPY London breakout.
A planning simulation, not an edge trial: no rule is fitted here; the legs are the registered ones.

## Starting state
Balance = counted equity 95,472.14 (the trader, 2026-10-18), no open positions, EAs off. Counted profit C0 = -4,527.86 vs 100,000.
Horizon: from the first business day the book is armed (default Mon 2026-10-19; re-run with the real start day) to Mon
2026-11-30 inclusive (31 business days from 19 Oct); 22 Dec 2026 also reported for context.

## Legs (unchanged definitions)
- **Gold pair:** `clean_boot_lib.series(pool, mult)` (ManualSDB + XAU5 on the clean guard simulation: closed P&L counted, guard
  loss cap, hedging allowed per MT5 broker's reply 2026-10-11), pools MT5 broker (2025-10-01..2026-09-30, MT5 broker real ticks) and FT (2022-01..2026-09
  MT5 broker trades at MT5 broker prices); multipliers 0 (off), 1.0, 1.2, 1.5, 1.8, 2.0.
- **ManualDip:** `dip_addon.trades()` + `day_arrays()` (z3 <= -2 on SP / NSDQ / DOW / DAX at 15:49 NY / 17:19 Berlin, 1-day hold,
  3-SD stop), V / B / Hi scaled from its 1,000 day risk to 0 / 500 / 1,000.
- **USDJPY London breakout:** `uj_conf.trades()` (0.6-pip spread floor), R minus a 0.06 R real-tick haircut, at 0 / 150 / 250 / 500
  USD a trade; per server day V = R x risk, B = min(V, -risk) (a stop-to-close intraday low, conservative), Hi = max(V, 0).
- Legs are added day by day on the pair pool's calendar (`dip_addon.combine` pattern); B values are summed (conservative).

## Rules simulated (`pass70.simulate` semantics)
Stationary block bootstrap (mean block 5 days) of the joint day rows, 20,000 paths; breach = combined in-day low <= -2,500 or
equity <= 92,000; counted profit adds min(day, +2,000); pass = counted >= +8,000 at a day end or the counted-equity pass lock
(counted + min(day high, 2,000) >= 8,100). Pools: MT5 broker, FT and MIX = 50/50 average of the two.

## Outputs
1. The pass / breach frontier by 30 Nov over the 6 x 3 x 4 = 72 static configurations, per pool and MIX.
2. The dynamic-sizing ceiling: `pass70.dp` over the pair multipliers (lambda 0 = breach not penalised = absolute maximum, and
   lambda 1) with the chosen dip / USDJPY legs, by 30 Nov.
3. For the max-pass configuration and the best pass-per-breach configuration: the same with 70% of the pair's edge (each pair
   day shifted down by 0.3 x the pool's mean pair day), two bootstrap seeds, and P(pass) by 22 Dec.
4. Engine checks first: `pass70.simulate` on the pair alone reproduces `PAIR_FROM_TODAY_RESULT.md` from its own start state;
   the USDJPY-only configuration reproduces the second PC run (`data\scratch\pass_by_nov.txt`, ~1% by 30 Nov at $500).

## Honest prior
The best configuration is expected around 10-25% by 30 Nov (MIX), with breach of the same order or higher; 70% is not
expected (it needs an annual Sharpe near 7.7). The MT5 broker-pool numbers are in-sample and flattered by the 2025-26 gold trend.

## Amendments
1. (2026-10-18 00:31, before any combined number) Match the deployed legs and the reference run (`pair_from_today.py`): the pair is
   built with `combo_grid.pair_series(pool, m, m, 1500)` (ManualSDB and XAU5 at the same multiplier m, guard day stop 1,500, news flat
   on CPI only, as the 11-Oct final plan); the dip leg is `combo_grid.dip_days(risk)` = ManualDip as deployed (z3 <= -1.5, `DA_Z=1.5`,
   P&L x0.75 tester haircut), not z <= -2; the guard also closes the dip and the USDJPY legs (`combo_grid.add_dip` flooring:
   a combined day below -(1,500 + 100) is cut there).
