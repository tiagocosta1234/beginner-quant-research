# ANALOG result (2026-10-14 ~21:50): chart pattern memory over all 46 MT5 broker - NO EDGE
Pre-registration `PREREG_ANALOG.md` (commit 73b2cdbb), engine `analog.py`, cells in `data\si_ledgers\ANALOG_cells.csv`. 2026 never loaded.

## Dry-run
46 markets (the pre-registration said 45; corrected before any P&L, nothing else changed), 149,540 decision marks 2021-12..2025-12, about 93k DEV and 38k VAL queries per cell. Truncation test PASS (shapes and vol before a cut unchanged on EURUSD, XAUUSD, SP, BTCUSD), library causality assert passed in every monthly batch, hand check matches the raw M1 bid/ask.

## Cells (net, sigma units per trade; t on the daily portfolio, Newey-West lag 2)
| cell | DEV n | DEV net | DEV t | VAL net | VAL t | placebo worlds 91-93 DEV t |
|---|---|---|---|---|---|---|
| W12-H4 | 26,352 | -0.137 (-19 bp) | -12.6 | -0.076 | -6.2 | -13.3 / -12.1 / -12.6 |
| W12-H22 | 26,296 | -0.065 (-21 bp) | -8.4 | -0.025 | -1.3 | -7.4 / -5.8 / -7.1 |
| W48-H4 | 29,317 | -0.161 (-22 bp) | -13.1 | -0.057 | -4.2 | -11.7 / -11.9 / -12.3 |
| W48-H22 | 32,802 | -0.064 (-22 bp) | -6.4 | -0.005 | -0.3 | -4.6 / -6.1 / -6.6 |

The engine printed "PASS True" for W48-H4 (all five gates met in the negative direction: |t| 13.12 just above the placebo 95th percentile 12.91, below the placebo maximum 13.30). **That pass is an artefact of the two-sided gate applied to net returns, not a finding**: a negative net mean caused by the spread does not turn positive when the trade is reversed, because the fade pays the same spread. Diagnostic (run after, no new cell; `data\scratch\bracket2k\analog_diag.py`):
- W48-H4 gross mid-to-mid P&L: DEV +0.0045 sigma per trade (t +0.11), VAL +0.013 (t +1.17). The fade's net: DEV -0.170 (t -13.8), VAL -0.083 (t -6.5). Both directions lose; the vote carries no information.
- Crypto alts (MT5 broker spreads of 60-100 bp) make most of the loss: crypto net about -0.6 sigma, -90 bp per trade. FX, indices and metals are also negative net in both directions (FX fade -0.048, t -3.9).
- The only positive gross corner, W12-H4 FX DEV +0.035 sigma (t +2.70), is -0.008 in VAL and below the FX spread in both periods.
- The placebo worlds (labels shuffled in time) score the same t as the real library, so the size of the t statistics comes from cost, not from patterns.

## Reading
Pooling every market and reading the chart as a whole shape (12 or 48 hours, normalised by volatility) instead of indicators does not predict the next 4 or 22 hours: the 50 nearest past shapes vote no better than shuffled labels, and the mid-to-mid P&L is zero to the second decimal on 29-33k DEV trades per cell (power: SE about 0.01 sigma, so +0.03 would have shown). Closed; HOLD stays sealed. Lesson for the protocol: a two-sided gate must be applied to the GROSS (mid) P&L, or the fade direction must be computed with its own costs, before a negative net cell is read as "fade works" (the same reading was applied correctly in GOLD-FIX by hand).
