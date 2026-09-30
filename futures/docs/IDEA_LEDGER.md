# Idea ledger

Every strategy variant tested with honest exits (flat at the session close, real
costs), one row each. The row count **k** sets the bar for the next test: an idea
is a candidate only if its rules were committed before the run, it is positive
before and after costs, in-sample P(edge>0) >= 0.95, and out-of-sample
P(edge>0) >= **1 - 0.01/k** (Bonferroni: the more ideas tried, the stricter).
Counting starts at Round 120c; earlier rounds used exits that held positions
overnight, and counting them would only raise the bar.

Tested with `futures/engine/idea_harness.py` from Round 126 on.
"n/a" = not computed in that round.

| # | date | idea (variant) | source | commit | trades | net $/trade | before costs | P(edge>0) IS / OOS | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-09-26 | Legal overnight drift, long MNQ 18:00->09:30 ET, 1 contract | Round 120c | 771ed0f | 961 days | +11.8 | n/a | t=1.2 full sample | no edge |
| 2 | 2026-09-26 | Legal overnight drift, long MGC 18:00->09:30 ET, 1 contract | Round 120c | 771ed0f | 940 days | +17.7 | n/a | t=1.5 full sample | no edge |
| 3 | 2026-09-26 | EMA 9/21 1-min, one position | Round 121 (pre-registered) | 9d38207 | 2,042 | +1.6 | n/a | 0.78 / 0.15 | no edge |
| 4 | 2026-09-26 | EMA 9/21 1-min stop-and-reverse, stop 1.5 | Round 121 (pre-registered) | 9d38207 | 15,274 | -6.8 | n/a | 0.01 / 0.00 | no edge |
| 5 | 2026-09-26 | EMA 9/21 1-min stop-and-reverse, stop 1.0 | Round 121 (pre-registered) | 9d38207 | 14,368 | -11.6 | n/a | 0.00 / 0.00 | no edge |
| 6 | 2026-09-26 | EMA 20/50 1-min stop-and-reverse, stop 1.5 | Round 121 (pre-registered) | 9d38207 | 6,432 | -12.1 | n/a | 0.16 / 0.26 | no edge |
| 7 | 2026-09-26 | EMA 20/50 1-min stop-and-reverse, stop 1.0 | Round 121 (pre-registered) | 9d38207 | 6,217 | -12.1 | n/a | 0.07 / 0.03 | no edge |
| 8 | 2026-09-26 | EMA 9/21 on MNQ + MGC, one position each | Round 121 (pre-registered) | 9d38207 | 4,301 | -13.6 | n/a | 0.04 / 0.14 | no edge |
| 9 | 2026-09-26 | EMA 9/21 on MNQ + MGC, stop-and-reverse each | Round 121 (pre-registered) | 9d38207 | 30,079 | -13.5 | n/a | 0.00 / 0.00 | no edge |
| 10 | 2026-09-26 | Vol breakout (range > 3x expected), random direction | Round 121 (pre-registered) | 9d38207 | 4,394 | -11.4 | n/a | 0.05 / 0.49 | no edge |
| 11 | 2026-09-26 | Vol breakout (range > 5x expected), random direction | Round 121 (pre-registered) | 9d38207 | 1,880 | -13.4 | n/a | 0.51 / 0.04 | no edge |
| 12 | 2026-09-26 | TS momentum 5-min, lookback 6 | Round 121 (pre-registered) | 9d38207 | 12,925 | -8.0 | n/a | 0.00 / 0.04 | no edge |
| 13 | 2026-09-26 | TS momentum 5-min, lookback 12 | Round 121 (pre-registered) | 9d38207 | 8,816 | -16.4 | n/a | 0.03 / 0.12 | no edge |
| 14 | 2026-09-26 | TS momentum 15-min, lookback 6 | Round 121 (pre-registered) | 9d38207 | 4,479 | +4.9 | n/a | 0.75 / 0.36 | no edge |
| 15 | 2026-09-26 | TS momentum 15-min, lookback 12 | Round 121 (pre-registered) | 9d38207 | 3,096 | +4.5 | n/a | 0.95 / 0.06 | no edge |
| 16 | 2026-09-26 | EMA 9/21 on 5-min bars, one position | Round 121 (pre-registered) | 9d38207 | 1,562 | +20.9 | n/a | 0.79 / 0.50 | no edge |
| 17 | 2026-09-26 | EMA 9/21 on 15-min bars, one position | Round 121 (pre-registered) | 9d38207 | 827 | +5.7 | n/a | 0.88 / 0.11 | no edge |
| 18 | 2026-09-26 | TS momentum 5min, lookback 6, on MNQ + MGC | Round 121 (pre-registered) | 9d38207 | 25,649 | -6.3 | n/a | 0.00 / 0.00 | no edge |
| 19 | 2026-09-26 | H1a intraday momentum, prev close -> 10:00 signal | Round 122 (pre-registered) | 3f3d278 | 949 | -3.5 | n/a | 0.49 / 0.07 | no edge |
| 20 | 2026-09-26 | H1b intraday momentum, prev close -> 15:30 signal | Round 122 (pre-registered) | 3f3d278 | 952 | -2.1 | n/a | 0.54 / 0.16 | no edge |
| 21 | 2026-09-26 | H1c intraday momentum, 15:30 signal, large-move days | Round 122 (pre-registered) | 3f3d278 | 437 | -5.2 | n/a | 0.44 / 0.13 | no edge |
| 22 | 2026-09-26 | H3 turn of the month, long RTH | Round 122 (pre-registered) | 3f3d278 | 180 | +44.6 | n/a | 0.81 / 0.98 | no edge |
| 23 | 2026-09-26 | Turn-of-month open->close, SPY + QQQ daily 1993-2022 (check of R122 H3) | Round 122b | 174225d | 1,437 / 1,141 TOM days | +3.0 / +3.5 bp vs other days | n/a | t=1.06 / 0.69 | no edge |
| 24 | 2026-09-26 | CodeTrading 5-min scalper, SL 1.1 x ATR7, BB 1.5 | Round 124 (video) | f6efb2b | 3,922 | -21.8 | -6.0 | 0.00 / 0.03 | no edge |
| 25 | 2026-09-26 | CodeTrading 5-min scalper, SL 1.1 x ATR7, BB 2.0 | Round 124 (video) | f6efb2b | 2,457 | -14.5 | n/a | 0.02 / 0.18 | no edge |
| 26 | 2026-09-26 | CodeTrading 5-min scalper, SL 1.2 x ATR7, BB 1.5 | Round 124 (video) | f6efb2b | 3,654 | -18.7 | n/a | 0.00 / 0.09 | no edge |
| 27 | 2026-09-26 | CodeTrading 5-min scalper, SL 1.2 x ATR7, BB 2.0 | Round 124 (video) | f6efb2b | 2,335 | -14.3 | -0.2 | 0.02 / 0.21 | no edge |
| 28 | 2026-09-26 | ICT Judas swing at NY open, to 10:30, 2R | Round 125 (video) | a9eb103 | 642 | -24.7 | -0.2 | 0.02 / 0.57 | no edge |
| 29 | 2026-09-26 | ICT Judas swing at NY open, to 10:30, opposite side | Round 125 (video) | a9eb103 | 642 | -14.6 | +10.0 | 0.29 / 0.50 | no edge |
| 30 | 2026-09-26 | ICT Judas swing at NY open, to 11:00, 2R | Round 125 (video) | a9eb103 | 704 | -26.0 | -1.2 | 0.01 / 0.55 | no edge |
| 31 | 2026-09-26 | ICT Judas swing at NY open, to 11:00, opposite side | Round 125 (video) | a9eb103 | 704 | -8.0 | +16.8 | 0.42 / 0.42 | no edge |
| 32 | 2026-09-26 | Judas swing, 2R, stop 0.5x protected | Round 125b (video) | 5ae7f8b | 702 | -87.2 | -44.4 | 0.00 / 0.00 | no edge |
| 33 | 2026-09-26 | Judas swing, 2R, stop 1.5x protected | Round 125b (video) | 5ae7f8b | 704 | -14.7 | +2.0 | 0.13 / 0.40 | no edge |
| 34 | 2026-09-26 | Judas swing, opposite side, stop 0.5x protected | Round 125b (video) | 5ae7f8b | 702 | -49.8 | -7.0 | 0.14 / 0.34 | no edge |
| 35 | 2026-09-26 | Judas swing, opposite side, stop 1.5x protected | Round 125b (video) | 5ae7f8b | 704 | -19.7 | -2.9 | 0.41 / 0.17 | no edge |
| 36 | 2026-09-26 | B1 MNQ opening-range breakout, 15-min range, 2R | Round 126 batch B (pre-registered) | bb38a7b | 907 | +15.4 | +18.7 | 0.96 / 0.535 | no edge |
| 37 | 2026-09-26 | B1 MNQ opening-range breakout, 15-min range, hold to close | Round 126 batch B (pre-registered) | bb38a7b | 907 | +14.4 | +17.7 | 0.95 / 0.308 | no edge |
| 38 | 2026-09-26 | B1 MNQ opening-range breakout, 30-min range, 2R | Round 126 batch B (pre-registered) | bb38a7b | 877 | +12.2 | +15.0 | 0.98 / 0.277 | no edge |
| 39 | 2026-09-26 | B1 MNQ opening-range breakout, 30-min range, hold to close | Round 126 batch B (pre-registered) | bb38a7b | 877 | +14.9 | +17.6 | 0.98 / 0.299 | no edge |
| 40 | 2026-09-26 | B2 MNQ gap fill, gap >= 0.1%, full fill target | Round 126 batch B (pre-registered) | bb38a7b | 777 | +8.7 | +13.3 | 0.45 / 0.927 | no edge |
| 41 | 2026-09-26 | B2 MNQ gap fill, gap >= 0.1%, half fill target | Round 126 batch B (pre-registered) | bb38a7b | 777 | -1.4 | +3.2 | 0.29 / 0.653 | no edge |
| 42 | 2026-09-26 | B2 MNQ gap fill, gap >= 0.3%, full fill target | Round 126 batch B (pre-registered) | bb38a7b | 527 | +10.0 | +12.7 | 0.50 / 0.872 | no edge |
| 43 | 2026-09-26 | B2 MNQ gap fill, gap >= 0.3%, half fill target | Round 126 batch B (pre-registered) | bb38a7b | 527 | -0.9 | +1.7 | 0.35 / 0.632 | no edge |
| 44 | 2026-09-26 | B3 MGC London breakout, stop other side, 2R | Round 126 batch B (pre-registered) | bb38a7b | 615 | +14.4 | +21.6 | 0.75 / 0.816 | no edge |
| 45 | 2026-09-26 | B3 MGC London breakout, stop other side, hold to 11:00 | Round 126 batch B (pre-registered) | bb38a7b | 615 | +15.3 | +22.6 | 0.69 / 0.849 | no edge |
| 46 | 2026-09-26 | B3 MGC London breakout, stop midpoint, 2R | Round 126 batch B (pre-registered) | bb38a7b | 615 | +6.0 | +20.0 | 0.31 / 0.937 | no edge |
| 47 | 2026-09-26 | B3 MGC London breakout, stop midpoint, hold to 11:00 | Round 126 batch B (pre-registered) | bb38a7b | 615 | +5.9 | +20.0 | 0.37 / 0.898 | no edge |
| 48 | 2026-09-26 | B4 MGC London sweep fade, to 05:00, stop 1.0x | Round 126 batch B (pre-registered) | bb38a7b | 585 | -53.4 | +4.3 | 0.03 / 0.216 | no edge |
| 49 | 2026-09-26 | B4 MGC London sweep fade, to 05:00, stop 1.5x | Round 126 batch B (pre-registered) | bb38a7b | 592 | -76.5 | -31.0 | 0.00 / 0.035 | no edge |
| 50 | 2026-09-26 | B4 MGC London sweep fade, to 08:00, stop 1.0x | Round 126 batch B (pre-registered) | bb38a7b | 689 | -59.3 | -3.5 | 0.01 / 0.169 | no edge |
| 51 | 2026-09-26 | B4 MGC London sweep fade, to 08:00, stop 1.5x | Round 126 batch B (pre-registered) | bb38a7b | 694 | -74.0 | -30.0 | 0.00 / 0.059 | no edge |
| 52 | 2026-09-26 | MNQ Asian-range STDV fade, 2.0 SD, target 1 SD back | Round 127 (video, pre-registered) | 4ccc3de | 517 | -52.0 | -35.5 | 0.00 / 0.557 | no edge |
| 53 | 2026-09-26 | MNQ Asian-range STDV fade, 2.0 SD, target range edge | Round 127 (video, pre-registered) | 4ccc3de | 520 | -74.8 | -58.4 | 0.00 / 0.344 | no edge |
| 54 | 2026-09-26 | MNQ Asian-range STDV fade, 2.5 SD, target 1 SD back | Round 127 (video, pre-registered) | 4ccc3de | 425 | -22.1 | -4.1 | 0.03 / 0.915 | no edge |
| 55 | 2026-09-26 | MNQ Asian-range STDV fade, 2.5 SD, target range edge | Round 127 (video, pre-registered) | 4ccc3de | 426 | -6.6 | +11.3 | 0.18 / 0.870 | no edge |
| 56 | 2026-09-26 | MNQ trade toward LRL at open, stop 1:1, all days | Round 128 (video, pre-registered) | a72cff4 | 532 | -25.9 | -15.8 | 0.01 / 0.418 | no edge |
| 57 | 2026-09-26 | MNQ trade toward LRL at open, stop 1:1, HRL path >= 1.5x denser | Round 128 (video, pre-registered) | a72cff4 | 394 | -39.6 | -27.5 | 0.00 / 0.270 | no edge |
| 58 | 2026-09-26 | MNQ trade toward LRL at open, stop other level, all days | Round 128 (video, pre-registered) | a72cff4 | 532 | -12.6 | -9.7 | 0.01 / 0.888 | no edge |
| 59 | 2026-09-26 | MNQ trade toward LRL at open, stop other level, HRL path >= 1.5x denser | Round 128 (video, pre-registered) | a72cff4 | 394 | -15.5 | -12.8 | 0.01 / 0.886 | no edge |
| 60 | 2026-09-26 | MNQ 4H Po3 06:00-10:00, both directions | Round 129 (video, pre-registered) | 2d5f12d | 851 | -94.6 | -47.4 | 0.14 / 0.006 | no edge |
| 61 | 2026-09-26 | MNQ 4H Po3 06:00-10:00, near-ATH longs only | Round 129 (video, pre-registered) | 2d5f12d | 275 | +24.6 | +70.0 | 0.66 / 0.323 | no edge |
| 62 | 2026-09-26 | MNQ 4H Po3 10:00-14:00, both directions | Round 129 (video, pre-registered) | 2d5f12d | 875 | -24.8 | -3.8 | 0.35 / 0.135 | no edge |
| 63 | 2026-09-26 | MNQ 4H Po3 10:00-14:00, near-ATH longs only | Round 129 (video, pre-registered) | 2d5f12d | 276 | -69.3 | -49.5 | 0.04 / 0.215 | no edge |
| 64 | 2026-09-26 | live random_entry_atr_trail, all day, MNQ, seeds 0-4 pooled | Round 130 (live_bot re-check) | 1054cc0 | 4781 | +2.0 | +7.9 | 0.41 / 0.900 | no edge |
| 65 | 2026-09-26 | live support_resistance_bounce MGC, fill at bar extreme (as validated) | Round 130 (live_bot re-check) | 1054cc0 | 2376 | -37.9 | -23.8 | 0.00 / 0.000 | no edge |
| 66 | 2026-09-26 | live support_resistance_bounce MGC, entry at touch bar's close | Round 130 (live_bot re-check) | 1054cc0 | 2312 | -20.7 | -6.6 | 0.00 / 0.001 | no edge |
| 67 | 2026-09-26 | INVERTED R124 scalper SL 1.1 BB 1.5 | Round 131 (inverted losers, pre-registered) | ed57a7f | 3922 | -8.0 | +2.2 | 0.01 / 0.283 | no edge |
| 68 | 2026-09-26 | INVERTED R124 scalper SL 1.1 BB 2.0 | Round 131 (inverted losers, pre-registered) | ed57a7f | 2457 | -12.3 | -2.3 | 0.00 / 0.187 | no edge |
| 69 | 2026-09-26 | INVERTED R124 scalper SL 1.2 BB 1.5 | Round 131 (inverted losers, pre-registered) | ed57a7f | 3654 | -7.6 | +1.7 | 0.02 / 0.204 | no edge |
| 70 | 2026-09-26 | INVERTED R124 scalper SL 1.2 BB 2.0 | Round 131 (inverted losers, pre-registered) | ed57a7f | 2335 | -10.3 | -1.2 | 0.01 / 0.184 | no edge |
| 71 | 2026-09-26 | INVERTED R125 Judas to 10:30 2R stop 1.0x | Round 131 (inverted losers, pre-registered) | ed57a7f | 642 | -32.0 | -19.9 | 0.01 / 0.001 | no edge |
| 72 | 2026-09-26 | INVERTED R125 Judas to 10:30 opp stop 1.0x | Round 131 (inverted losers, pre-registered) | ed57a7f | 642 | -11.7 | -9.2 | 0.19 / 0.046 | no edge |
| 73 | 2026-09-26 | INVERTED R125 Judas to 11:00 2R stop 1.0x | Round 131 (inverted losers, pre-registered) | ed57a7f | 704 | -29.5 | -17.3 | 0.00 / 0.001 | no edge |
| 74 | 2026-09-26 | INVERTED R125 Judas to 11:00 opp stop 1.0x | Round 131 (inverted losers, pre-registered) | ed57a7f | 704 | -10.7 | -8.2 | 0.11 / 0.089 | no edge |
| 75 | 2026-09-26 | INVERTED R125 Judas to 11:00 2R stop 0.5x | Round 131 (inverted losers, pre-registered) | ed57a7f | 702 | -44.1 | -22.4 | 0.00 / 0.000 | no edge |
| 76 | 2026-09-26 | INVERTED R125 Judas to 11:00 2R stop 1.5x | Round 131 (inverted losers, pre-registered) | ed57a7f | 704 | -17.6 | -9.4 | 0.05 / 0.050 | no edge |
| 77 | 2026-09-26 | INVERTED R125 Judas to 11:00 opp stop 0.5x | Round 131 (inverted losers, pre-registered) | ed57a7f | 702 | -6.9 | -4.4 | 0.12 / 0.146 | no edge |
| 78 | 2026-09-26 | INVERTED R125 Judas to 11:00 opp stop 1.5x | Round 131 (inverted losers, pre-registered) | ed57a7f | 704 | -7.3 | -4.8 | 0.32 / 0.141 | no edge |
| 79 | 2026-09-26 | INVERTED R126 B2 gap fill 0.1% half | Round 131 (inverted losers, pre-registered) | ed57a7f | 777 | -16.2 | -7.0 | 0.20 / 0.170 | no edge |
| 80 | 2026-09-26 | INVERTED R126 B2 gap fill 0.3% half | Round 131 (inverted losers, pre-registered) | ed57a7f | 527 | -7.2 | -2.6 | 0.38 / 0.327 | no edge |
| 81 | 2026-09-26 | INVERTED R126 B4 gold London fade to 05:00 stop 1.0x | Round 131 (inverted losers, pre-registered) | ed57a7f | 585 | -15.6 | +1.4 | 0.01 / 0.478 | no edge |
| 82 | 2026-09-26 | INVERTED R126 B4 gold London fade to 05:00 stop 1.5x | Round 131 (inverted losers, pre-registered) | ed57a7f | 592 | -3.3 | +13.4 | 0.25 / 0.728 | no edge |
| 83 | 2026-09-26 | INVERTED R126 B4 gold London fade to 08:00 stop 1.0x | Round 131 (inverted losers, pre-registered) | ed57a7f | 689 | -13.5 | +3.0 | 0.01 / 0.724 | no edge |
| 84 | 2026-09-26 | INVERTED R126 B4 gold London fade to 08:00 stop 1.5x | Round 131 (inverted losers, pre-registered) | ed57a7f | 694 | -3.9 | +12.2 | 0.19 / 0.738 | no edge |
| 85 | 2026-09-26 | INVERTED R127 STDV fade 2.0 SD 1 SD back | Round 131 (inverted losers, pre-registered) | ed57a7f | 517 | +0.1 | +7.9 | 0.70 / 0.201 | no edge |
| 86 | 2026-09-26 | INVERTED R127 STDV fade 2.0 SD range edge | Round 131 (inverted losers, pre-registered) | ed57a7f | 520 | +19.3 | +22.9 | 0.95 / 0.801 | no edge |
| 87 | 2026-09-26 | INVERTED R127 STDV fade 2.5 SD 1 SD back | Round 131 (inverted losers, pre-registered) | ed57a7f | 425 | -7.5 | +1.2 | 0.43 / 0.112 | no edge |
| 88 | 2026-09-26 | INVERTED R127 STDV fade 2.5 SD range edge | Round 131 (inverted losers, pre-registered) | ed57a7f | 426 | -14.2 | -11.2 | 0.14 / 0.069 | no edge |
| 89 | 2026-09-26 | INVERTED R128 toward LRL stop 1:1 ratio 1.0 | Round 131 (inverted losers, pre-registered) | ed57a7f | 532 | -18.2 | -8.2 | 0.46 / 0.015 | no edge |
| 90 | 2026-09-26 | INVERTED R128 toward LRL stop 1:1 ratio 1.5 | Round 131 (inverted losers, pre-registered) | ed57a7f | 394 | -17.0 | -4.9 | 0.57 / 0.017 | no edge |
| 91 | 2026-09-26 | INVERTED R128 toward LRL stop other level ratio 1.0 | Round 131 (inverted losers, pre-registered) | ed57a7f | 532 | +14.9 | +25.0 | 0.91 / 0.020 | no edge |
| 92 | 2026-09-26 | INVERTED R128 toward LRL stop other level ratio 1.5 | Round 131 (inverted losers, pre-registered) | ed57a7f | 394 | +28.9 | +41.1 | 0.92 / 0.042 | no edge |
| 93 | 2026-09-26 | MNQ STDV continuation k=1.5 T=0.25 | Round 132 (STDV continuation checks, pre-registered) | e489071 | 609 | +7.3 | +11.8 | 0.48 / 0.870 | no edge |
| 94 | 2026-09-26 | MNQ STDV continuation k=1.5 T=0.5 | Round 132 (STDV continuation checks, pre-registered) | e489071 | 644 | +18.0 | +22.5 | 0.82 / 0.982 | no edge |
| 95 | 2026-09-26 | MNQ STDV continuation k=1.5 T=0.75 | Round 132 (STDV continuation checks, pre-registered) | e489071 | 653 | +26.1 | +30.6 | 0.97 / 0.970 | no edge |
| 96 | 2026-09-26 | MNQ STDV continuation k=1.75 T=0.25 | Round 132 (STDV continuation checks, pre-registered) | e489071 | 546 | +15.3 | +19.2 | 0.50 / 1.000 | no edge |
| 97 | 2026-09-26 | MNQ STDV continuation k=1.75 T=0.5 | Round 132 (STDV continuation checks, pre-registered) | e489071 | 578 | +20.8 | +24.8 | 0.79 / 0.991 | no edge |
| 98 | 2026-09-26 | MNQ STDV continuation k=1.75 T=0.75 | Round 132 (STDV continuation checks, pre-registered) | e489071 | 587 | +25.7 | +29.8 | 0.95 / 0.963 | no edge |
| 99 | 2026-09-26 | MNQ STDV continuation k=2.0 T=0.25 | Round 132 (STDV continuation checks, pre-registered) | e489071 | 484 | +13.5 | +17.1 | 0.69 / 0.864 | no edge |
| 100 | 2026-09-26 | MNQ STDV continuation k=2.0 T=0.5 | Round 132 (STDV continuation checks, pre-registered) | e489071 | 520 | +19.3 | +22.9 | 0.95 / 0.801 | no edge |
| 101 | 2026-09-26 | MNQ STDV continuation k=2.0 T=0.75 | Round 132 (STDV continuation checks, pre-registered) | e489071 | 527 | +12.8 | +16.4 | 0.73 / 0.703 | no edge |
| 102 | 2026-09-26 | MNQ STDV continuation k=2.25 T=0.25 | Round 132 (STDV continuation checks, pre-registered) | e489071 | 430 | +16.9 | +20.1 | 0.92 / 0.727 | no edge |
| 103 | 2026-09-26 | MNQ STDV continuation k=2.25 T=0.5 | Round 132 (STDV continuation checks, pre-registered) | e489071 | 471 | +7.9 | +11.2 | 0.51 / 0.650 | no edge |
| 104 | 2026-09-26 | MNQ STDV continuation k=2.25 T=0.75 | Round 132 (STDV continuation checks, pre-registered) | e489071 | 482 | +7.6 | +10.9 | 0.55 / 0.601 | no edge |
| 105 | 2026-09-26 | MNQ STDV continuation k=2.5 T=0.25 | Round 132 (STDV continuation checks, pre-registered) | e489071 | 393 | -12.0 | -9.0 | 0.15 / 0.106 | no edge |
| 106 | 2026-09-26 | MNQ STDV continuation k=2.5 T=0.5 | Round 132 (STDV continuation checks, pre-registered) | e489071 | 426 | -14.2 | -11.2 | 0.14 / 0.069 | no edge |
| 107 | 2026-09-26 | MNQ STDV continuation k=2.5 T=0.75 | Round 132 (STDV continuation checks, pre-registered) | e489071 | 433 | -15.1 | -12.1 | 0.13 / 0.103 | no edge |
| 108 | 2026-09-26 | MGC STDV continuation k=2.0 T=0.5 (replication) | Round 132 (STDV continuation checks, pre-registered) | e489071 | 256 | -9.2 | -2.7 | 0.01 / 0.924 | no edge |
| 109 | 2026-09-26 | C1 MNQ STDV continuation, trending regime | Round 134 batch C (pre-registered) | e05cbc8 | 132 | +29.0 | +32.9 | 1.00 / 0.492 | no edge |
| 110 | 2026-09-26 | C1 MGC STDV continuation, trending regime | Round 134 batch C (pre-registered) | e05cbc8 | 69 | +8.4 | +14.6 | 0.15 / 1.000 | no edge |
| 111 | 2026-09-26 | C1 MNQ STDV continuation, trending regime + aligned | Round 134 batch C (pre-registered) | e05cbc8 | 76 | +11.6 | +15.1 | 0.96 / 0.271 | no edge |
| 112 | 2026-09-26 | C1 MGC STDV continuation, trending regime + aligned | Round 134 batch C (pre-registered) | e05cbc8 | 28 | +41.5 | +47.5 | 0.78 / 1.000 | no edge |
| 113 | 2026-09-26 | C2 MNQ NR7 ORB 15-min, 2R | Round 134 batch C (pre-registered) | e05cbc8 | 143 | +32.8 | +36.4 | 0.97 / 0.254 | no edge |
| 114 | 2026-09-26 | C2 MNQ NR7 ORB 15-min, hold | Round 134 batch C (pre-registered) | e05cbc8 | 143 | +29.9 | +33.5 | 0.96 / 0.111 | no edge |
| 115 | 2026-09-26 | C2 MNQ NR7 ORB 30-min, 2R | Round 134 batch C (pre-registered) | e05cbc8 | 140 | +40.5 | +43.5 | 0.97 / 0.623 | no edge |
| 116 | 2026-09-26 | C2 MNQ NR7 ORB 30-min, hold | Round 134 batch C (pre-registered) | e05cbc8 | 140 | +39.3 | +42.3 | 0.97 / 0.559 | no edge |
| 117 | 2026-09-26 | C2 MGC NR7 ORB 15-min, 2R | Round 134 batch C (pre-registered) | e05cbc8 | 142 | -31.3 | -19.9 | 0.01 / 0.876 | no edge |
| 118 | 2026-09-26 | C2 MGC NR7 ORB 15-min, hold | Round 134 batch C (pre-registered) | e05cbc8 | 142 | -0.8 | +10.5 | 0.18 / 0.889 | no edge |
| 119 | 2026-09-26 | C2 MGC NR7 ORB 30-min, 2R | Round 134 batch C (pre-registered) | e05cbc8 | 136 | -25.5 | -16.8 | 0.03 / 0.654 | no edge |
| 120 | 2026-09-26 | C2 MGC NR7 ORB 30-min, hold | Round 134 batch C (pre-registered) | e05cbc8 | 136 | -18.1 | -9.4 | 0.14 / 0.577 | no edge |
| 121 | 2026-09-26 | C3 MGC Asia 18-02, short 1 contract | Round 134 batch C (pre-registered) | e05cbc8 | 894 | -9.8 | -6.5 | 0.11 / 0.247 | no edge |
| 122 | 2026-09-26 | C3 MGC London 02-08, long 1 contract | Round 134 batch C (pre-registered) | e05cbc8 | 907 | +9.1 | +12.3 | 0.82 / 0.849 | no edge |
| 123 | 2026-09-26 | C3 MGC NY morning 08-11, short 1 contract | Round 134 batch C (pre-registered) | e05cbc8 | 907 | +1.4 | +4.6 | 0.34 / 0.641 | no edge |
| 124 | 2026-09-26 | C3 MGC NY rest 11-16, long 1 contract | Round 134 batch C (pre-registered) | e05cbc8 | 898 | -5.3 | -2.0 | 0.57 / 0.180 | no edge |
| 125 | 2026-09-26 | C4 hourly momentum 10:00 -> 16:00, 7-instrument portfolio | Round 134 batch C (pre-registered) | e05cbc8 | 4102 | -8.6 | +6.9 | 0.23 / 0.260 | no edge |
| 126 | 2026-09-26 | C4 hourly momentum 15:00 -> 16:00, 7-instrument portfolio | Round 134 batch C (pre-registered) | e05cbc8 | 4111 | -7.9 | +3.4 | 0.00 / 0.345 | no edge |
| 127 | 2026-09-26 | D1 TSMOM 20-day, 10 markets (R units) | Round 135 batch D (pre-registered) | 7214aa4 | 48534 | -0.029R | +0.018R | 0.01 / 0.000 | no edge |
| 128 | 2026-09-26 | D1 TSMOM 120-day, 10 markets (R units) | Round 135 batch D (pre-registered) | 7214aa4 | 47634 | -0.023R | +0.024R | 0.00 / 0.000 | no edge |
| 129 | 2026-09-26 | D1 TSMOM 250-day, 10 markets (R units) | Round 135 batch D (pre-registered) | 7214aa4 | 46467 | -0.027R | +0.021R | 0.00 / 0.000 | no edge |
| 130 | 2026-09-26 | D2 reversal after a 1.0 SD day, 4 indices (R units) | Round 135 batch D (pre-registered) | 7214aa4 | 6675 | +0.000R | +0.041R | 0.42 / 0.557 | no edge |
| 131 | 2026-09-26 | D2 reversal after a 1.5 SD day, 4 indices (R units) | Round 135 batch D (pre-registered) | 7214aa4 | 3307 | +0.023R | +0.065R | 0.48 / 0.908 | no edge |
| 132 | 2026-09-26 | D3 pre-holiday long, 4 indices (R units) | Round 135 batch D (pre-registered) | 7214aa4 | 794 | +0.063R | +0.104R | 0.53 / 0.998 | no edge |
| 133 | 2026-09-26 | E1a long each currency in US hours 09-16 (R units) | Round 136 batch E (pre-registered) | 8ffcfcf | 2304 | -0.177R | -0.038R | 0.00 / 0.000 | no edge |
| 134 | 2026-09-26 | E1b short each currency in its own hours (R units) | Round 136 batch E (pre-registered) | 8ffcfcf | 2267 | -0.167R | +0.005R | 0.00 / 0.000 | no edge |
| 135 | 2026-09-26 | E2 FOMC statement day long, 4 indices (R units) | Round 136 batch E (pre-registered) | 8ffcfcf | 678 | +0.098R | +0.140R | 1.00 / 0.247 | no edge |
| 136 | 2026-09-26 | E3 jobs-report day long, 4 indices (R units) | Round 136 batch E (pre-registered) | 8ffcfcf | 963 | +0.046R | +0.087R | 0.02 / 0.999 | no edge |
| 137 | 2026-09-26 | F1a walk-forward logistic regression (L2, C=0.1) (R units) | Round 137 batch F (pre-registered) | f44f1f7 | 10929 | -0.004R | +0.039R | 0.53 / 0.326 | no edge |
| 138 | 2026-09-26 | F1b walk-forward gradient boosting (depth 3) (R units) | Round 137 batch F (pre-registered) | f44f1f7 | 10191 | +0.006R | +0.049R | 0.18 / 0.872 | no edge |

