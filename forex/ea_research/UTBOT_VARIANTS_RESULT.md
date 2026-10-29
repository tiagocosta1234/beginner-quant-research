# UTBOT-VARIANTS result (2026-10-14): Key Value 2, Key Value 3, Heikin Ashi on, 46 symbols x 8 timeframes
Pre-registration `PREREG_UTBOT_VARIANTS.md`, engine `utbot.py --variants`, output `UTBOT_VARIANTS_OUTPUT.txt`, cells `data\tmp\utbot_variant_cells.csv` (1,104 cells; 1,472 tests with the default run). 2026 hold-out unopened.
## Verdict: no candidate in any variant
- Placebo (100 random shifts per cell): max t over the 1,104 cells has median 2.87, 95th percentile 3.38; the registered bar was DEV t >= 4.1. Best real DEV t: +2.44 (GBPJPY H4, Heikin Ashi: +16.7 bp per trade in DEV, -2.2 in VAL).
- Cells positive in both periods: HA 3.3%, K2 4.9%, K3 7.9% (the share rises with the Key Value only because fewer trades pay fewer spreads); median net per trade -1.7 to -2.1 bp in DEV and -1.7 to -1.8 in VAL for all three variants.
- The best validation cells (XAUUSD H4 K3, NIKKEI H4 K3: about +56 / +69 bp per trade in 2024-25 on 76-78 trades; XAUUSD H4 HA) have DEV t of 0.3-1.0 and are the gold/index bull market of 2024-25 caught by a slow trend flip, the same mechanism as the gold pair, not a new edge.
- Together with `UTBOT_RESULT.md`: UT Bot Alerts shows no edge on any of the 46 MT5 broker symbols at any intraday timeframe, with default or looser (K2/K3) or smoothed (Heikin Ashi) settings; FX pairs lose the spread on every flip.
Nothing goes to multi_fx_ea. No further variants (kill rule).
