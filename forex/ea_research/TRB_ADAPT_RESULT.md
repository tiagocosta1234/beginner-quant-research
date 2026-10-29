# TRB-ADAPT (2026-10-15 ~11:35 local): can a trader who keeps adapting catch each year's best breakout? No.
the trader: "on 2024 a type of breakout, on 2025 a better one, 2026 the same; the markets never stay the same, we're the ones that need to adapt". Script `trb_adapt.py` (cache `data\tmp\trb_cache_2026`, 46 markets x 2,808 breakout variants, 2022-01..2026-10-02; 2026 already open for breakouts), table `data\si_ledgers\TRB_ADAPT.csv`.

1. **The prize (hindsight):** each year's best variant per market averages +0.224 R a trade (2022), +0.248 (2023), +0.204 (2024), +0.159 (2025), +0.209 (2026). the trader is right that every year has a good breakout, and that it is a different one.
2. **Persistence:** rank correlation across variants between the last L months and the next month is +0.16 (L 1), +0.23 (3), +0.27 (6), +0.30 (12). It is positive because COSTLY variants stay bad (tight stops on wide spreads lose every month), not because winners keep winning: see 3.
3. **The adaptive trader** (every month, per market, switch to the best variant of the last L months, or the average of the top 20, and trade it next month), net R per trade, all markets pooled:

| rule | 2023 | 2024 | 2025 | 2026 | months positive |
|---|---|---|---|---|---|
| best of last 1 month | -0.168 | -0.237 | -0.268 | -0.246 | 1 / 46 |
| best of last 3 months | -0.084 | -0.188 | -0.184 | -0.197 | 3 / 46 |
| best of last 6 months | -0.113 | -0.143 | -0.159 | -0.181 | 1 / 46 |
| best of last 12 months | -0.050 | -0.121 | -0.150 | -0.146 | 5 / 46 |
| top-20 average, last 1 / 3 / 6 / 12 months | -0.174 / -0.131 / -0.112 / -0.084 (2023) ... all negative every year | | | | 0 / 46 |

Reading: adapting at any speed loses in every year, and by MORE than trading a fixed variant (the recent winner is usually a high-variance variant that just got lucky). The year's best breakout exists only after the year; it cannot be identified while it is still working, at 1, 3, 6 or 12 months of look-back. This closes the adaptive-selection idea for breakouts on MT5 broker data (TRB monthly 3/6, ORB-REFINE regime rules, TRB-BEST yearly, TRB-ADAPT all speeds).
