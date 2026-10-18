# GN9 result - no late-day continuation on big-move days; on US indices the last half hour REVERSES the day (0 of 3)

Run 2026-10-18 14:38 local (local clock, second PC PC-2). Pre-registration `PREREG_GN9.md` (commit 43b21d5e), engine `gn9.py`, dry run
`GN9_DRYRUN.txt` (truncation PASS, futures port check 97-98% same side), output `GN9_OUTPUT.txt`.
Hypothesis (Baltussen et al. 2021; leveraged-ETF rebalancing): on days whose move from the previous close to 15:29 (ROD) is in the
top quartile of the last 250 days, the last half hour continues in the direction of the day. Net R a trade, R = 2 x the 14-day
mean last-half-hour move (stop), MT5 broker bid/ask; OOT = CME futures 2020-21 with the MT5 broker cost model.

| trial | DEV 2022-24 | info (t) | other days DEV | VAL 2025 | OOT 2020-21 | verdict |
|---|---|---|---|---|---|---|
| L1 NSDQ 15:30-15:58 | -0.145 (t -2.92), n 154 | -0.063 (-1.08) | -0.025 | +0.047 (n 60) | -0.206 (t -2.86), n 77 | FAIL |
| L2 SP 15:30-15:58 | -0.058 (t -0.92), n 156 | -0.043 (-0.60) | -0.018 | -0.179 (t -2.31) | -0.396 (t -5.09), n 61 | FAIL |
| L3 XAUUSD 13:00-13:28 | -0.009 (t -0.16), n 192 | +0.010 | -0.056 | +0.013 | +0.010 | FAIL |

The 2026 hold-out stays sealed.

## What it shows
- **The published late-day momentum is absent; on US indices the opposite appears.** On big-move days the last half hour went
  AGAINST the day in 2022-24 on MT5 broker (NSDQ -0.145 R, t -2.9) and in the 2020-21 futures (NQ -0.21, t -2.9; ES -0.40, t -5.1),
  and the bigger the day, the stronger the reversal (futures NQ by |ROD| / threshold: +0.07 / +0.08 / -0.12 / -0.20 / -0.22 R;
  MT5 broker NSDQ: -0.02 / +0.01 / -0.10 / -0.09 / -0.10). On normal days it is about zero. 2025 is mixed (NSDQ +0.05, SP -0.18).
- Possible mechanisms for the reversal (not tested): since 2020-22 zero-day options leave dealers net LONG gamma into the close
  (they sell rallies and buy dips), and closing-auction imbalances are published at 15:50 and absorbed. Leveraged-ETF flows, if
  they still move prices, are smaller than these.
- Gold's COMEX last half hour is noise (-0.01 R on big days; the very largest days +0.11 MT5 broker / +0.09 futures, few trades).
- The reversal is a POST-HOC observation: these data were used to see it, so they cannot confirm it. Any test of it must be
  decided on data not yet seen (the MT5 broker 2026 hold-out), written down before that look.

## Account view (2022-25 trades, from 95,472, MT5 broker rules, R = 2 S)
All three lose or break even (-0.09 / -0.09 / -0.00 R); 0% pass at every date, 24-38% breach by 30 Jun 2027 at $500.

## Running count
GN1-GN9: 30 of 40 variants of this research window used, 0 passes.
