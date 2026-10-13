# Family S (2026-10-09 23:54 local): our own GoldenShot-style micro-scalp - three trials, all fail (ledger 72 -> 75)

Pre-registration `PREREG_MICRO_SCALP.md` (23:55, before any model was fitted), diagnostic `gs_mechanics.py` (GS_MECHANICS_OUTPUT.txt), runner `micro_scalp.py`, output `MICRO_SCALP_OUTPUT.txt`, ledger rows `micro_scalp`. Data: 139 Monday-Thursday days of MT5 broker real ticks (2025-10..2026-09), 107,162 candidate trades (a candidate every 120 s, both directions) under the fixed exit geometry (stop 20, target 4, trailing from +1.2 at 0.6 distance, 0.3 steps, 30-minute cap, 300 ms entry latency, spread paid through bid / ask). DEV 2025-10..2026-03, VAL 2026-04..2026-09.

## Diagnostic first: the exits are not the edge
Random entries with those exits win 82-83% of the time and lose 0.32-0.43 USD/oz (PF 0.73-0.75), for both strategy geometries and for modification latencies of 0 / 300 / 800 ms. A 95% win rate is therefore not evidence of anything by itself; the EA's tester record (95.6%, +1.7 USD/oz) must come from its entry filter (and its own history-fitted "pre-entry validation"), and its live record (87%, PF 1.01) is about halfway back to the random control.

## Results (mean net USD per oz; the random control on VAL is -0.43)
| trial | DEV (in-sample) | VAL (registered threshold) | verdict |
|---|---|---|---|
| S1 logistic regression, top 20% by score | -0.57 | n 1,458, -0.378, win 87.8%, PF 0.77, daily t -2.64 | fails |
| S2 gradient boosting, top 5% | +0.36 (n 1,209, win 93.7%, PF 1.36) | n 760, -0.228, win 88.0%, PF 0.85, t -1.21 | fails: fitted in DEV, gone in VAL |
| S3 hand rule (pullback inside a trend) | -0.37 | n 2,396, -0.310, PF 0.79, t -3.30 | fails |
Even in-sample the best model reaches +0.36 USD/oz, a fifth of what the EA's tester shows (+1.7): the 18 price features (returns, ranges, position in range, ATR, EMA gap and slope, hour, spread, direction) contain no tradable information for the +4 / -20 geometry, or the EA's filter uses something these features do not capture. Cost stress (+0.3 USD/oz) makes every VAL result worse. No hold-out was needed.

## Reading
We can build the EA's mechanics (the exits, the windows, the cooldown, the one-position rule) in a day; we cannot build its edge, because on 12 months of real ticks no simple or boosted entry filter beats random entries by more than noise. The 62 + 3 + 7 earlier and later trials say the same: the entry rule is where the edge is not. What public evidence supports is the opposite reading of the EA's tester record: a very high in-sample win rate produced by exits with a 17:1 stop-to-target ratio plus a filter tuned on history, and a live record of break-even. Next possible evidence, free: re-read the author's live signal in 8-12 weeks.
