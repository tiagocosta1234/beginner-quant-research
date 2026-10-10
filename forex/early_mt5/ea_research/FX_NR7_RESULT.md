# F2: NR7 breakout on the 28 MT5 broker FX pairs: result (15:13 local, 2026-10-09)

Pre-registration `PREREG_FX_NR7.md`, simulator `fx_nr7.py`, output `FX_NR7_OUTPUT.txt`, trial ledger `LEDGER.csv` (family fx_nr7). Ledger now 39 of 40. The 2026 hold-out was NOT opened.

## Verdict: FAILS acceptance 1, 2 and 3 (strongly negative); idea closed as registered
| period | trades | mean R | PF | daily t | win | pairs with mean > 0 |
|---|---|---|---|---|---|---|
| DEV 2022-24 | 2,586 | -0.173 | 0.72 | -4.73 | 32.6% | 4/28 |
| VAL 2025 | 893 | -0.305 | 0.53 | -5.78 | 30.9% | 2/28 |
| 2022-25 pooled | 3,479 | -0.207 | 0.67 | -6.76 | 32.2% | 4/28 |
Registered bars were DEV mean > +0.05, PF >= 1.10, t >= 2.24 and 18/28 pairs: none is close.

## Reading (CORRECTED later the same afternoon, see the diagnostic below)
- First reading, WRONG: 'NR7 breakouts reverse'. The mirror rule F2m (PREREG_FX_NR7_FADE.md) also lost (DEV -0.162 R, VAL -0.243 R, t -4.8 / -4.2), so the loss is not a direction effect.
- Diagnostic (post-hoc, NOT a trial, ledger rows DIAG-*): mean spread at the entry bar 9.5 bp of the price (median much lower), at the exit bar 3.5 bp; mean result per trade -10.7 bp; CORRECTED 2026-10-09 15:47: mid-to-mid gross (adding back ONE spread = half at each fill, plus 0.4 bp slippage) is about -3.8 bp for the continuation rule and -2.1 bp for the fade rule, i.e. no edge in either direction (the first version added back two spreads and read +2.3 / +3.6 bp). Orders on a narrow-range day trigger mostly at the open of the day, around the rollover hour, where the ask jumps on a spread spike and the fill is wide; all 1,420 time exits fall in hour 23 server time (last bar of the day, spreads starting to widen). The registered execution bleeds spread; there is no gross edge to rescue.
- Disclosure: the mechanics smoke test printed the whole-period (2021-12..2026-10) mean R of EURUSD alone (+0.075 R), which includes the 2026 months for that one pair; it was not used for any decision.
