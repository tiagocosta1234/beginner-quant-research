# Pre-registration: does an implied-vol regime (CBOE GVZ, VIX term structure, SKEW) predict the gold pair's daily P&L? (written 2026-10-12, before any outcome was looked at)

Source of the data: CBOE history CSVs fetched with the Fincept Terminal's key-free CBOE endpoint (`D:\finance\data_macro\cboe\*.csv`, 2008-2026). New to us: we only held VIXCLS before.
Question: if a regime separates the pair's good days from its bad days, risk could be scaled by it. If not, nothing changes.

## Test (3 trials, fixed now)
- Outcome: daily net P&L V of the final pair at x1.5 with the news-flat rule and a 1,500 USD guard, FT pool (MT5 broker real-tick trades re-priced on MT5 broker specs), 2022-01-03 .. 2026-09-30, exactly `combo_grid.pair_series("FT", 1.5, 1.5, 1500)`. ManualDip not included. Every weekday row of that series, zero days included.
- Features, each taken from the LAST CBOE observation strictly BEFORE the trading day (causal): F1 GVZ close; F2 VIX9D / VIX3M close ratio (short-term stress vs 3-month); F3 SKEW close.
- Split: HIGH = feature above its DEV median (DEV = 2022-2024 days; median computed on DEV only), else LOW. Statistic: mean V(HIGH) - mean V(LOW), Welch t.
- Acceptance per feature: DEV |t| >= 2.4 (about p<0.017, Bonferroni for 3), AND VAL 2025 difference has the SAME sign and at least half of the DEV difference in size, AND the 2026-01..09 hold-out (one look, only for accepted features) has the same sign.
- If none is accepted the round ends with no sizing rule and no live change. If one is accepted, a SEPARATE pre-registration defines the sizing rule and its test; nothing goes live from this round.

## Honest prior
Low. Gold's daily range already scales with its own vol and the pair is sized in dollars, so the regime mostly changes variance, not mean. Trials logged as VR1-VR3 (DEV), VR1-VR3 (VAL), plus HOLD rows only if opened.
