# F: strategy factory for the 70%-this-month goal: result (2026-10-10, local local clock)

Pre-registration `PREREG_FACTORY.md` (commit 245e650, before any run), script `factory.py`, output `FACTORY_DEV_OUTPUT.txt`. 272 variants (8 MT5 broker x M15/H1 x 17 rules: Donchian, EMA trend, RSI and Bollinger reversion, session momentum), each at 1% of the account per ATR, real median spreads, flat over the rollover and the weekend.

## Verdict: nothing passes; the hold-out stays closed
- DEV 2022-24 daily Sharpe: median -0.035, best +0.046 (USDJPY M15 EMA 20/100); 81% of variants lose after costs; NO variant reaches a daily t of 2. The goal needs a daily Sharpe of 0.5 (11 times the best).
- Reality check: the same search on data with every variant's edge removed (demeaned, block bootstrap, common resampling) finds a best daily Sharpe of +0.098 (median), +0.132 (95th percentile). The real best (+0.046) is BELOW what pure selection luck produces: the real variants are worse than zero-edge because of costs.
- Engine control: a long-only intraday position (flat overnight) earns +5.5 USD/day on gold and +29.2 on NSDQ per 100K in DEV, as expected (the drift sits mostly overnight), so the engine is not broken.
- With the stat-arb (R), macro events (V), the daily and hourly panels (K, K2, K3) and the 1,131-EA screen, every source of a high daily Sharpe reachable on MT5 broker CFDs at MT5 broker's sizes has now been tested and is closed. A system with P(pass by 30 Oct) >= 70% does not exist in this data; replacing the gold pair with anything found here would LOWER the odds (the pair is the best thing tested: daily Sharpe 0.24 in its best regime against <= 0.05 for every factory variant).