Note: Round 138 scanned 582 sub-hour pattern cells; none passed discovery selection (t >= 3.5), so no rows were added (see TRADING_JOURNAL.md).
| 139 | 2026-09-26 | H1a variance risk premium in top third (R units) | Round 139 batch H (pre-registered) | 70013b8 | 6098 | +0.035R | +0.071R | 0.89 / 0.949 | no edge |
| 140 | 2026-09-26 | H1b VIX term structure in backwardation (R units) | Round 139 batch H (pre-registered) | 70013b8 | 1837 | +0.073R | +0.100R | 0.62 / 0.997 | no edge |
| 141 | 2026-09-26 | H1c VIX spike >= 20% above 20-day average (R units) | Round 139 batch H (pre-registered) | 70013b8 | 1797 | +0.117R | +0.148R | 0.78 / 0.999 | no edge |
| 142 | 2026-09-26 | H2a crypto TSMOM 20-day, BTC + ETH (R units) | Round 139 batch H (pre-registered) | 70013b8 | 3526 | -0.027R | +0.061R | 0.09 / 0.244 | no edge |
| 143 | 2026-09-26 | H2a crypto TSMOM 60-day, BTC + ETH (R units) | Round 139 batch H (pre-registered) | 70013b8 | 3454 | -0.065R | +0.023R | 0.00 / 0.054 | no edge |
| 144 | 2026-09-26 | H2b crypto intraday momentum 18-10 -> 10-16 (R units) | Round 139 batch H (pre-registered) | 70013b8 | 1109 | -0.020R | +0.073R | 0.65 / 0.141 | no edge |
| 145 | 2026-09-26 | H1c VIX-spike long, 1993-2000 SPY replication (R units) | Round 140 replication (pre-registered) | a516a4d | 89 | +0.085R | n/a | replication P 0.727, excess P 0.962 | not replicated |
| 146 | 2026-09-26 | I1a short ZN 2 days before auctions (R units) | Round 141 batch I (pre-registered) | 47244bb | 1088 | -0.089R | +0.005R | 0.00 / 0.103 | no edge |
| 147 | 2026-09-26 | I1b long ZN 2 days after auctions (R units) | Round 141 batch I (pre-registered) | 47244bb | 1090 | +0.006R | +0.100R | 1.00 / 0.023 | no edge |
| 148 | 2026-09-26 | I2 long ZN on the last trading day of the month (R units) | Round 141 batch I (pre-registered) | 47244bb | 308 | +0.111R | +0.204R | 0.98 / 0.723 | no edge |
| 149 | 2026-09-26 | I3a long indices in OPEX week (R units) | Round 141 batch I (pre-registered) | 47244bb | 4995 | +0.023R | +0.064R | 0.39 / 0.985 | no edge |
| 150 | 2026-09-26 | I3b short indices the week after OPEX (R units) | Round 141 batch I (pre-registered) | 47244bb | 4833 | -0.072R | -0.031R | 0.04 / 0.000 | no edge |
| 151 | 2026-09-26 | J1 crypto CME weekend-gap fade, BTC + ETH (R units) | Round 142 batch J (pre-registered) | 3cfe3dc | 323 | -0.177R | -0.085R | 0.30 / 0.003 | no edge |
| 152 | 2026-09-26 | J2 index weekend-gap fade, 4 indices (R units) | Round 142 batch J (pre-registered) | 3cfe3dc | 551 | +0.000R | +0.038R | 0.30 / 0.624 | no edge |
| 153 | 2026-09-26 | J3 Connors RSI(2) < 10 above 200-day, 4 indices (R units) | Round 142 batch J (pre-registered) | 3cfe3dc | 2357 | +0.059R | +0.101R | 0.92 / 0.934 | no edge |
| 154 | 2026-09-26 | J3 Connors RSI(2) < 5 above 200-day, 4 indices (R units) | Round 142 batch J (pre-registered) | 3cfe3dc | 1291 | +0.033R | +0.073R | 0.97 / 0.429 | no edge |
| 155 | 2026-09-26 | J4 NQ-ES spread reversal after a 2 SD day (R units) | Round 142 batch J (pre-registered) | 3cfe3dc | 399 | -0.074R | -0.023R | 0.00 / 0.001 | no edge |
| 156 | 2026-09-26 | pre-holiday long, 1990-2000 S&P 500 replication (R units) | Round 143 replication (pre-registered) | 9245730 | 87 | -0.207R | -0.015R | replication P 0.025, excess P 0.263 | not replicated |
| 157 | 2026-09-26 | Connors RSI(2) < 10 long, 1990-2000 S&P 500 replication (R units) | Round 143 replication (pre-registered) | 9245730 | 422 | +0.010R | +0.193R | replication P 0.564, excess P 0.989 | not replicated |
| 158 | 2026-09-26 | K1 month-end rebalancing: fade stocks-minus-bonds MTD, last 3 days (R units) | Round 144 batch K (pre-registered) | 2243a1f | 3045 | +0.044R | +0.084R | 0.61 / 0.996 | no edge |
| 159 | 2026-09-26 | K2a Connors RSI(2) both sides, 6 non-equity markets (R units) | Round 144 batch K (pre-registered) | 2243a1f | 4651 | -0.058R | -0.006R | 0.06 / 0.000 | no edge |
| 160 | 2026-09-26 | K2b Connors RSI(2) > 90 short below 200-day, 4 indices (R units) | Round 144 batch K (pre-registered) | 2243a1f | 891 | +0.016R | +0.047R | 0.22 / 0.941 | no edge |
| 161 | 2026-09-26 | K3 Santa Claus rally, last 5 Dec + first 2 Jan days, 4 indices (R units) | Round 144 batch K (pre-registered) | 2243a1f | 590 | -0.035R | +0.008R | 0.45 / 0.147 | no edge |
| 162 | 2026-09-26 | K4 long 4 indices when 20-day SD is below its 250-day median (R units) | Round 144 batch K (pre-registered) | 2243a1f | 11042 | -0.013R | +0.038R | 0.04 / 0.470 | no edge |
| 163 | 2026-09-26 | K5 cross-sectional momentum 12-1, top 3 / bottom 3 of 10 markets (R units) | Round 144 batch K (pre-registered) | 2243a1f | 34914 | -0.034R | +0.016R | 0.00 / 0.002 | no edge |
| 164 | 2026-09-26 | L1 month-end hedging flow: 6E with US-minus-DAX MTD, last day (R units) | Round 145 batch L (pre-registered) | 2044b3b | 306 | -0.071R | -0.015R | 0.46 / 0.083 | no edge |
| 165 | 2026-09-26 | L2a volatility breakout 0.5 x prior range, 10 markets (R units) | Round 145 batch L (pre-registered) | 2044b3b | 36136 | +0.072R | +0.120R | 1.00 / 1.000 | no edge |
| 166 | 2026-09-26 | L2b volatility breakout 1.0 x prior range, 10 markets (R units) | Round 145 batch L (pre-registered) | 2044b3b | 15876 | +0.014R | +0.063R | 0.66 / 0.993 | no edge |
| 167 | 2026-09-26 | L3 IBS < 0.2 long next day, 4 indices (R units) | Round 145 batch L (pre-registered) | 2044b3b | 3896 | +0.077R | +0.115R | 0.89 / 1.000 | no edge |
| 168 | 2026-09-26 | L4 lunar: long near new moon, short near full moon, 4 indices (R units) | Round 145 batch L (pre-registered) | 2044b3b | 20251 | -0.039R | +0.001R | 0.00 / 0.001 | no edge |
Note: Round 145's L2a row shows its 50/50 headline (P 1.00 / 1.000). It is "no edge" because it failed the pre-registered worst-case check (-0.031R, P 0.00 / 0.002). On a random walk the 50/50 method scores +0.080R, so the headline is an artifact (`round145_batch_l.py --order-bias`). L3 passed the 2013-26 bar (P 1.00000) but failed the 2000-12 condition (P 0.888 < 0.95).
| 169 | 2026-09-26 | IBS < 0.2 long, 1990-2000 S&P 500 replication (R units) | Round 146 replication (pre-registered) | 4137623 | 544 | -0.053R | +0.013R | replication P 0.138, excess P 0.189 | not replicated |
| 170 | 2026-09-26 | M1 round-number fade, T=S/2, MNQ + MGC | Round 147 batch M (pre-registered) | 37c68b8 | 6898 | -12.9 | -4.0 | 0.00 / 0.000 | no edge |
| 171 | 2026-09-26 | M1 round-number fade, T=S/3, MNQ + MGC | Round 147 batch M (pre-registered) | 37c68b8 | 7051 | -11.1 | -2.2 | 0.00 / 0.000 | no edge |
| 172 | 2026-09-26 | M2 previous-day high/low fade, T=S/2, MNQ + MGC | Round 147 batch M (pre-registered) | 37c68b8 | 1686 | -21.4 | -10.7 | 0.00 / 0.032 | no edge |
| 173 | 2026-09-26 | M2 previous-day high/low fade, T=S/3, MNQ + MGC | Round 147 batch M (pre-registered) | 37c68b8 | 1686 | -19.8 | -9.0 | 0.00 / 0.018 | no edge |
| 174 | 2026-09-26 | M3 opening-range fade, T=S/2, MNQ + MGC | Round 147 batch M (pre-registered) | 37c68b8 | 1818 | -8.2 | +0.6 | 0.01 / 0.520 | no edge |
| 175 | 2026-09-26 | M3 opening-range fade, T=S/3, MNQ + MGC | Round 147 batch M (pre-registered) | 37c68b8 | 1818 | -10.1 | -1.4 | 0.00 / 0.355 | no edge |
| 176 | 2026-09-26 | N1 round-number breakout, target 2S, MNQ + MGC | Round 148 batch N (pre-registered) | 8bb523f | 4907 | +0.2 | +9.3 | 0.51 / 0.513 | no edge |
| 177 | 2026-09-26 | N1 round-number breakout, no target, stop to 16:00, MNQ + MGC | Round 148 batch N (pre-registered) | 8bb523f | 3433 | +10.2 | +19.7 | 0.79 / 0.707 | no edge |
| 178 | 2026-09-26 | N2 previous-day high/low breakout, target 2S, MNQ + MGC | Round 148 batch N (pre-registered) | 8bb523f | 1509 | -3.0 | +7.3 | 0.50 / 0.243 | no edge |
| 179 | 2026-09-26 | N2 previous-day high/low breakout, no target, stop to 16:00, MNQ + MGC | Round 148 batch N (pre-registered) | 8bb523f | 1493 | +17.6 | +28.0 | 0.87 / 0.615 | no edge |
| 180 | 2026-09-26 | N3 overnight high/low breakout in RTH, target 2S, MNQ + MGC | Round 148 batch N (pre-registered) | 8bb523f | 1590 | -14.6 | -5.0 | 0.14 / 0.063 | no edge |
| 181 | 2026-09-26 | N3 overnight high/low breakout in RTH, no target, stop to 16:00, MNQ + MGC | Round 148 batch N (pre-registered) | 8bb523f | 1590 | -0.8 | +8.8 | 0.53 / 0.378 | no edge |
| 182 | 2026-09-26 | O1 walk-forward gradient boosting, 1:1 bracket, top/bottom 10%, MNQ + MGC | Round 149 batch O (pre-registered) | b8c2400 | 3738 | -14.3 | +1.1 | 0.00 / 0.035 | no edge |
| 183 | 2026-09-26 | O2 walk-forward logistic regression, 1:1 bracket, top/bottom 10%, MNQ + MGC | Round 149 batch O (pre-registered) | b8c2400 | 4628 | -9.3 | +5.5 | 0.00 / 0.481 | no edge |
| 184 | 2026-09-26 | P1 plain FVG retest, 5-min, 1:1, MNQ + MGC | Round 150 batch P (pre-registered; video qkzJknH5IJk) | 6ec5a9a | 24215 | -11.1 | +3.4 | 0.00 / 0.013 | no edge |
| 185 | 2026-09-26 | P2 FVG with displacement, VWAP side, killzone, 50% entry, 5-min, 1:1, MNQ + MGC | Round 150 batch P (pre-registered; video qkzJknH5IJk) | 6ec5a9a | 4740 | -15.6 | -1.8 | 0.00 / 0.506 | no edge |
| 186 | 2026-09-26 | P1 plain FVG retest, 15-min, 1:1, MNQ + MGC | Round 150 batch P (pre-registered; video qkzJknH5IJk) | 6ec5a9a | 11427 | -9.0 | +2.7 | 0.00 / 0.272 | no edge |
| 187 | 2026-09-26 | P2 FVG with displacement, VWAP side, killzone, 50% entry, 15-min, 1:1, MNQ + MGC | Round 150 batch P (pre-registered; video qkzJknH5IJk) | 6ec5a9a | 2891 | -4.6 | +6.8 | 0.08 / 0.621 | no edge |
| 188 | 2026-09-26 | Q1 same-slot persistence, 30-min slots 08-16 ET, |t| >= 2 over 20 days, MNQ + MGC | Round 151 batch Q (pre-registered) | 0266ee6 | 1497 | -30.8 | -9.9 | 0.00 / 0.283 | no edge |
| 189 | 2026-09-26 | Q2 overnight 18:00-09:29 against a >= 1 SD previous regular session, MNQ + MGC | Round 151 batch Q (pre-registered) | 0266ee6 | 526 | +1.7 | +5.4 | 0.49 / 0.557 | no edge |
| 190 | 2026-09-26 | Q3 08:30 news breakout of the 08:30-08:34 range, 1:1, MNQ + MGC | Round 151 batch Q (pre-registered) | 0266ee6 | 446 | -27.9 | -21.2 | 0.08 / 0.001 | no edge |
| 191 | 2026-09-26 | Q3 inverse: fade the 08:30 news break, 1:1, MNQ + MGC (chosen after Q3 lost) | Round 152 inversion of Q3 (pre-registered; selected after Q3's result) | 48ecabb | 446 | +14.5 | +21.2 | 0.62 / 0.992 | no edge |
| 192 | 2026-09-26 | FVG plain 5-min, exit chosen in-sample: stop 2S target 2S, MNQ + MGC | Round 153 exit grid, chosen in-sample (pre-registered) | 7510b4f | 10712 | -0.1 | +6.5 | 0.09 / 0.907 | no edge |
| 193 | 2026-09-26 | 08:30 news fade, exit chosen in-sample: stop 0.5S target hold, MNQ + MGC | Round 153 exit grid, chosen in-sample (pre-registered) | 7510b4f | 446 | +68.1 | +82.3 | 0.82 / 0.981 | no edge |
| 194 | 2026-09-26 | round-number breakout, exit chosen in-sample: stop 1S target hold, MNQ + MGC | Round 153 exit grid, chosen in-sample (pre-registered) | 7510b4f | 3433 | +10.2 | +19.7 | 0.79 / 0.707 | no edge |
| 195 | 2026-09-26 | previous-day high/low breakout, exit chosen in-sample: stop 0.5S target hold, MNQ + MGC | Round 153 exit grid, chosen in-sample (pre-registered) | 7510b4f | 1496 | +43.3 | +65.3 | 0.97 / 0.523 | no edge |
| 196 | 2026-09-26 | BTC weekend gap -> same-direction ES/NQ/YM/RTY open->close (co-movement) | Round 154 (pre-registered, new idea class: crypto->equity information transfer) | 6002bcb | 801 | -0.1 | -0.0 | 0.03 / 0.602 | no edge |
| 197 | 2026-09-27 | 6E prior-day move -> same-direction GC open->close (dollar leads gold) | Round 155 (pre-registered, new idea class: dollar/currency leading a commodity) | 4c849a4 | 1885 | -0.0 | -0.0 | 0.48 / 0.101 | no edge |
| 198 | 2026-09-27 | Halloween indicator: long Nov-Apr, flat May-Oct, ES/NQ/YM/RTY | Round 156 (pre-registered, new idea class: Halloween/seasonal month-block) | e6e7b74 | 10454 | +0.0 | +0.0 | 0.06 / 0.942 | no edge |
| 199 | 2026-09-27 | Copper (HG) prior-day move -> same-direction ES/NQ/YM/RTY open->close (Dr. Copper) | Round 157 (pre-registered, new idea class: Dr. Copper as a growth-expectations leader) | 7297867 | 9014 | -0.1 | -0.0 | 0.00 / 0.019 | no edge |
| 200 | 2026-09-27 | Round 157 inverse: fade copper's prior-day move, ES/NQ/YM/RTY (chosen after Round 157's fade lean) | Round 158 inversion of Round 157 (pre-registered; selected after Round 157's fade lean) | 8fe7208 | 9014 | -0.0 | +0.0 | 0.32 / 0.024 | no edge |
| 201 | 2026-09-27 | ICT Order Block retest continuation, 1R, MNQ + MGC | Round 159 (pre-registered, ICT: all remaining strategies) | 9d31d45 | 25529 | -81.0 | +2.9 | 0.00 / 0.000 | no edge |
| 202 | 2026-09-27 | ICT Order Block retest continuation, 2R, MNQ + MGC | Round 159 (pre-registered, ICT: all remaining strategies) | 9d31d45 | 23961 | -74.2 | +10.0 | 0.00 / 0.000 | no edge |
| 203 | 2026-09-27 | ICT Order Block retest continuation, 3R, MNQ + MGC | Round 159 (pre-registered, ICT: all remaining strategies) | 9d31d45 | 22608 | -71.4 | +13.0 | 0.00 / 0.000 | no edge |
| 204 | 2026-09-27 | ICT Silver Bullet (10-11/14-15 ET sweep+FVG), 1:1, MNQ + MGC | Round 159 (pre-registered, ICT: all remaining strategies) | 9d31d45 | 1739 | -14.2 | -6.6 | 0.02 / 0.095 | no edge |
| 205 | 2026-09-27 | ICT Silver Bullet (10-11/14-15 ET sweep+FVG), 1:2, MNQ + MGC | Round 159 (pre-registered, ICT: all remaining strategies) | 9d31d45 | 1658 | -10.2 | -2.5 | 0.16 / 0.233 | no edge |
| 206 | 2026-09-27 | INVERTED P1 plain FVG retest, 5-min, MNQ + MGC | Round 160 (pre-registered, inverting all remaining un-inverted ICT strategies) | 0cf6101 | 35496 | -140.2 | -125.8 | 0.00 / 0.000 | no edge |
| 207 | 2026-09-27 | INVERTED P2 FVG (displacement/VWAP/killzone/50%), 5-min, MNQ + MGC | Round 160 (pre-registered, inverting all remaining un-inverted ICT strategies) | 0cf6101 | 7765 | -192.1 | -178.6 | 0.00 / 0.000 | no edge |
| 208 | 2026-09-27 | INVERTED P1 plain FVG retest, 15-min, MNQ + MGC | Round 160 (pre-registered, inverting all remaining un-inverted ICT strategies) | 0cf6101 | 16752 | -137.1 | -125.7 | 0.00 / 0.000 | no edge |
| 209 | 2026-09-27 | INVERTED P2 FVG (displacement/VWAP/killzone/50%), 15-min, MNQ + MGC | Round 160 (pre-registered, inverting all remaining un-inverted ICT strategies) | 0cf6101 | 4687 | -191.2 | -180.2 | 0.00 / 0.000 | no edge |
| 210 | 2026-09-27 | INVERTED ICT Order Block retest, 1R, MNQ + MGC | Round 160 (pre-registered, inverting all remaining un-inverted ICT strategies) | 0cf6101 | 25529 | -80.7 | +3.2 | 0.00 / 0.000 | no edge |
| 211 | 2026-09-27 | INVERTED ICT Order Block retest, 2R, MNQ + MGC | Round 160 (pre-registered, inverting all remaining un-inverted ICT strategies) | 0cf6101 | 24548 | -77.5 | +6.4 | 0.00 / 0.000 | no edge |
| 212 | 2026-09-27 | INVERTED ICT Order Block retest, 3R, MNQ + MGC | Round 160 (pre-registered, inverting all remaining un-inverted ICT strategies) | 0cf6101 | 23453 | -74.1 | +10.0 | 0.00 / 0.000 | no edge |
| 213 | 2026-09-27 | INVERTED ICT Silver Bullet, 1:1, MNQ + MGC | Round 160 (pre-registered, inverting all remaining un-inverted ICT strategies) | 0cf6101 | 1739 | -1.1 | +6.6 | 0.40 / 0.536 | no edge |
| 214 | 2026-09-27 | INVERTED ICT Silver Bullet, 1:2, MNQ + MGC | Round 160 (pre-registered, inverting all remaining un-inverted ICT strategies) | 0cf6101 | 1584 | +0.9 | +8.6 | 0.28 / 0.842 | no edge |
| 215 | 2026-09-27 | INVERTED MNQ 4H Po3 06:00-10:00, both directions | Round 160 (pre-registered, inverting all remaining un-inverted ICT strategies) | 0cf6101 | 859 | +36.5 | +83.6 | 0.20 / 0.930 | no edge |
| 216 | 2026-09-27 | INVERTED MNQ 4H Po3 06:00-10:00, near-ATH longs only | Round 160 (pre-registered, inverting all remaining un-inverted ICT strategies) | 0cf6101 | 279 | -84.0 | -39.0 | 0.31 / 0.060 | no edge |
| 217 | 2026-09-27 | INVERTED MNQ 4H Po3 10:00-14:00, both directions | Round 160 (pre-registered, inverting all remaining un-inverted ICT strategies) | 0cf6101 | 883 | +39.6 | +60.5 | 0.73 / 0.801 | no edge |
| 218 | 2026-09-27 | INVERTED MNQ 4H Po3 10:00-14:00, near-ATH longs only | Round 160 (pre-registered, inverting all remaining un-inverted ICT strategies) | 0cf6101 | 279 | -50.2 | -30.5 | 0.04 / 0.420 | no edge |
| 219 | 2026-09-27 | 10Y note (ZN) prior-day move -> same-direction ES/NQ/YM/RTY open->close (discount-rate channel) | Round 162 (pre-registered, new idea class: rates/discount-rate channel leading equities) | 394e12a | 13127 | -0.0 | +0.0 | 0.00 / 0.704 | no edge |
| 220 | 2026-09-27 | Long Tue-Fri, flat Monday, ES/NQ/YM/RTY (weekend effect) | Round 163 (pre-registered, new idea class: day-of-week seasonality) | 5019966 | 17353 | -0.0 | +0.0 | 0.00 / 0.835 | no edge |
| 221 | 2026-09-27 | Short Monday only, flat Tue-Fri, ES/NQ/YM/RTY (Monday-effect direct test) | Round 163 (pre-registered, new idea class: day-of-week seasonality) | 5019966 | 4031 | -0.1 | -0.1 | 0.00 / 0.000 | no edge |
| 222 | 2026-09-27 | Crude oil (CL) prior-day move -> OPPOSITE-direction ES/NQ/YM/RTY open->close (cost-push channel) | Round 164 (pre-registered, new idea class: oil cost-push channel leading equities) | 1834ed9 | 13205 | -0.1 | -0.0 | 0.00 / 0.001 | no edge |
| 223 | 2026-09-27 | VIX/VIX3M backwardation extreme (z>=1.5) -> short ES/NQ/YM/RTY next session | Round 165 (pre-registered, new idea class: VIX term-structure shape) | 8eb9dd2 | 1932 | -0.1 | -0.1 | 0.11 / 0.002 | no edge |
| 224 | 2026-09-27 | VIX/VIX3M contango extreme (z<=-1.5) -> long ES/NQ/YM/RTY next session | Round 165 (pre-registered, new idea class: VIX term-structure shape) | 8eb9dd2 | 1284 | -0.1 | -0.0 | 0.01 / 0.186 | no edge |
| 225 | 2026-09-27 | Round 166 ensemble: Connors+IBS+month-end+pre-holiday, netted, 4 indices | Round 166 (pre-registered, original strategy: dip-buy-family ensemble) | f3dcc59 | 8105 | +0.1 | +0.1 | 0.94 / 1.000 | no edge |
| 226 | 2026-09-27 | VCORB 1R, no filter, MNQ+MGC | Round 167 (pre-registered, original strategy: volume-confirmed opening-range breakout) | 0aa5052 | 1837 | -0.0 | +7.3 | 0.51 / 0.501 | no edge |
| 227 | 2026-09-27 | VCORB 1R, >=1.5x OR-avg vol, MNQ+MGC | Round 167 (pre-registered, original strategy: volume-confirmed opening-range breakout) | 0aa5052 | 1445 | -2.3 | +5.1 | 0.47 / 0.305 | no edge |
| 228 | 2026-09-27 | VCORB 1R, >=2.5x OR-avg vol, MNQ+MGC | Round 167 (pre-registered, original strategy: volume-confirmed opening-range breakout) | 0aa5052 | 759 | +2.0 | +10.6 | 0.23 / 0.896 | no edge |
| 229 | 2026-09-27 | VCORB 2R, no filter, MNQ+MGC | Round 167 (pre-registered, original strategy: volume-confirmed opening-range breakout) | 0aa5052 | 1837 | -1.3 | +6.0 | 0.64 / 0.218 | no edge |
| 230 | 2026-09-27 | VCORB 2R, >=1.5x OR-avg vol, MNQ+MGC | Round 167 (pre-registered, original strategy: volume-confirmed opening-range breakout) | 0aa5052 | 1445 | +8.4 | +15.8 | 0.91 / 0.429 | no edge |
| 231 | 2026-09-27 | VCORB 2R, >=2.5x OR-avg vol, MNQ+MGC | Round 167 (pre-registered, original strategy: volume-confirmed opening-range breakout) | 0aa5052 | 759 | +14.9 | +23.6 | 0.69 / 0.928 | no edge |
| 232 | 2026-09-27 | VCORB 3R, no filter, MNQ+MGC | Round 167 (pre-registered, original strategy: volume-confirmed opening-range breakout) | 0aa5052 | 1837 | +2.4 | +9.7 | 0.83 / 0.203 | no edge |
| 233 | 2026-09-27 | VCORB 3R, >=1.5x OR-avg vol, MNQ+MGC | Round 167 (pre-registered, original strategy: volume-confirmed opening-range breakout) | 0aa5052 | 1445 | +9.2 | +16.6 | 0.90 / 0.460 | no edge |
| 234 | 2026-09-27 | VCORB 3R, >=2.5x OR-avg vol, MNQ+MGC | Round 167 (pre-registered, original strategy: volume-confirmed opening-range breakout) | 0aa5052 | 759 | +11.2 | +19.9 | 0.71 / 0.798 | no edge |
| 235 | 2026-09-27 | VCORB hold-to-close, no filter, MNQ+MGC | Round 167 (pre-registered, original strategy: volume-confirmed opening-range breakout) | 0aa5052 | 1837 | -0.1 | +7.2 | 0.79 / 0.106 | no edge |
| 236 | 2026-09-27 | VCORB hold-to-close, >=1.5x OR-avg vol, MNQ+MGC | Round 167 (pre-registered, original strategy: volume-confirmed opening-range breakout) | 0aa5052 | 1445 | +6.3 | +13.7 | 0.85 / 0.349 | no edge |
| 237 | 2026-09-27 | VCORB hold-to-close, >=2.5x OR-avg vol, MNQ+MGC | Round 167 (pre-registered, original strategy: volume-confirmed opening-range breakout) | 0aa5052 | 759 | +5.1 | +13.8 | 0.63 / 0.603 | no edge |
| 238 | 2026-09-27 | N1 round-number breakout, target 2S, no filter (replicates Round 148), MNQ+MGC | Round 168 (pre-registered, does volume confirmation generalize past the ORB?) | c5f59c4 | 4972 | +0.7 | +9.8 | 0.51 / 0.582 | no edge |
| 239 | 2026-09-27 | N1 round-number breakout, target 2S, >=1.5x trailing-30-bar vol, MNQ+MGC | Round 168 (pre-registered, does volume confirmation generalize past the ORB?) | c5f59c4 | 3730 | +0.7 | +10.0 | 0.57 / 0.466 | no edge |
| 240 | 2026-09-27 | N1 round-number breakout, target 2S, >=2.5x trailing-30-bar vol, MNQ+MGC | Round 168 (pre-registered, does volume confirmation generalize past the ORB?) | c5f59c4 | 2563 | -0.5 | +9.5 | 0.66 / 0.244 | no edge |
| 241 | 2026-09-27 | N2 previous-day high/low breakout, target 2S, no filter (replicates Round 148), MNQ+MGC | Round 168 (pre-registered, does volume confirmation generalize past the ORB?) | c5f59c4 | 1531 | -2.7 | +7.5 | 0.50 / 0.281 | no edge |
| 242 | 2026-09-27 | N2 previous-day high/low breakout, target 2S, >=1.5x trailing-30-bar vol, MNQ+MGC | Round 168 (pre-registered, does volume confirmation generalize past the ORB?) | c5f59c4 | 1154 | +2.7 | +13.4 | 0.63 / 0.470 | no edge |
| 243 | 2026-09-27 | N2 previous-day high/low breakout, target 2S, >=2.5x trailing-30-bar vol, MNQ+MGC | Round 168 (pre-registered, does volume confirmation generalize past the ORB?) | c5f59c4 | 908 | -4.8 | +6.6 | 0.39 / 0.381 | no edge |
| 244 | 2026-09-27 | N3 overnight high/low breakout in RTH, target 2S, no filter (replicates Round 148), MNQ+MGC | Round 168 (pre-registered, does volume confirmation generalize past the ORB?) | c5f59c4 | 1602 | -13.9 | -4.4 | 0.14 / 0.080 | no edge |
| 245 | 2026-09-27 | N3 overnight high/low breakout in RTH, target 2S, >=1.5x trailing-30-bar vol, MNQ+MGC | Round 168 (pre-registered, does volume confirmation generalize past the ORB?) | c5f59c4 | 1254 | -12.2 | -2.3 | 0.25 / 0.085 | no edge |
| 246 | 2026-09-27 | N3 overnight high/low breakout in RTH, target 2S, >=2.5x trailing-30-bar vol, MNQ+MGC | Round 168 (pre-registered, does volume confirmation generalize past the ORB?) | c5f59c4 | 861 | -21.4 | -10.8 | 0.22 / 0.010 | no edge |
| 247 | 2026-09-27 | VCORB 2R, >=3.5x OR-avg vol, MNQ+MGC | Round 169 (pre-registered, extending + decomposing Round 167's ORB volume finding) | 174f31f | 512 | -5.8 | +3.0 | 0.47 / 0.257 | no edge |
| 248 | 2026-09-27 | VCORB 2R, >=5.0x OR-avg vol, MNQ+MGC | Round 169 (pre-registered, extending + decomposing Round 167's ORB volume finding) | 174f31f | 306 | -4.5 | +4.4 | 0.59 / 0.174 | no edge |
| 249 | 2026-09-27 | VCORB 2R, >=2.5x OR-avg vol, MNQ only | Round 169 (pre-registered, extending + decomposing Round 167's ORB volume finding) | 174f31f | 99 | +32.8 | +35.8 | 0.85 / 0.711 | no edge |
| 250 | 2026-09-27 | VCORB 2R, >=2.5x OR-avg vol, MGC only | Round 169 (pre-registered, extending + decomposing Round 167's ORB volume finding) | 174f31f | 660 | +12.3 | +21.8 | 0.58 / 0.908 | no edge |
| 251 | 2026-09-27 | VCORB 2R, >=0.0x OR-avg vol, ES (Databento, full 2019-2026) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 1798 | +1.3 | +27.8 | 0.69 / 0.160 | no edge |
| 252 | 2026-09-27 | VCORB 2R, >=0.0x OR-avg vol, ES (Databento, pre-2023 (never used before)) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 837 | +2.6 | +29.1 | 0.52 / nan | no edge |
| 253 | 2026-09-27 | VCORB 2R, >=1.5x OR-avg vol, ES (Databento, full 2019-2026) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 1677 | +28.2 | +54.6 | 0.77 / 0.801 | no edge |
| 254 | 2026-09-27 | VCORB 2R, >=1.5x OR-avg vol, ES (Databento, pre-2023 (never used before)) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 775 | +0.7 | +27.1 | 0.49 / nan | no edge |
| 255 | 2026-09-27 | VCORB 2R, >=2.5x OR-avg vol, ES (Databento, full 2019-2026) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 1512 | -15.6 | +10.8 | 0.30 / 0.230 | no edge |
| 256 | 2026-09-27 | VCORB 2R, >=2.5x OR-avg vol, ES (Databento, pre-2023 (never used before)) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 701 | -52.6 | -26.2 | 0.01 / nan | no edge |
| 257 | 2026-09-27 | VCORB 2R, >=0.0x OR-avg vol, NQ (Databento, full 2019-2026) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 1793 | +76.3 | +87.5 | 0.95 / 0.516 | no edge |
| 258 | 2026-09-27 | VCORB 2R, >=0.0x OR-avg vol, NQ (Databento, pre-2023 (never used before)) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 832 | +44.3 | +55.5 | 0.73 / nan | no edge |
| 259 | 2026-09-27 | VCORB 2R, >=1.5x OR-avg vol, NQ (Databento, full 2019-2026) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 1492 | +47.5 | +58.7 | 0.77 / 0.694 | no edge |
| 260 | 2026-09-27 | VCORB 2R, >=1.5x OR-avg vol, NQ (Databento, pre-2023 (never used before)) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 654 | -13.3 | -2.1 | 0.41 / nan | no edge |
| 261 | 2026-09-27 | VCORB 2R, >=2.5x OR-avg vol, NQ (Databento, full 2019-2026) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 855 | -3.8 | +7.4 | 0.45 / 0.478 | no edge |
| 262 | 2026-09-27 | VCORB 2R, >=2.5x OR-avg vol, NQ (Databento, pre-2023 (never used before)) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 266 | -114.0 | -102.8 | 0.05 / nan | no edge |
| 263 | 2026-09-27 | VCORB 2R, >=0.0x OR-avg vol, GC (Databento, full 2019-2026) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 1868 | -7.0 | +14.5 | 0.56 / 0.334 | no edge |
| 264 | 2026-09-27 | VCORB 2R, >=0.0x OR-avg vol, GC (Databento, pre-2023 (never used before)) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 909 | +33.6 | +55.1 | 0.91 / nan | no edge |
| 265 | 2026-09-27 | VCORB 2R, >=1.5x OR-avg vol, GC (Databento, full 2019-2026) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 1764 | +2.4 | +23.9 | 0.80 / 0.311 | no edge |
| 266 | 2026-09-27 | VCORB 2R, >=1.5x OR-avg vol, GC (Databento, pre-2023 (never used before)) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 854 | +45.4 | +66.9 | 0.96 / nan | no edge |
| 267 | 2026-09-27 | VCORB 2R, >=2.5x OR-avg vol, GC (Databento, full 2019-2026) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 1480 | +58.3 | +79.7 | 0.92 / 0.811 | no edge |
| 268 | 2026-09-27 | VCORB 2R, >=2.5x OR-avg vol, GC (Databento, pre-2023 (never used before)) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 722 | +34.6 | +56.1 | 0.88 / nan | no edge |
| 269 | 2026-09-27 | VCORB 2R, >=0.0x OR-avg vol, SI (Databento, full 2019-2026) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 1858 | -79.0 | -27.7 | 0.10 / 0.124 | no edge |
| 270 | 2026-09-27 | VCORB 2R, >=0.0x OR-avg vol, SI (Databento, pre-2023 (never used before)) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 903 | -17.9 | +33.4 | 0.29 / nan | no edge |
| 271 | 2026-09-27 | VCORB 2R, >=1.5x OR-avg vol, SI (Databento, full 2019-2026) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 1748 | -19.9 | +31.4 | 0.20 / 0.482 | no edge |
| 272 | 2026-09-27 | VCORB 2R, >=1.5x OR-avg vol, SI (Databento, pre-2023 (never used before)) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 847 | -1.5 | +49.8 | 0.48 / nan | no edge |
| 273 | 2026-09-27 | VCORB 2R, >=2.5x OR-avg vol, SI (Databento, full 2019-2026) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 1464 | -87.3 | -36.0 | 0.08 / 0.240 | no edge |
| 274 | 2026-09-27 | VCORB 2R, >=2.5x OR-avg vol, SI (Databento, pre-2023 (never used before)) | Round 171 (pre-registered, out-of-sample ORB replication on Databento data) | ea774e8 | 711 | -22.9 | +28.4 | 0.25 / nan | no edge |
| 275 | 2026-09-27 | INVERTED NQ no-filter ORB, 2R, Databento | Round 172 (pre-registered, inverting Round 171's two least-bad Databento cells) | fb067f4 | 1793 | -34.0 | -22.7 | 0.36 / 0.293 | no edge |
| 276 | 2026-09-27 | INVERTED GC >=2.5x vol ORB, 2R, Databento | Round 172 (pre-registered, inverting Round 171's two least-bad Databento cells) | fb067f4 | 1480 | -60.0 | -38.6 | 0.01 / 0.295 | no edge |
| 277 | 2026-09-27 | Sharpe-optimized ORB exit, NQ no-filter, RR=2.0 (IS-selected from {0.5,0.75,1.0,1.5,2.0,3.0}), Databento | Round 173 (pre-registered, IS-selected Sharpe-optimal exit, OOS-validated) | de99097 | 1793 | +76.3 | +87.5 | 0.95 / 0.516 | no edge |
| 278 | 2026-09-27 | Sharpe-optimized ORB exit, GC >=2.5x vol, RR=0.5 (IS-selected from {0.5,0.75,1.0,1.5,2.0,3.0}), Databento | Round 173 (pre-registered, IS-selected Sharpe-optimal exit, OOS-validated) | de99097 | 1480 | +29.0 | +50.4 | 0.96 / 0.624 | no edge |
| 279 | 2026-09-27 | Round 174 confluence (>=2 of 4 dip-buy-family legs agree), 4 indices | Round 174 (pre-registered, confluence/AND combination of the dip-buy family) | ceb3797 | 1343 | +0.2 | +0.2 | 1.00 / 0.999 | no edge |
| 280 | 2026-09-27 | Checkpoint 10:00 ET, money-flow, hold to close, MNQ+MGC | Round 170 (pre-registered, original strategy: cumulative money-flow proxy) | cb4173b | 1840 | -2.6 | +10.9 | 0.77 / 0.135 | no edge |
| 281 | 2026-09-27 | Checkpoint 10:00 ET, price-momentum control, hold to close, MNQ+MGC | Round 170 (pre-registered, original strategy: cumulative money-flow proxy) | cb4173b | 1832 | +8.5 | +18.5 | 0.86 / 0.328 | no edge |
| 282 | 2026-09-27 | Checkpoint 10:30 ET, money-flow, hold to close, MNQ+MGC | Round 170 (pre-registered, original strategy: cumulative money-flow proxy) | cb4173b | 1840 | -4.4 | +5.8 | 0.48 / 0.198 | no edge |
| 283 | 2026-09-27 | Checkpoint 10:30 ET, price-momentum control, hold to close, MNQ+MGC | Round 170 (pre-registered, original strategy: cumulative money-flow proxy) | cb4173b | 1835 | +5.4 | +12.6 | 0.85 / 0.389 | no edge |
| 284 | 2026-09-27 | GC/SI ratio z>=1.5 -> fade (short rich leg/long cheap leg) | Round 176 (pre-registered, new methodology: Gold/Silver ratio pairs trade) | 0522b5a | 513 | -0.0 | -0.0 | 0.02 / 0.255 | no edge |
| 285 | 2026-09-27 | GC/SI ratio z>=2.0 -> fade (short rich leg/long cheap leg) | Round 176 (pre-registered, new methodology: Gold/Silver ratio pairs trade) | 0522b5a | 237 | -0.1 | -0.0 | 0.08 / 0.069 | no edge |
| 286 | 2026-09-27 | Volume-spike fade (>=4x trailing 30-bar vol), GC, hold 5 bars, Databento | Round 177 (pre-registered, formalizing an exploratory volume-spike scan) | 65daf5b | 55313 | -151.7 | +38.1 | 0.00 / 0.001 | no edge |
| 287 | 2026-09-27 | Volume-spike fade (>=4x trailing 30-bar vol), SI, hold 5 bars, Databento | Round 177 (pre-registered, formalizing an exploratory volume-spike scan) | 65daf5b | 66545 | -305.0 | +28.8 | 0.00 / 0.000 | no edge |
| 288 | 2026-09-27 | Volume-spike continue (>=4x trailing 30-bar vol), NQ, hold 15 bars, Databento | Round 177 (pre-registered, formalizing an exploratory volume-spike scan) | 65daf5b | 37394 | -39.7 | +38.5 | 0.00 / 0.428 | no edge |
| 289 | 2026-09-28 | Volume Profile POC reversion, ES, Databento | Round 178 (pre-registered, new idea class: volume profile POC reversion) | cd145ba | 1308 | -7.4 | +19.7 | 0.58 / 0.113 | no edge |
| 290 | 2026-09-28 | Volume Profile POC reversion, NQ, Databento | Round 178 (pre-registered, new idea class: volume profile POC reversion) | cd145ba | 1348 | +98.0 | +109.3 | 0.98 / 0.848 | no edge |
| 291 | 2026-09-28 | Volume Profile POC reversion, GC, Databento | Round 178 (pre-registered, new idea class: volume profile POC reversion) | cd145ba | 1577 | -12.4 | +9.4 | 0.08 / 0.581 | no edge |
| 292 | 2026-09-28 | Volume Profile POC reversion, SI, Databento | Round 178 (pre-registered, new idea class: volume profile POC reversion) | cd145ba | 1555 | -26.0 | +27.6 | 0.24 / 0.351 | no edge |
| 293 | 2026-09-28 | Harmonic XABCD patterns (7 combined, sigma pooled [0.01, 0.02, 0.03]), ES, hourly Databento | Round 180 (pre-registered, formalizing a /watched video: harmonic XABCD patterns) | 2049381 | 32 | -1436.1 | -1407.4 | 0.01 / 0.000 | no edge |
| 294 | 2026-09-28 | Harmonic XABCD patterns (7 combined, sigma pooled [0.01, 0.02, 0.03]), NQ, hourly Databento | Round 180 (pre-registered, formalizing a /watched video: harmonic XABCD patterns) | 2049381 | 46 | -442.9 | -431.4 | 0.31 / 0.466 | no edge |
| 295 | 2026-09-28 | Harmonic XABCD patterns (7 combined, sigma pooled [0.01, 0.02, 0.03]), GC, hourly Databento | Round 180 (pre-registered, formalizing a /watched video: harmonic XABCD patterns) | 2049381 | 34 | -281.2 | -260.0 | 0.91 / 0.012 | no edge |
| 296 | 2026-09-28 | Harmonic XABCD patterns (7 combined, sigma pooled [0.01, 0.02, 0.03]), SI, hourly Databento | Round 180 (pre-registered, formalizing a /watched video: harmonic XABCD patterns) | 2049381 | 113 | -419.0 | -363.3 | 0.18 / 0.234 | no edge |
| 297 | 2026-09-28 | Daily RTH gap fade, |gap|>=0.5x vol, ES+NQ+GC+SI | Round 181 (pre-registered, new idea class: the ordinary daily overnight gap) | 451c139 | 3957 | -0.0 | -0.0 | 0.06 / 0.401 | no edge |
| 298 | 2026-09-28 | Daily RTH gap follow, |gap|>=0.5x vol, ES+NQ+GC+SI | Round 181 (pre-registered, new idea class: the ordinary daily overnight gap) | 451c139 | 3957 | -0.0 | +0.0 | 0.25 / 0.417 | no edge |
| 299 | 2026-09-28 | Daily RTH gap fade, |gap|>=1.0x vol, ES+NQ+GC+SI | Round 181 (pre-registered, new idea class: the ordinary daily overnight gap) | 451c139 | 2069 | -0.1 | -0.0 | 0.01 / 0.606 | no edge |
| 300 | 2026-09-28 | Daily RTH gap follow, |gap|>=1.0x vol, ES+NQ+GC+SI | Round 181 (pre-registered, new idea class: the ordinary daily overnight gap) | 451c139 | 2069 | +0.0 | +0.0 | 0.75 / 0.283 | no edge |
| 301 | 2026-09-28 | Gold (GC) prior-day move -> OPPOSITE-direction ES/NQ/YM/RTY open->close (flight-to-safety channel) | Round 182 (pre-registered, new idea class: gold as a flight-to-safety leader) | 2fe08bc | 6394 | -0.0 | +0.0 | 0.55 / 0.065 | no edge |
| 302 | 2026-09-28 | Volume Profile POC reversion, NQ, bin size x2 (robustness pass on Round 178), Databento | Round 183 (pre-registered, robustness pass on Round 178's NQ POC lead) | 9be1eca | 1360 | +82.4 | +93.6 | 0.97 / 0.740 | no edge |
| 303 | 2026-09-28 | Volume Profile POC reversion, NQ, bin size x4 (robustness pass on Round 178), Databento | Round 183 (pre-registered, robustness pass on Round 178's NQ POC lead) | 9be1eca | 1360 | +81.4 | +92.7 | 0.98 / 0.704 | no edge |
| 304 | 2026-09-28 | Volume Profile POC reversion, NQ, lookback 10d (robustness pass on Round 178), Databento | Round 183 (pre-registered, robustness pass on Round 178's NQ POC lead) | 9be1eca | 1351 | +96.1 | +107.4 | 0.96 / 0.927 | no edge |
| 305 | 2026-09-28 | Volume Profile POC reversion, NQ, lookback 30d (robustness pass on Round 178), Databento | Round 183 (pre-registered, robustness pass on Round 178's NQ POC lead) | 9be1eca | 1342 | +104.1 | +115.4 | 0.99 / 0.863 | no edge |
| 306 | 2026-09-28 | Volume Profile POC reversion, NQ, lookback 40d (robustness pass on Round 178), Databento | Round 183 (pre-registered, robustness pass on Round 178's NQ POC lead) | 9be1eca | 1333 | +101.0 | +112.3 | 0.98 / 0.902 | no edge |
| 307 | 2026-09-28 | Volume Profile POC reversion, NQ, threshold 0.1x (robustness pass on Round 178), Databento | Round 183 (pre-registered, robustness pass on Round 178's NQ POC lead) | 9be1eca | 1483 | +102.6 | +114.2 | 1.00 / 0.915 | no edge |
| 308 | 2026-09-28 | Volume Profile POC reversion, NQ, threshold 0.2x (robustness pass on Round 178), Databento | Round 183 (pre-registered, robustness pass on Round 178's NQ POC lead) | 9be1eca | 1194 | +70.2 | +81.4 | 0.89 / 0.704 | no edge |
| 309 | 2026-09-28 | Volume Profile POC reversion, NQ, threshold 0.25x (robustness pass on Round 178), Databento | Round 183 (pre-registered, robustness pass on Round 178's NQ POC lead) | 9be1eca | 1070 | +108.7 | +119.9 | 0.95 / 0.762 | no edge |
| 310 | 2026-09-28 | Value Area breakout continuation, ES, Databento | Round 184 (pre-registered, new idea class: value-area breakout/rejection) | 14accb0 | 1104 | -100.6 | -74.3 | 0.02 / 0.317 | no edge |
| 311 | 2026-09-28 | Value Area breakout rejection, ES, Databento | Round 184 (pre-registered, new idea class: value-area breakout/rejection) | 14accb0 | 1104 | +29.4 | +74.6 | 0.59 / 0.875 | no edge |
| 312 | 2026-09-28 | Value Area breakout continuation, NQ, Databento | Round 184 (pre-registered, new idea class: value-area breakout/rejection) | 14accb0 | 1099 | -155.3 | -144.1 | 0.11 / 0.100 | no edge |
| 313 | 2026-09-28 | Value Area breakout rejection, NQ, Databento | Round 184 (pre-registered, new idea class: value-area breakout/rejection) | 14accb0 | 1099 | +168.0 | +183.7 | 0.93 / 0.972 | no edge |
| 314 | 2026-09-28 | Value Area breakout continuation, GC, Databento | Round 184 (pre-registered, new idea class: value-area breakout/rejection) | 14accb0 | 1385 | -21.5 | -0.3 | 0.59 / 0.281 | no edge |
| 315 | 2026-09-28 | Value Area breakout rejection, GC, Databento | Round 184 (pre-registered, new idea class: value-area breakout/rejection) | 14accb0 | 1385 | -46.1 | -8.0 | 0.09 / 0.377 | no edge |
| 316 | 2026-09-28 | Value Area breakout continuation, SI, Databento | Round 184 (pre-registered, new idea class: value-area breakout/rejection) | 14accb0 | 1376 | -18.6 | +32.7 | 0.06 / 0.636 | no edge |
| 317 | 2026-09-28 | Value Area breakout rejection, SI, Databento | Round 184 (pre-registered, new idea class: value-area breakout/rejection) | 14accb0 | 1376 | -164.1 | -92.9 | 0.03 / 0.073 | no edge |
| 318 | 2026-09-28 | Value Area rejection, NQ, bin size x2 (robustness pass on Round 184), Databento | Round 185 (pre-registered, robustness pass on Round 184's NQ Value Area rejection lead) | b4156fd | 1142 | +157.7 | +173.5 | 0.93 / 0.960 | no edge |
| 319 | 2026-09-28 | Value Area rejection, NQ, bin size x4 (robustness pass on Round 184), Databento | Round 185 (pre-registered, robustness pass on Round 184's NQ Value Area rejection lead) | b4156fd | 1156 | +158.1 | +174.5 | 0.94 / 0.925 | no edge |
| 320 | 2026-09-28 | Value Area rejection, NQ, VA 60% (robustness pass on Round 184), Databento | Round 185 (pre-registered, robustness pass on Round 184's NQ Value Area rejection lead) | b4156fd | 1186 | +172.1 | +188.2 | 0.93 / 0.986 | no edge |
| 321 | 2026-09-28 | Value Area rejection, NQ, VA 80% (robustness pass on Round 184), Databento | Round 185 (pre-registered, robustness pass on Round 184's NQ Value Area rejection lead) | b4156fd | 1003 | +160.5 | +176.9 | 0.86 / 0.982 | no edge |
| 322 | 2026-09-28 | NQ POC reversion + Value Area rejection, netted per day, Databento | Round 186 (pre-registered, does combining NQ's two Market Profile leads help?) | 08973b8 | 1452 | +218.2 | n/a | 0.97 / 0.959 | no edge |
| 323 | 2026-09-28 | Daily overnight gap fade, ES, Databento | Round 187 (pre-registered, new idea class: simple daily gap fade) | 0d03fa6 | 977 | -26.3 | +0.8 | 0.36 / 0.118 | no edge |
| 324 | 2026-09-28 | Daily overnight gap fade, NQ, Databento | Round 187 (pre-registered, new idea class: simple daily gap fade) | 0d03fa6 | 1004 | +114.1 | +125.3 | 0.97 / 0.619 | no edge |
| 325 | 2026-09-28 | Daily overnight gap fade, GC, Databento | Round 187 (pre-registered, new idea class: simple daily gap fade) | 0d03fa6 | 1051 | -20.8 | +1.0 | 0.36 / 0.304 | no edge |
| 326 | 2026-09-28 | Daily overnight gap fade, SI, Databento | Round 187 (pre-registered, new idea class: simple daily gap fade) | 0d03fa6 | 1042 | +5.9 | +59.6 | 0.45 / 0.559 | no edge |
| 327 | 2026-09-28 | NQ POC + Value Area rejection + gap fade, netted per day, Databento | Round 188 (pre-registered, does combining all of NQ's leads help?) | 3bd1c7a | 1484 | +290.7 | n/a | 0.98 / 0.918 | no edge |
| 328 | 2026-09-26 | FVG real secrets [none], 1:2, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 2972 | -2.4 | +3.9 | 0.15 / 0.697 | no edge |
| 329 | 2026-09-26 | FVG real secrets [equilibrium], 1:2, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 168 | +12.1 | +18.4 | 0.64 / 0.642 | no edge |
| 330 | 2026-09-26 | FVG real secrets [trend], 1:2, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 1590 | -10.0 | -3.8 | 0.15 / 0.296 | no edge |
| 331 | 2026-09-26 | FVG real secrets [trend, equilibrium], 1:2, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 27 | +8.7 | +16.7 | 0.48 / 0.564 | no edge |
| 332 | 2026-09-26 | FVG real secrets [color], 1:2, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 1917 | -0.4 | +5.5 | 0.58 / 0.386 | no edge |
| 333 | 2026-09-26 | FVG real secrets [color, equilibrium], 1:2, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 29 | -19.1 | -11.4 | 0.29 / 0.564 | no edge |
| 334 | 2026-09-26 | FVG real secrets [color, trend], 1:2, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 994 | -6.2 | -0.3 | 0.52 / 0.184 | no edge |
| 335 | 2026-09-26 | FVG real secrets [color, trend, equilibrium], 1:2, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 8 | -63.9 | -54.8 | 0.01 / 0.755 | no edge |
| 336 | 2026-09-26 | FVG real secrets [size], 1:2, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 1558 | -1.4 | +3.2 | 0.27 / 0.624 | no edge |
| 337 | 2026-09-26 | FVG real secrets [size, equilibrium], 1:2, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 43 | +28.1 | +32.4 | 0.73 / 0.533 | no edge |
| 338 | 2026-09-26 | FVG real secrets [size, trend], 1:2, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 728 | -2.7 | +1.9 | 0.50 / 0.384 | no edge |
| 339 | 2026-09-26 | FVG real secrets [size, trend, equilibrium], 1:2, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 6 | +246.2 | +254.7 | 0.99 / 1.000 | CANDIDATE |
| 340 | 2026-09-26 | FVG real secrets [size, color], 1:2, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 888 | -6.2 | -1.8 | 0.55 / 0.212 | no edge |
| 341 | 2026-09-26 | FVG real secrets [size, color, equilibrium], 1:2, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 5 | -5.6 | +2.4 | 0.55 / 0.000 | no edge |
| 342 | 2026-09-26 | FVG real secrets [size, color, trend], 1:2, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 434 | -7.3 | -3.1 | 0.73 / 0.112 | no edge |
| 343 | 2026-09-26 | FVG real secrets [size, color, trend, equilibrium], 1:2, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 2 | -23.0 | -10.0 | 0.24 / nan | no edge |
| 344 | 2026-09-26 | FVG real secrets [none], 1:3, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 2788 | -2.3 | +3.9 | 0.24 / 0.609 | no edge |
| 345 | 2026-09-26 | FVG real secrets [equilibrium], 1:3, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 168 | +13.7 | +20.0 | 0.57 / 0.713 | no edge |
| 346 | 2026-09-26 | FVG real secrets [trend], 1:3, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 1521 | -2.4 | +3.9 | 0.46 / 0.403 | no edge |
| 347 | 2026-09-26 | FVG real secrets [trend, equilibrium], 1:3, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 27 | +4.2 | +12.2 | 0.27 / 0.694 | no edge |
| 348 | 2026-09-26 | FVG real secrets [color], 1:3, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 1872 | -1.1 | +4.9 | 0.54 / 0.384 | no edge |
| 349 | 2026-09-26 | FVG real secrets [color, equilibrium], 1:3, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 29 | -15.0 | -7.3 | 0.20 / 0.702 | no edge |
| 350 | 2026-09-26 | FVG real secrets [color, trend], 1:3, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 973 | -1.7 | +4.1 | 0.69 / 0.224 | no edge |
| 351 | 2026-09-26 | FVG real secrets [color, trend, equilibrium], 1:3, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 8 | -29.5 | -20.4 | 0.01 / 0.755 | no edge |
| 352 | 2026-09-26 | FVG real secrets [size], 1:3, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 1520 | -4.2 | +0.3 | 0.21 / 0.543 | no edge |
| 353 | 2026-09-26 | FVG real secrets [size, equilibrium], 1:3, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 43 | +28.3 | +32.6 | 0.62 / 0.627 | no edge |
| 354 | 2026-09-26 | FVG real secrets [size, trend], 1:3, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 719 | -5.5 | -0.9 | 0.51 / 0.265 | no edge |
| 355 | 2026-09-26 | FVG real secrets [size, trend, equilibrium], 1:3, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 6 | +129.8 | +138.3 | 0.97 / 1.000 | CANDIDATE |
| 356 | 2026-09-26 | FVG real secrets [size, color], 1:3, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 878 | -12.7 | -8.2 | 0.36 / 0.140 | no edge |
| 357 | 2026-09-26 | FVG real secrets [size, color, equilibrium], 1:3, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 5 | -9.9 | -1.9 | 0.55 / 0.000 | no edge |
| 358 | 2026-09-26 | FVG real secrets [size, color, trend], 1:3, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 430 | -8.7 | -4.6 | 0.77 / 0.073 | no edge |
| 359 | 2026-09-26 | FVG real secrets [size, color, trend, equilibrium], 1:3, 60-min, MNQ+MGC | Round 189 (pre-registered, the video's own 5 FVG secrets) | e51c3b2 | 2 | -23.0 | -10.0 | 0.24 / nan | no edge |
| 360 | 2026-09-28 | 2-leg (Round 186 POC+VA) discretized +1650/-900/0 | Round 190 (pre-registered, disciplined daily bracket, +1650/-900/0) | 0f7bce1 | 1452 | +81.7 | n/a | 0.98 / 0.906 | no edge |
| 361 | 2026-09-28 | 3-leg (Round 188 +gap fade) discretized +1650/-900/0 | Round 190 (pre-registered, disciplined daily bracket, +1650/-900/0) | 0f7bce1 | 1484 | +48.5 | n/a | 0.91 / 0.753 | no edge |
| 362 | 2026-09-28 | Daily overnight gap continuation, ES, Databento | Round 193 (pre-registered, new idea class: daily gap continuation, opposite of Round 187's fade) | b8f80c0 | 977 | +5.9 | +33.0 | 0.38 / 0.779 | no edge |
| 363 | 2026-09-28 | Daily overnight gap continuation, NQ, Databento | Round 193 (pre-registered, new idea class: daily gap continuation, opposite of Round 187's fade) | b8f80c0 | 1004 | +65.2 | +76.4 | 0.87 / 0.572 | no edge |
| 364 | 2026-09-28 | Daily overnight gap continuation, GC, Databento | Round 193 (pre-registered, new idea class: daily gap continuation, opposite of Round 187's fade) | b8f80c0 | 1051 | +15.5 | +37.3 | 0.94 / 0.234 | no edge |
| 365 | 2026-09-28 | Daily overnight gap continuation, SI, Databento | Round 193 (pre-registered, new idea class: daily gap continuation, opposite of Round 187's fade) | b8f80c0 | 1042 | -103.6 | -49.8 | 0.08 / 0.034 | no edge |
| 366 | 2026-09-28 | Quad-witching Friday fade on next trading day, ES=F (R units) | Round 194 (pre-registered, new idea class: quad-witching/Nasdaq-100 rebalance reversal) | 69a345e | 99 | -0.042R | +0.012R | 0.25 / 0.519 | no edge |
| 367 | 2026-09-28 | Quad-witching Friday fade on next trading day, NQ=F (R units) | Round 194 (pre-registered, new idea class: quad-witching/Nasdaq-100 rebalance reversal) | 69a345e | 102 | -0.168R | -0.131R | 0.17 / 0.112 | no edge |
| 368 | 2026-09-28 | Quad-witching Friday fade on next trading day, YM=F (R units) | Round 194 (pre-registered, new idea class: quad-witching/Nasdaq-100 rebalance reversal) | 69a345e | 92 | -0.008R | +0.032R | 0.18 / 0.705 | no edge |
| 369 | 2026-09-28 | Quad-witching Friday fade on next trading day, RTY=F (R units) | Round 194 (pre-registered, new idea class: quad-witching/Nasdaq-100 rebalance reversal) | 69a345e | 36 | -0.053R | -0.030R | nan / 0.392 | no edge |
| 370 | 2026-09-28 | ES leads NQ, 5-min bars, 2.5 SD, 1-bar hold, Databento | Round 195 (pre-registered, new idea class: ES/NQ intraday lead-lag) | aa2ddc8 | 2948 | -19.0 | -7.7 | 0.02 / 0.828 | no edge |
| 371 | 2026-09-28 | NQ leads ES, 5-min bars, 2.5 SD, 1-bar hold, Databento | Round 195 (pre-registered, new idea class: ES/NQ intraday lead-lag) | aa2ddc8 | 2896 | -30.8 | -4.5 | 0.00 / 0.242 | no edge |
| 372 | 2026-09-28 | Supply/demand zone retest continuation (2R), ES, Databento | Round 196 (pre-registered, new idea class: supply/demand zone retest) | d7bb6eb | 435 | -76.2 | +14.0 | 0.00 / 0.176 | no edge |
| 373 | 2026-09-28 | Supply/demand zone retest continuation (2R), NQ, Databento | Round 196 (pre-registered, new idea class: supply/demand zone retest) | d7bb6eb | 265 | -47.5 | -8.7 | 0.09 / 0.138 | no edge |
| 374 | 2026-09-28 | Supply/demand zone retest continuation (2R), GC, Databento | Round 196 (pre-registered, new idea class: supply/demand zone retest) | d7bb6eb | 2692 | -74.7 | +47.8 | 0.00 / 0.091 | no edge |
| 375 | 2026-09-28 | Supply/demand zone retest continuation (2R), SI, Databento | Round 196 (pre-registered, new idea class: supply/demand zone retest) | d7bb6eb | 3894 | -130.8 | +10.8 | 0.00 / 0.102 | no edge |
| 376 | 2026-09-28 | Lunch-lull (12:00-13:29 ET) extreme fade, ES, Databento | Round 197 (pre-registered, new idea class: NY lunch-lull session-segment fade) | 3209027 | 1089 | -147.0 | -15.6 | 0.00 / 0.000 | no edge |
| 377 | 2026-09-28 | Lunch-lull (12:00-13:29 ET) extreme fade, NQ, Databento | Round 197 (pre-registered, new idea class: NY lunch-lull session-segment fade) | 3209027 | 1012 | -103.4 | -41.3 | 0.00 / 0.015 | no edge |
| 378 | 2026-09-28 | Lunch-lull (12:00-13:29 ET) extreme fade, GC, Databento | Round 197 (pre-registered, new idea class: NY lunch-lull session-segment fade) | 3209027 | 850 | -116.6 | +2.0 | 0.00 / 0.038 | no edge |
| 379 | 2026-09-28 | Lunch-lull (12:00-13:29 ET) extreme fade, SI, Databento | Round 197 (pre-registered, new idea class: NY lunch-lull session-segment fade) | 3209027 | 851 | -128.1 | +9.8 | 0.00 / 0.002 | no edge |
| 380 | 2026-09-29 | Meta-labeling filter (logistic regression, top 33% confidence) on NQ POC reversion, Databento | Round 198 (pre-registered, new idea class: meta-labeling -- ML filters an existing signal's trades, not price direction) | 9adaaf4 | 82 | +287.3 | n/a | 0.934 / 0.938 | no edge |
| 381 | 2026-09-29 | Meta-labeling filter (logistic regression, top 33% confidence) on NQ Value Area rejection, Databento | Round 199 (extends Round 198's meta-labeling technique to a second leg) | 4e4400c | 67 | +751.1 | n/a | 0.846 / 0.923 | no edge |
| 382 | 2026-09-30 | Checkpoint 10:00 ET, money-flow/price divergence-reversal, hold to close, MNQ+MGC | Round 220 (pre-registered, new idea class: money-flow/price divergence reversal) | e0615c3 | 382 | -54.0 | -23.2 | 0.04 / 0.337 | no edge |
| 383 | 2026-09-30 | Checkpoint 10:00 ET, money-flow/price agreement-continuation control, hold to close, MNQ+MGC | Round 220 (pre-registered, new idea class: money-flow/price divergence reversal) | e0615c3 | 1450 | +10.0 | +18.7 | 0.98 / 0.029 | no edge |
| 384 | 2026-09-30 | Checkpoint 10:30 ET, money-flow/price divergence-reversal, hold to close, MNQ+MGC | Round 220 (pre-registered, new idea class: money-flow/price divergence reversal) | e0615c3 | 376 | -50.7 | -25.6 | 0.02 / 0.430 | no edge |
| 385 | 2026-09-30 | Checkpoint 10:30 ET, money-flow/price agreement-continuation control, hold to close, MNQ+MGC | Round 220 (pre-registered, new idea class: money-flow/price divergence reversal) | e0615c3 | 1459 | +7.8 | +14.1 | 0.96 / 0.188 | no edge |
| 386 | 2026-09-30 | Opening-range (15-min) failure fade, sweep-and-reverse, hold to close, MNQ+MGC | Round 221 (pre-registered, new idea class: opening-range failure fade) | 654caf7 | 2313 | +15.1 | +59.2 | 0.38 / 0.919 | no edge |
| 387 | 2026-09-30 | Opening-range (30-min) failure fade, sweep-and-reverse, hold to close, MNQ+MGC | Round 221 (pre-registered, new idea class: opening-range failure fade) | 654caf7 | 2103 | -9.0 | +34.1 | 0.10 / 0.791 | no edge |
| 388 | 2026-09-30 | Outside-bar (engulfing) reversal, 5-min HTF, hold to close, MNQ+MGC | Round 222 (pre-registered, new idea class: outside-bar/engulfing-candle reversal) | 8b27160 | 5426 | -29.6 | -3.6 | 0.00 / 0.075 | no edge |
| 389 | 2026-09-30 | Outside-bar (engulfing) reversal, 15-min HTF, hold to close, MNQ+MGC | Round 222 (pre-registered, new idea class: outside-bar/engulfing-candle reversal) | 8b27160 | 3103 | +1.5 | +16.7 | 0.87 / 0.026 | no edge |
| 390 | 2026-09-30 | Overnight drift long 18:00->09:29 ET, MNQ, 1 micro (replication of rows 1-2), Databento | Round 238 (pre-registered, stronger-edge hunt) | 9d60774 | 1793 | +14.4 | +16.7 | 0.94 / 0.954 | no edge |
| 391 | 2026-09-30 | Overnight drift long 18:00->09:29 ET, MES, 1 micro (replication of rows 1-2), Databento | Round 238 (pre-registered, stronger-edge hunt) | 9d60774 | 1801 | +5.3 | +9.0 | 0.77 / 0.963 | no edge |
| 392 | 2026-09-30 | Overnight drift long 18:00->09:29 ET, MGC, 1 micro (replication of rows 1-2), Databento | Round 238 (pre-registered, stronger-edge hunt) | 9d60774 | 1867 | +9.9 | +13.1 | 0.73 / 0.917 | no edge |
| 393 | 2026-09-30 | Overnight drift long 18:00->09:29 ET, SIL, 1 micro (replication of rows 1-2), Databento | Round 238 (pre-registered, stronger-edge hunt) | 9d60774 | 1872 | +5.5 | +16.7 | 0.17 / 0.717 | no edge |
| 394 | 2026-09-30 | Intraday NQ-ES spread z-reversion, |z|>=2.5 in / 0 out / 5 stop, 5 MNQ vs beta MES, Databento | Round 238 (pre-registered, stronger-edge hunt) | 9d60774 | 5506 | -34.6 | +7.5 | 0.00 / 0.000 | no edge |
| 395 | 2026-09-30 | Intraday GC-SI spread z-reversion, |z|>=2.5 in / 0 out / 5 stop, 5 MGC vs beta SIL, Databento | Round 238 (pre-registered, stronger-edge hunt) | 9d60774 | 4479 | -39.7 | -5.9 | 0.00 / 0.007 | no edge |
| 396 | 2026-09-30 | POC leg mega-ML filter (L1 logit + HGB, 30 feats, NQ+ES pooled), EV rule, MNQ $300 | Round 245 (pre-registered, POC mega-ML) | 124c396 | 494 | +51.4 | +59.9 | 0.93 / 0.971 | no edge |
| 397 | 2026-09-30 | POC leg L1-logit filter (30 feats, NQ+ES pooled), EV rule, MNQ $300 | Round 245 (pre-registered, POC mega-ML) | 124c396 | 582 | +38.8 | +47.4 | 0.74 / 0.993 | no edge |
| 398 | 2026-09-30 | POC leg Round-198 logit filter (6 feats, NQ), EV rule, MNQ $300 | Round 245 (pre-registered, POC mega-ML) | 124c396 | 623 | +45.5 | +53.7 | 0.93 / 0.970 | no edge |
| 399 | 2026-09-30 | Profile rotation: 5-min rejection toward prior POC (>=0.15S), stop 0.10S, target 0.6 stop, <=12/day, -3R day stop, MNQ $300, Databento | Round 246 (pre-registered, profile rotation) | 8b367a4 | 11428 | -19.1 | -4.3 | 0.00 / 0.052 | no edge |
| 400 | 2026-09-30 | Profile rotation: 5-min rejection toward prior POC (>=0.15S), stop 0.10S, target 0.6 stop, <=12/day, -3R day stop, MES $300, Databento | Round 246 (pre-registered, profile rotation) | 8b367a4 | 9760 | -54.6 | -8.8 | 0.00 / 0.000 | no edge |
| 401 | 2026-09-30 | POC leg payoff reshape at the open: stop 0.15S, target 0.33 x dist to prior POC, MNQ $300, Databento | Round 247 (pre-registered, POC payoff reshape) | 162c51f | 1352 | +3.4 | +13.2 | 0.59 / 0.696 | no edge |
| 402 | 2026-09-30 | POC leg payoff reshape at the open: stop 0.15S, target 0.50 x dist to prior POC, MNQ $300, Databento | Round 247 (pre-registered, POC payoff reshape) | 162c51f | 1352 | +8.7 | +18.5 | 0.80 / 0.562 | no edge |
| 403 | 2026-09-30 | POC leg payoff reshape at the open: stop 0.15S, target 0.75 x dist to prior POC, MNQ $300, Databento | Round 247 (pre-registered, POC payoff reshape) | 162c51f | 1352 | +18.5 | +28.3 | 0.89 / 0.815 | no edge |
| 404 | 2026-09-30 | POC leg payoff reshape at the open: stop 0.15S, target 1.00 x dist to prior POC, MNQ $300, Databento | Round 247 (pre-registered, POC payoff reshape) | 162c51f | 1352 | +22.6 | +32.4 | 0.89 / 0.920 | no edge |
| 405 | 2026-09-30 | POC leg payoff reshape at the open: stop 0.30S, target 0.33 x dist to prior POC, MNQ $300, Databento | Round 247 (pre-registered, POC payoff reshape) | 162c51f | 1352 | -2.0 | +2.4 | 0.31 / 0.541 | no edge |
| 406 | 2026-09-30 | POC leg payoff reshape at the open: stop 0.30S, target 0.50 x dist to prior POC, MNQ $300, Databento | Round 247 (pre-registered, POC payoff reshape) | 162c51f | 1352 | -0.1 | +4.3 | 0.61 / 0.265 | no edge |
| 407 | 2026-09-30 | POC leg payoff reshape at the open: stop 0.30S, target 0.75 x dist to prior POC, MNQ $300, Databento | Round 247 (pre-registered, POC payoff reshape) | 162c51f | 1352 | +8.3 | +12.7 | 0.85 / 0.614 | no edge |
| 408 | 2026-09-30 | POC leg payoff reshape at the open: stop 0.30S, target 1.00 x dist to prior POC, MNQ $300, Databento | Round 247 (pre-registered, POC payoff reshape) | 162c51f | 1352 | +10.6 | +15.1 | 0.80 / 0.874 | no edge |
| 409 | 2026-09-30 | POC leg payoff reshape at the open: stop 0.45S, target 0.33 x dist to prior POC, MNQ $300, Databento | Round 247 (pre-registered, POC payoff reshape) | 162c51f | 1352 | -2.2 | +0.7 | 0.13 / 0.842 | no edge |
| 410 | 2026-09-30 | POC leg payoff reshape at the open: stop 0.45S, target 0.50 x dist to prior POC, MNQ $300, Databento | Round 247 (pre-registered, POC payoff reshape) | 162c51f | 1352 | +0.6 | +3.5 | 0.43 / 0.693 | no edge |
| 411 | 2026-09-30 | POC leg payoff reshape at the open: stop 0.45S, target 0.75 x dist to prior POC, MNQ $300, Databento | Round 247 (pre-registered, POC payoff reshape) | 162c51f | 1352 | +7.7 | +10.6 | 0.77 / 0.867 | no edge |
| 412 | 2026-09-30 | POC leg payoff reshape at the open: stop 0.45S, target 1.00 x dist to prior POC, MNQ $300, Databento | Round 247 (pre-registered, POC payoff reshape) | 162c51f | 1352 | +9.0 | +11.9 | 0.70 / 0.948 | no edge |
| 413 | 2026-09-30 | POC leg payoff reshape at the open: stop 0.45S, target 0.50 x dist (Round 247 C*), MES $300, Databento | Round 247 (pre-registered, POC payoff reshape) | 162c51f | 1312 | -4.6 | +4.7 | 0.18 / 0.440 | no edge |
| 414 | 2026-09-30 | MT5 broker 2-Step, POC leg, flat by 16:10 (US100 CFD), costs+base swap | Round 248 (pre-registered, MT5 broker 2-Step rules, CFD costs) | a55b644 | 1352 | +59.4 | +130.9 | 0.76 / 0.864 | no edge |
| 415 | 2026-09-30 | MT5 broker 2-Step, POC leg, held overnight to next 16:10 (US100 CFD), costs+base swap | Round 248 (pre-registered, MT5 broker 2-Step rules, CFD costs) | a55b644 | 1352 | +55.7 | +129.2 | 0.73 / 0.816 | no edge |
| 416 | 2026-09-30 | MT5 broker 2-Step, the trader TOD+VWAP-Z, flat by 16:00 (US100 CFD), costs+base swap | Round 248 (pre-registered, MT5 broker 2-Step rules, CFD costs) | a55b644 | 5533 | -79.1 | -38.9 | 0.00 / 0.245 | no edge |
| 417 | 2026-09-30 | MT5 broker 2-Step, the trader TOD+VWAP-Z, held overnight 1 session (US100 CFD), costs+base swap | Round 248 (pre-registered, MT5 broker 2-Step rules, CFD costs) | a55b644 | 5519 | -88.1 | -40.6 | 0.00 / 0.308 | no edge |
| 418 | 2026-09-30 | MT5 broker 2-Step, S/R bounce, flat by 16:10 (XAUUSD CFD), costs+base swap | Round 248 (pre-registered, MT5 broker 2-Step rules, CFD costs) | a55b644 | 8152 | -89.9 | +90.1 | 0.00 / 0.902 | no edge |
| 419 | 2026-09-30 | MT5 broker 2-Step, Overnight drift: long US100 close->open, Mon-Thu (control), costs+base swap | Round 248 (pre-registered, MT5 broker 2-Step rules, CFD costs) | a55b644 | 1318 | +51.8 | +264.6 | 0.66 / 0.641 | no edge |
