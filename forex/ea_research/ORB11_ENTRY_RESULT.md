# ORB11_ENTRY_RESULT - every reasonable ENTRY on the trader's 30-minute London / NY ORB, plus a 2020-21 out-of-time check (2026-10-15, local clock 17:40)
Pre-registrations `PREREG_ORB11_ENTRY.md` (commit f76c848e) and `PREREG_ORB11_ENTRY_OOT.md` (commit 384e1f17). Code `orb11_entry.py`, `orb11_entry_oot.py`; output `ORB11_ENTRY_OUTPUT.txt`, `ORB11_ENTRY_OOT_OUTPUT.txt`; tables `data/si_ledgers/ORB11_ENTRY_*`. Engine checks: truncation identical (6,915 trades), TOUCH 1:1 reproduces ORB11 exactly (EURUSD +0.0434 R).

## Verdict: no entry fixes it. 0 of 826 pools, 0 of 5,924 cells, 0 of 3 out-of-time picks
6 triggers (stop-order touch, 5- and 15-minute close outside, still outside after 15 minutes, retest limit, fade of the failed break) x 6 filters (none, daily trend, box >= 40 spreads, squeeze, box direction, trend + wide) x 2 exits (1:1, hold to the session end), 46 MT5 broker symbols, MT5 broker bid/ask, 557,823 trades and 108,226 random entries.

1. **Trigger hardly matters.** All symbols, 2022-24, 1:1 exit, no filter: London -0.056 (HOLD15) to -0.078 R (RETEST), New York -0.033 to -0.061 R. Waiting for a close outside the box or for a retest does not separate real from false breaks. **Fading the failed break is the worst entry by far** (-0.17 to -0.24 R): the stop at the break's extreme is small, so the spread eats it.
2. **The only filter that matters is box width in spreads (WIDE).** It moves every trigger from about -0.05 to about 0 (1:1) or +0.02..+0.05 R (hold). It is a cost filter: it removes the trades where the spread is a large part of R (BRK_COST and COST_OOS found the same; it breaks even out of sample). Trend, squeeze and box direction add nothing pooled.
3. **Best pooled rules are below the bar:** London TOUCH + WIDE + hold +0.052 / +0.105 / +0.034 R (2022-24 / 2025 / 2026), t 1.84; New York TOUCH + TREND + WIDE + hold +0.056 / +0.001 / -0.004, t 2.39. Bar 3.81. Best session x class pool: New York metals C15 + TREND + WIDE + hold +0.168 / +0.132 / +0.107, t 3.16.
4. **Cells:** highest t 3.34 (NSDQ NY TOUCH + TREND, 1:1); the same search on random entries reaches 3.49. Noise.
5. **Walk-forward (choose the best of 72 rules per symbol-session on 2022-24):** DEV +0.230 -> 2025 **-0.089** -> 2026 **-0.140** R; 9 of 92 cells positive in both. The search picks FADE and HOLD15 + SQUEEZE most often (small samples that look good by chance).
6. **Out-of-time 2020-21 (HistData bid + today's MT5 broker spread), the three per-pool walk-forward picks that stayed positive in 2025 and 2026:**
| pick | 2022-24 / 2025 / 2026 | 2020-21 (one look) | t | 2020 / 2021 | verdict |
|---|---|---|---|---|---|
| P1 London FX, TOUCH + TREND + WIDE, hold | +0.058 / +0.086 / +0.055 | +0.089 R (2,326 trades, 470 days) | 1.13 | +0.029 / +0.150 | FAIL (t < 2.13) |
| P2 London indices, HOLD15 + SQUEEZE, hold | +0.202 / +0.103 / +0.231 | -0.006 R (303 trades) | -0.05 | -0.260 / +0.267 | FAIL |
| P3 New York metals, TOUCH + TREND + WIDE, hold | +0.243 / +0.121 / +0.068 | **-0.230 R** (206 trades, almost all gold) | **-3.35** | -0.261 / -0.199 | FAIL |
P3 (gold at the New York open with the trend) was the strongest-looking lead in sample and is clearly negative out of time: the 2022-26 result was the gold bull market. P1 is positive in all four periods but small (+0.06..+0.09 R a trade held all day) and never significant; it is the same family as the USDJPY London breakout already found (USDJPY +0.214, AUDUSD +0.273 R carry most of it in 2020-21).

## Reading for the trader
The breakout's problem is not the stop, the target or the entry trigger. There is almost no information in the moment the price leaves a 30-minute box: every way of entering (stop order, close confirmation, wait 15 minutes, retest, fade) gives the same result as a random entry within a few hundredths of R, and the spread costs more than that. What helps is not trading when the box is small compared with the spread, and that only brings it to about zero. The one family still weakly positive in every period is London FX breakouts held to the close with the trend and a wide box (+0.06..+0.09 R, t about 1-2 per period): too small and too slow for the test, and not proven.
