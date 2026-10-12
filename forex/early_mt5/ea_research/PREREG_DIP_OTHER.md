# Pre-registration: ManualDip rule on commodities and FX majors (written 2026-10-12, before any non-index signal was evaluated)

the trader: "avança" on extending the dip-reversal, our only non-gold edge. The rule is FROZEN exactly as ManualDip.mq5 / `dip_addon.py` (DA_Z = 1.5): decision at 15:49 New York on the daily series of that bar's close, z3 = 3-day log return / (sigma60 x sqrt 3) <= -1.5, entry the next minute at the ASK, Mon-Thu entries, stop at 3 sigma, exit the next trading day, per-trade return in bp = pl / (q x e) x 1e4 (sizing cancels out). Same 15:49 New York clock for every asset (no per-asset tuning). Data: MT5 broker M1 bid/ask, `data_mt5`, 2021-12 .. 2026-10-02.

## Groups (3 trials, fixed now)
- DD1 metals: XAUUSD+, XAGUSD+. DD2 energy: WTI+, BRENT+. DD3 FX majors: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD.
- Control DD0 (informational, not a trial): the four indices ManualDip already trades, to confirm the machinery reproduces the known positive DEV result.
- Unit = decision day: trades of the same group on the same date are averaged into one observation.

## Acceptance per group
DEV (entry dates 2022-01-01 .. 2024-12-31): >= 25 signal-days, mean >= +10 bp, one-sided t >= 1.65. VAL 2025: mean > 0. HOLD-OUT 2026-01-01 .. 2026-09-30 (one look, accepted groups only): mean > 0.
Gold is already in the live book through SDB and XAU5, so a DD1 pass would also need its correlation with the pair checked before it is a diversifier. Nothing goes live from this round.

## Honest prior
Low to moderate. The index dip works because equity indices mean-revert after short sell-offs (leverage and flow); metals, energy and FX majors are driven by other flows and FX in particular trends. Crypto showed only a noisy positive (CD1/CD2). Trials DD1-DD3 (DEV, VAL).
