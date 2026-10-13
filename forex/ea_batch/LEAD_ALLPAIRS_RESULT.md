# The mirrored "JFatl breakout" lead on all 28 FX pairs, MT5 broker data (2026-10-08)

Pre-registered in `PREREG_LEAD_ALLPAIRS.md` (amended before any pair result to use MT5 broker data). Code: `lead_allpairs_run.py` (entries), `mt5data_m1_export.py` (MT5 broker M1 bars), `lead_allpairs_study.py` (mirror + rules). Raw: `leadpairs_mt5/` (entries per pair-year, `study_cells.csv`, `study.out`). Bars: `forex/data_mt5/<PAIR>_M1_rates.parquet` (1.1 GB, not for git).

## Method facts
- Entries: the original EA (Exp_JFatl_Digit_System, H4, default inputs) in the portable MT5 broker tester, Model 2 (open prices), symbols `<PAIR>+`, 2022-2026. MT5 broker's symbols accept only IOC fills and the EA's library asks for FOK, so every order was refused; the EA was recompiled in the portable terminal with FOK -> IOC (the only change; signal logic untouched). Without that change the EA never holds a position and its entries differ (refused-order signals are a different, state-free series).
- Validation on GBPUSD against the stored MT5 broker real-tick entries: 2024 99.6% / 100%, 2025 94.0% / 99.2%, 2026 96% / 100% (same side within one H4 bar; the last-entry dates coincide) but **2023 3.7%: the EA went short on MT5 broker (208 sells) and long on MT5 broker (319 buys)**. The pre-registered bar (>= 90% pooled) is therefore NOT met for the discovery years; the study continued on MT5 broker's own entries and says so.
- MT5 broker has no ticks before 2025-09, so exits use MT5 broker M1 bars with ask = bid + the bar's spread. On MT5 broker's tick-built gold bars this is exact on the bid side and 0.02 USD/oz (about 5% of the spread) low on the ask side.
- The EA's entries are almost one-directional inside every pair-year (average share going the same way: 0.94 / 0.97 / 0.93 / 0.91 / 0.95 for 2022-2026), so the mirrored lead is mostly one long or one short position per pair per year: it behaves like a drift/dip trade, not a two-sided signal.

## Result (448 cells = 28 pairs x TP {10,20,40,80} x SL {20,40,80,160})
- Positive in all three discovery years (2023-25): 38 of 448 (pure chance would give about 56). Of those, positive in BOTH hold-outs: 6 (chance about 9).
- Correlation across all 448 cells between discovery pips and hold-out pips: -0.06. The 40 cells with the highest discovery pips earned on average -2,140 pips in the hold-outs (42% positive).
- DISCOVERIES by the pre-registered bar (3 years positive, t >= 3.7, no day with > 50% of profit, <= 20 open): 4. **CONFIRMED in 2022 and 2026: 3** -- NZDCHF 10/160, NZDCHF 10/80, AUDNZD 10/160 (all small-target cells, two related NZD crosses).
  - NZDCHF TP10/SL160: pips per year 2022..2026 = +396, +1,530, +3,487, +2,798, +2,187; win 98%, t 10.4, 17 positions open at most.
  - AUDNZD TP10/SL160: +521, +709, +943, +2,801, +579, win 97%.
- **GBPUSD 40/160 (the original lead) is a discovery on MT5 broker data too** (+805, +5,401, +2,804 pips in 2023-25, t 5.3) but **fails the 2022 hold-out catastrophically: -10,182 pips** (USD 10.2K at 0.10 lot; the EA sold 431 times while GBPUSD fell from 1.35 to 1.07, and the mirror bought every time) and only +453 in 2026. It is NOT confirmed.

## Reading
No broad edge: across 448 cells discovery performance does not predict hold-out performance. The three confirmed cells are one small family (NZD crosses, TP 10) with the same shape as the GBPUSD lead (win rate 97-98%, loss 16x the win): positive in five years here but a single large trend would cost many wins at once. Not tested: floating-equity MT5 broker replay (up to 17 open positions), swap (MT5 broker account is swap-free), position sizing within the 2.5% daily line, the NZD family's dependence on one macro regime. Nothing is added to the live plan.
