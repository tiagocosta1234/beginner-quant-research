# Pre-registration: does an implied-vol regime improve ManualDip (index dip-reversal)? (written 2026-10-12, before any outcome was looked at)

Follows `VOL_REGIME_RESULT.md` (vol regime does not separate the gold pair's days). ManualDip is the only non-gold edge we have (z3 <= -1.5, Mon-Thu, 3-sigma stop, next-day exit); a classic idea is that dip-buying works better when fear is high / VIX in backwardation. Data: CBOE history in `data\data_macro\cboe\`.

## Test (3 trials, fixed now)
- Outcome: the ManualDip trades exactly as `dip_addon.trades()` / `day_arrays()` with DA_Z=1.5 produce them (SP, NSDQ, DOW, DAX, 2022-2026), per-trade return in bp = pl / (q * e) * 1e4. Trades on the same decision date are averaged into ONE observation (the four indices are strongly correlated, so a day, not a trade, is the unit).
- Features, each = the last CBOE close strictly BEFORE the decision date (VIX closes after the 15:49 NY decision, so same-day is not causal): G1 VIX close; G2 VIX9D / VIX3M close ratio, split at the natural level 1.0 (backwardation) with no tuning; G3 SKEW close.
- Split: G1 and G3 above/below their DEV median (DEV = decision dates 2022-2024, median on DEV only). Statistic: mean bp (HIGH or backwardation) - mean bp (LOW), Welch t on signal-days.
- Acceptance per feature: both groups >= 15 signal-days in DEV, DEV |t| >= 2.4, VAL (2025) difference same sign and at least half the DEV size, and (one look, accepted features only) 2026-01..09 same sign.
- Otherwise the round ends, ManualDip stays as it is. If accepted, a separate pre-registration would define a gating rule; nothing goes live from this round.

## Honest prior
Low to moderate. About 100-200 signal days over the DEV years, so the power is small; a null here means "not detectable", not "no effect". Trials logged as VD1-VD3 (DEV, VAL).
