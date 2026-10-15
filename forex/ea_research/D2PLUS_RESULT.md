# D2PLUS_RESULT - four refinements of D2 from the trader's 50-hypothesis list (2026-10-15, local clock 19:01)
Pre-registration PREREG_D2PLUS.md; code d2plus.py; output D2PLUS_OUTPUT.txt. Truncation test passed.

## Verdict: none improves D2; D2 stays unchanged
USD a day per 100k gross (2026 = HOLD, context only):
| variant | 2020-21 | 2022-24 | 2025 | 2026 | DEV+VAL t | difference vs D2 (USD/day, t) | corr with D2 |
|---|---|---|---|---|---|---|---|
| D2 (base) | +24.5 | +30.2 | +87.5 | +50.6 | 2.42 | - | - |
| P41 breadth (flat if < 3 of 5 above SMA200) | +18.3 | +29.4 | +77.2 | +45.8 | 2.37 | -4.2 (t -0.95) | 0.95 |
| P42 correlation-adjusted weights | +20.5 | +28.2 | +98.0 | +51.0 | 2.59 | -0.6 (t -0.24) | 0.98 |
| P43 downside-vol weights | +29.1 | +28.8 | +95.7 | +55.0 | 2.48 | +2.1 (t 1.42) | 1.00 |
| P47 hysteresis 1% band on the SMA | +26.1 | +27.8 | +84.0 | +56.6 | 2.30 | -1.3 (t -0.61) | 0.99 |
Bar: DEV+VAL t >= 2.50, OOT > 0 and a paired difference t >= 2.24. P43 is the only one ahead of D2 and only by about 2 USD a day, well inside noise. The variants are 0.95-1.00 correlated with D2: weighting details do not matter for this book; the edge is the long-only trend-filtered drift itself.
