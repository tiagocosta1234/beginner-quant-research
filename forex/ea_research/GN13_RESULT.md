# GN13 result - bond-trend-aligned breakouts: a near miss on the indices that flips sign with the stock-bond regime (0 of 3)

Run 2026-10-18 15:01 local (local clock, second PC PC-2). Pre-registration `PREREG_GN13.md` (commit 194f3261), engine `gn13.py`,
dry run `GN13_DRYRUN.txt` (truncation PASS x3, futures port check 100% same side), output `GN13_OUTPUT.txt`.
Rule: one-sided session breakout in the direction of the 10-year note trend (ZN close of the day before vs its 20-day mean;
bonds up = yields falling = long). Net R a trade, MT5 broker bid/ask; OOT = CME futures 2020-21 with the MT5 broker cost model.

| trial | DEV 2022-24 | info over aligned random (t) | misaligned DEV | VAL 2025 (misaligned) | OOT 2020-21 (misaligned) | verdict |
|---|---|---|---|---|---|---|
| B1 NSDQ 09:30 box | +0.150 (t 2.34), n 470 | +0.104 (1.38) | +0.049 | +0.222, t 1.62 (-0.035) | -0.021 (+0.144) | FAIL |
| B2 SP 09:30 box | +0.152 (t 2.02), n 509 | +0.097 (1.09) | +0.050 | +0.152, t 1.24 (-0.136) | -0.060 (+0.157) | FAIL |
| B3 XAUUSD 08:20 box | +0.011 (t 0.16), n 513 | +0.040 (0.54) | +0.016 | +0.166, t 1.51 (-0.150) | -0.120, t -1.77 (+0.053) | FAIL |

The 2026 hold-out stays sealed. B1 missed DEV only on the information bar (t 1.38 < 1.65) and VAL by t 1.62 < 1.65.

## What it shows
- **On the indices the bond trend picked the better side in 2022-25** (aligned beats misaligned by +0.10 R in DEV and by +0.26 /
  +0.29 R in 2025, every DEV year positive for NSDQ) **and the wrong side in 2020-21** (aligned -0.02 / -0.06 vs misaligned +0.14 /
  +0.16). That is the stock-bond correlation regime: before 2022 bonds rallied when stocks fell (flight to quality), so "bonds up"
  meant risk-off; since the 2022 inflation shock bonds and stocks move together, so "bonds up" means risk-on. The filter is a proxy
  for the correlation sign, not a stable edge.
- Much of the aligned gain is the direction itself: aligned random entries also earned +0.05 R, so the breakout's own timing adds
  only +0.10 R (t 1.1-1.4).
- Gold: nothing in DEV, wrong-signed out of time (-0.12 R, t -1.8): the gold / real-yield link broke after 2022, as the prior said.
- A conditional version (follow the bond trend only while the rolling stock-bond correlation is positive) is a POST-HOC idea from
  these results; with the 40 variants of this window used, it belongs to a new window and would be decided on the 2026 hold-out.

## Account view (2022-25 trades, from 95,472, MT5 broker rules)
B1 at $500 a trade: 0.1% pass / 13% breach by 22 Dec, 19.6% / 26% by 30 Jun 2027; B2 19.9% / 45%. Nothing quick, nothing with
pass > breach.

## Running count
GN1-GN13: 40 of 40 variants of this research window used, 0 passes. **The window is closed.**
