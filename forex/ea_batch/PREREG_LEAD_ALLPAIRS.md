# Pre-registration: the mirrored "JFatl breakout" lead on all 28 FX pairs

Written 2026-10-08 ~19:20 local, BEFORE any result for other pairs exists. Requested by the trader ("(original wording omitted)"). **AMENDED 19:35, still before any result for another pair: the trader asked for MT5 broker's data ("(original wording omitted)"), so every step below uses MT5 broker's server (symbols with the + suffix, e.g. GBPUSD+) and MT5 broker's bars; my first draft said MT5 broker. The only runs done before the amendment are the 3 GBPUSD validation runs on the MT5 broker terminal (Model 2), kept only as a method check.**

## Question
The lead (mirror every entry of Exp_JFatl_Digit_System, H4, default inputs, with TP / SL exits) made +3.7k / +6.5k / +3.8k a year at 0.10 lot on GBPUSD in 2023-25 (lesson 41) and -310 in 2026 (profit factor 0.97). Is that a property of the signal on FX in general, or noise from searching 1,220 EAs?

## Design
1. **Entries**: the original EA (`ea_batch\15888`, default inputs, H4) run in the MT5 tester on each of the 28 FX pairs for 2022, 2023, 2024, 2025 and 2026 (to 2026-09-30) on the PORTABLE MT5 broker tester terminal (`data\mt5_mt5_tester`, MT5 broker-Server, symbols `<PAIR>+`; the live terminals are never touched). Model = 2 (open prices only): the EA decides on closed H4 bars, so entries should not depend on ticks. **Validation first**: GBPUSD+ 2023-25 entries on MT5 broker (Model 2) are compared with the stored MT5 broker real-tick entries (`results_inv_<year>/15888.csv`): >= 90% of them must exist on MT5 broker with the same side within one H4 bar (the two feeds differ a little, so exact equality is not expected); otherwise the study stops and says so.
2. **Mirror simulation** (unchanged from `inv_realize.py`): opposite direction at the next minute's ask / bid from MT5 broker's own M1 bars (`copy_rates_range`: bid OHLC, ask = bid + the bar's spread; MT5 broker has no ticks before 2025-09, so the bars are exported once into `forex/data_mt5/<PAIR>_M1_rates.parquet`; the approximation is checked against MT5 broker's tick-built gold bars first), exit at TP / SL pips or after 60 days, commission 0.6 pip per round trip. Result in PIPS (JPY pairs: pip = 0.01, others 1e-4); USD values at 0.10 lot only for the pairs quoted in USD.
3. **Grid**: TP {10, 20, 40, 80} x SL {20, 40, 80, 160}, 28 pairs => k = 448 cells.
4. **Discovery years 2023-25** (as in lesson 41). A cell is a DISCOVERY if: net pips > 0 in EACH of 2023, 2024, 2025; pooled per-trade t >= 3.7 (one-sided Bonferroni 5% for k = 448); no single day carries > 50% of the profit; at most 20 positions open at once.
5. **Hold-outs 2022 and 2026** (never used to choose anything). A discovery is **CONFIRMED** only if net pips > 0 in BOTH 2022 and 2026 and the profit factor over the two is >= 1.10.
6. **Reported regardless**: discoveries / confirmations per pair and per cell, the expected number of false discoveries under pure noise (448 x one-sided p for t = 3.7 is < 0.05, but the t-statistics are inflated by overlapping positions, so the confirmation is the real test), GBPUSD 40/160 in 2022 (the hold-out that was never run), GBPUSD in 2026, and a pooled "all pairs, all cells" table of hold-out pips versus discovery pips.

## Decision rules
- If **no** cell is confirmed: the lead is closed as noise / GBPUSD-and-2023-25 specific, and it leaves the plan for good.
- If **one or more** cells are confirmed: report them with their hold-out numbers and the stop-out / concurrency caveats; nothing is added to the live plan without a floating-equity MT5 broker replay and the trader's decision.
- A confirmation on 2022 + 2026 for GBPUSD alone does not make a lead: the 2026 result already known (-310) is a failure, so GBPUSD can only be confirmed if 2026 turns out positive in the cell it is judged on.

## Limits
Model 2 entries are assumed equal to real-tick entries after the validation above; MT5 broker bars with a modelled ask side (MT5 broker has no ticks before 2025-09 and the approximation is not re-checked on FX ticks); the original EA's own exits are ignored, only entry times and directions are used; the 2026 batch run of the original EA had its own stop-out dynamics, so 2026 entries are not identical in regime to the earlier years.
