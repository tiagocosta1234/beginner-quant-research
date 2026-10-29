# Family VR result: implied-vol regime vs the gold pair's daily P&L (2026-10-12)

Pre-registration: PREREG_VOL_REGIME.md. Data: CBOE history (GVZ, VIX9D, VIX3M, SKEW), fetched through the Fincept Terminal's key-free CBOE endpoint. Outcome: pair x1.5 daily V, FT pool, 1,225 days, 2022-01 .. 2026-09.

| Feature | DEV high-low (USD/day) | DEV t | VAL 2025 diff | VAL t | Accepted |
|---|---|---|---|---|---|
| GVZ (gold implied vol) | -4 | -0.10 | +148 | 2.24 | no |
| VIX9D / VIX3M | +40 | 1.02 | +110 | 1.32 | no |
| SKEW | +46 | 1.19 | -309 | -2.70 | no |

## Verdict: no regime separates the pair's days. The 2026 hold-out was not opened, no sizing rule is defined, nothing changes live.
DEV never reaches the |t| >= 2.4 bar. The 2025 swings (GVZ +148, SKEW -309 with t 2.2-2.7) are one year of noise: SKEW flips sign against DEV. As the prior said, the pair is sized in dollars and a vol regime mostly changes variance, not the mean.

Data kept for later use: `data\data_macro\cboe\` (VIX, VIX9D, VIX3M, VIX6M, VVIX, SKEW, GVZ, OVX, VXN, VXD, VXEEM, VXEFA daily history, to 2026-10-09).
