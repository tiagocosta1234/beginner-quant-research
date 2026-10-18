# GN7 result - 5-minute opening-range breakout on high relative-volume days (CME volume): 0 of 2 pass (2026-10-18 11:20 local, local clock, second PC)

Pre-registration `PREREG_GN7.md` (dfe130b0; amendment 1 before any P&L, 477889eb: in-play = each market's own top 20% RVOL5
days, because RVOL5 >= 1.5 left only 39 NQ DEV trades), engine `gn7.py`, dry runs `GN7_DRYRUN.txt` / `GN7_DRYRUN_A1.txt`,
output `GN7_OUTPUT.txt`. Databento NQ / GC futures with exchange volume, MT5 broker cost model, Zarattini-Aziz rule (first 5-minute
candle's direction, stop at its other end, 10R target, exit 15:55 / 13:25 New York).

| trial | DEV 2020-23 n, mean R (t) | random direction | info (t) | other days | years 20/21/22/23 | VAL 2024-25 n, mean R (t) | verdict |
|---|---|---|---|---|---|---|---|
| Q1 Nasdaq, 09:30 NY | 175, -0.017 (-0.11) | -0.076 | +0.059 (+0.32) | +0.084 | -0.29/+0.22/+0.31/-0.35 | 107, +0.422 (+1.73) | FAIL |
| Q2 gold, 08:20 NY (COMEX open) | 162, +0.242 (+1.11) | +0.084 | +0.159 (+0.60) | +0.017 | -0.03/+0.25/+0.00/+0.66 | 109, +0.305 (+1.10) | FAIL |

The 2026 hold-out stays sealed.

## What it says
- **Real exchange volume does not rescue the Nasdaq opening-range breakout**: on the busiest-open days it earns -0.02 R in DEV,
  less than on ordinary days (+0.08); +0.42 R in 2024-25 on 107 trades is one good stretch (t 1.73), not a pattern.
- **On gold the busy-open days do carry more, but what pays is volatility, not direction.** By RVOL5 band (2020-25,
  descriptive): +0.21 R at 1.5-2.0, +0.30 R above 2.0, about 0 or negative below 1.0; but a RANDOM direction with the same tight
  stop and 10R target also earns +0.08 R on those days. A tight stop with a far target is a long-volatility bet, and it pays
  when a busy open is followed by a big move in either direction. Those days cluster around the 08:30 New York data releases,
  where MT5 broker widens spreads 10-15x and slips stops (`NEWS_GAPS_RESULT.md`, `TICK_GAP_RESULT.md`), which the futures bars with a
  median-spread cost do not model. Not tradeable as measured.
- MT5 broker's MT5 has tick volume, not exchange volume; nothing here would justify the replication.

## Account environment (2020-25 in-play trades, from 95,472, MT5 broker rules)
At most 1.5% pass by 30 Jun 2027 with 13-64% breach. Not usable.

## Running count
GN1-GN6 21 + GN7 2 = 23 of 40 variants in this research window.
