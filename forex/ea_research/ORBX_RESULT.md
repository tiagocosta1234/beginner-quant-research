# ORBX result - London opening-range breakout + news-day / trend filters: 0 of 3 pass

Run 2026-10-16 ~15:05 local, pre-registration `PREREG_ORBX.md` (commit b819d99d), script `orbx.py`, output `ORBX_OUTPUT.txt`.
38 non-crypto MT5 broker, 45,250 trades 2022-01-03..2026-10-02, real bid/ask fills, R per trade, t clustered by day.

| Trial | DEV 2022-24 net (t) | gross | placebo 95% | VAL 2025 net (t) | 2026 info net (t) | Verdict |
|---|---|---|---|---|---|---|
| BASE (yardstick) | -0.049 (-4.7), n 28,600 | +0.023 | - | -0.076 (-4.5) | -0.040 (-1.9) | - |
| N news day | +0.031 (+0.6), n 1,353 | +0.078 | +0.026 | -0.054 (-0.9) | +0.011 (+0.1) | FAIL (t < 2.4) |
| T trend agreement | -0.061 (-4.2), n 14,314 | +0.013 | -0.040 | -0.093 (-3.9) | -0.026 (-1.0) | FAIL (negative) |
| NT both | +0.058 (+1.0), n 689 | +0.118 | +0.048 | -0.036 (-0.4) | -0.058 (-0.5) | FAIL (t < 2.4) |

Reading:
- News days do raise the gross edge (+0.08..+0.12R vs +0.02R) and lift the net to slightly positive in DEV, but with
  t 0.6-1.0, barely above random same-size subsets, and negative in VAL 2025. Not an edge.
- Agreeing with the previous day's direction makes it worse than the base rule (gross +0.013 vs +0.023).
- The base rule pooled over 38 markets loses about 0.05R per trade after the real spread in every period.

Per the kill rule the London opening-range breakout family is closed for this account (about 18 of 40 variants used
in this window). Nothing here changes CURRENT_STATE: D2 remains the only validated plan.
