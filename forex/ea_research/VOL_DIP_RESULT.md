# Family VD result: implied-vol regime vs ManualDip trade returns (2026-10-12)

Pre-registration: PREREG_VOL_DIP.md. Unit = decision day (mean bp over the indices that signalled), DEV 68 days (2022-24), VAL 28 (2025), HOLD 18 (2026, not opened).

| Feature (prior close) | DEV high / low (bp) | DEV t | VAL diff (bp) | VAL t | Accepted |
|---|---|---|---|---|---|
| VIX (split at DEV median 20.8) | +18.8 / -1.2 | 0.66 | +101 | 1.27 | no |
| VIX9D/VIX3M > 1.0 (backwardation) | +41.5 / -2.1 | 1.06 | +69 | 0.67 | no |
| SKEW (split at DEV median 134.5) | +1.5 / +16.2 | -0.48 | -228 | -1.22 | no |

## Verdict: not detectable. ManualDip stays exactly as it is; 2026 not opened; no gating rule.
With 68 DEV signal-days the test has little power, so this is "not detected", not "no effect". The VIX and backwardation splits point the same way (higher fear, better dips) in both DEV and VAL, but at t of 0.7-1.3 that is a hint at best. It can be revisited as a forward-only check once ManualDip has live signals (it now trades live; the live log is the clean sample).
