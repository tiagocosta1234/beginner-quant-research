# Pre-registration BRK-VOLREG (breakout day, round 3; written 2026-10-15 11:44 local (commit time), before any code or result)
Question: do volume or the volatility regime separate good breakouts from bad ones? Base events = round 1's session stop-order breakouts on 46 markets (same boxes, fills, R = the other side of the box), exit = hold to the session close (round 1's best, X4); 2R reported too. Tick volume = MT5 M1 tick_volume from `data\ticks_vol` (to 2026-08-15; MT5-native, deployable).

## Features (known at the fill)
- rel_vol_fill: tick volume of the 5 minutes ending at the fill minute / median of the same 5 local minutes over the previous 20 session days.
- rel_vol_box: tick volume inside the 30-minute box / median box volume of the previous 20 session days.
- atr_pct: rank of the previous day's ATR14 among the previous 250 days.
- nr4: the previous server day's range is the smallest of the last 4.
- trend: sign(previous close - previous SMA20) (server days, as ORB-REFINE).
"Top tercile" = above the 67th percentile of that feature over the previous 250 events of the same market (causal).

## Cells (6), exit X4 (hold to close), all 46 markets pooled
V1 volume surge at the breakout (rel_vol_fill top tercile). V2 busy box (rel_vol_box top tercile). V3 high-volatility regime (atr_pct >= 0.67). V4 NR4 day before. V5 trend direction (side = trend), every market. V6 trend direction AND volume surge.
## Gates (DEV 2022-24, VAL 2025; 2026 non-clean; volume cells end 2026-08-15)
1. DEV mean >= +0.05 R and t >= 2.4 (daily portfolio NW lag 1; Bonferroni 6). 2. VAL mean > 0 and t >= 1.65. 3. The DEV mean beats the 95th percentile of 1,000 random subsets of the same size drawn from the base DEV events. Reported by class and for indices.
## Honest prior
About 5-8%: "volume confirms the breakout" is the most repeated breakout rule; the trend filter is the only lead carried in (Nasdaq).
