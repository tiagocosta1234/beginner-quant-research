# GN8 result - the VIX regime does not switch the New York breakout on or off (0 of 4)

Run 2026-10-18 14:33 local (local clock, second PC PC-2). Pre-registration `PREREG_GN8.md` (commit c6b20f6d), engine `gn8.py`,
dry run `GN8_DRYRUN.txt` (truncation PASS, futures port check 96-97% same side), output `GN8_OUTPUT.txt`.
Hypothesis: options dealers short gamma on stress days (VIX(d-1) >= 20) make breakouts follow through; long gamma on calm days
makes them revert. Net R a trade, MT5 broker bid/ask; OOT = CME futures 2020-21 with the MT5 broker cost model.

| trial | DEV 2022-24 | info over random (t) | opposite regime DEV | VAL 2025 | OOT 2020-21 | verdict |
|---|---|---|---|---|---|---|
| V1 NSDQ follow, stress days | +0.182 (t 2.12), n 285 | +0.152 (1.62) | calm +0.127 | -0.062 (n 63) | +0.043 (t 0.61) | FAIL |
| V2 SP follow, stress days | +0.212 (t 2.14), n 289 | +0.224 (2.08) | calm +0.118 | +0.007 (n 63) | +0.083 (t 0.97) | FAIL |
| V3 NSDQ fade, calm days | -0.111 (t -2.55), n 442 | -0.066 | stress -0.099 | -0.087 | -0.105 | FAIL |
| V4 SP fade, calm days | -0.088 (t -1.94), n 450 | -0.078 | stress -0.103 | -0.027 | +0.009 | FAIL |

The 2026 hold-out stays sealed.

## What it shows
- **The regime does not matter.** Following the breakout earned about the same on calm days as on stress days in 2022-24
  (NSDQ +0.127 vs +0.182, SP +0.118 vs +0.212, both inside one standard error of each other). By VIX band the Nasdaq follow is
  flat (+0.13 / +0.12 / +0.14 / +0.19 / +0.07 R for VIX < 15 / 15-20 / 20-25 / 25-30 / > 30); the S&P rises to the 25-30 band
  (+0.08 .. +0.25) but the 2020-21 futures do not repeat the slope (-0.18 / +0.06 / +0.08 / +0.04 / +0.13).
- **The stress-day result fails where it should hold:** 2025's stress days (the March-May tariff shock, 63 trades) gave -0.06 /
  +0.01 R, and the 2020-21 futures (2020 was the strongest stress year of the decade) +0.04 / +0.08 R, neither significant.
- **Fading the breakout loses in every regime and period** (-0.03 .. -0.13 R): calm days do not make breakouts revert enough to
  pay the spread. Break vs bounce at the box edge stays a coin flip (as in BRK_TWOWAY), whatever the VIX.
- The positive DEV follow numbers are the known 2022-25 MT5 broker US-index opening breakout (+0.1 R, already shown to fail its 2020-21
  out-of-time check for the Nasdaq trend leg), not a regime effect.

## Account view (2022-25 trades, from 95,472, MT5 broker rules)
Best row V2 at $500 a trade: 0.1% pass / 11% breach by 22 Dec, 7.4% / 30% by 30 Jun 2027. The V1-V4 book at $150: 0.2% / 39%.
Nothing is usable.

## Running count
GN1-GN8: 27 of 40 variants of this research window used, 0 passes.
