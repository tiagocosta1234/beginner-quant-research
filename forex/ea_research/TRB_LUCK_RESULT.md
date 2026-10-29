# TRB-LUCK result (breakout day round 30, 2026-10-15 13:59, local clock): "a different best breakout every year" is exactly what luck produces
Pre-registration PREREG_TRB_LUCK.md, engine trb_luck.py, table data/si_ledgers/TRB_LUCK.csv. 46 markets x 2,808 breakout variants (TRB grid), day bootstrap within each market-year, 500 draws.
| year | markets | observed yearly prize (best variant, mean R per trade, avg over markets) | average variant (grand mean) | luck, all variants equal: median / 95th pct (p) | luck, stable variant quality: median / 95th pct (p) |
|---|---|---|---|---|---|
| 2022 | 41 | +0.224 | -0.212 | +0.219 / +0.242 (p 0.35) | +0.237 / +0.260 (p 0.86) |
| 2023 | 40 | +0.248 | -0.227 | +0.215 / +0.236 (p 0.01) | +0.247 / +0.269 (p 0.48) |
| 2024 | 46 | +0.204 | -0.266 | +0.176 / +0.196 (p 0.02) | +0.243 / +0.263 (p 1.00) |
| 2025 | 46 | +0.159 | -0.281 | +0.142 / +0.161 (p 0.06) | +0.228 / +0.245 (p 1.00) |
| 2026 | 44 | +0.209 | -0.269 | +0.227 / +0.251 (p 0.89) | +0.275 / +0.297 (p 1.00) |
**5 of 5 years inside the stable-quality null: luck explains the yearly best breakout.**

What this means, in plain words: take 2,808 breakout variants whose quality NEVER changes (the good ones stay good, the bad ones stay bad, nothing is special about any year), let each year's random noise play out, and look back at the end of each year for the best one. You find a variant earning +0.23..+0.28 R a trade, and it is a different variant every year. That is what the real markets show (+0.16..+0.25). Even if every variant had the SAME true quality (-0.21..-0.28 R a trade, the average breakout after costs), luck alone would crown a "best breakout" at +0.14..+0.23 every year.
So the observation "2024 had its type of breakout, 2025 a better one, 2026 another" is real as a description of the past, and it is exactly what 2,808 noisy coin-flippers produce. It does not show that the market changes its breakout type from year to year, and TRB-ADAPT showed that chasing the recent winner loses 0.05-0.27 R a trade every year. Adapting is the right instinct only when there is something real to adapt to; for price-only breakouts on MT5 broker the yearly winners are noise.
