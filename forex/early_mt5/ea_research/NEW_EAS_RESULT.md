# Families IM and GS result (2026-10-12)

Pre-registration: PREREG_NEW_EAS.md. MT5 broker M1 bid/ask, spread paid on every fill.

| Trial | DEV 2022-24 | VAL 2025 | HOLD | Verdict |
|---|---|---|---|---|
| IM last-half-hour momentum (SP, NSDQ, DOW) | **-1.92 bp/day, t -2.18** (741 days) | -1.41, t -0.93 | not opened | fail: the sign is negative |
| GS gold/silver ratio reversion | +169 bp/trade, t 2.37 (**16 trades**) | **-785 bp** (4 trades) | not opened | fail: 16 < 20 trades, VAL loses |

## Verdict: neither passes, hold-out unopened.
IM: the momentum direction loses after the spread, and significantly so in DEV. Fading it would pay the same spread twice over a gross effect of only about 1 bp, so the mirror image is not an edge either and is not tested (that would be choosing the sign after seeing the data).
GS: 16 DEV trades in three years is too few to say anything; the 2025 loss (4 trades, -785 bp each on average) shows why a spread trade with fat tails is not usable as-is: when the gold/silver ratio keeps trending it keeps losing.
