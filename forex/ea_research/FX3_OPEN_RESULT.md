# FX3-OPEN result (2026-10-14): regional equity-session lead into EURUSD / GBPUSD / USDJPY

Pre-registration `PREREG_FX3_OPEN.md`, engine `fx3_open.py`, output `FX3_OPEN_OUTPUT.txt`. 14 cells, 0 survivors. The 2026 hold-out was NOT opened.

## Verdict: nothing; closed
- Permutation calibration (200 draws, side shuffled across days): max |t| over the 14 cells in DEV has median 2.22 and 95th percentile 3.04; the registered bar was 2.9, so the effective bar is 3.04.
- Real DEV: best |t| 1.74 (GBPUSD after the SP open, 4 h, +1.64 bp), below the noise ceiling. In VAL (2025) that cell is -2.30 bp, t -1.95; the three EURUSD/GBPUSD SP cells that were positive in 2022-24 are all negative in 2025.
- USDJPY (Nikkei, DAX, SP drivers): net -0.5 to -1.5 bp in DEV and VAL; the transfer is not there.
- Reversed sign (traded the opposite way): +0.4..+0.8 bp for USDJPY after SP/DAX at 4 h, -1..-2.5 for EUR/GBP: also inside the noise and not registered as a trade.
## Reading
The first hours of the regional equity session do not lead the three FX pairs at 2-4 h horizons after the 0.8-0.9 bp round-trip cost. Together with FX3_MAP.md: price-only information from MT5 broker's own markets is exhausted for these pairs (hourly/daily features, ticks, calendar surprises and now session transfer). No EA. Live pair unchanged.
