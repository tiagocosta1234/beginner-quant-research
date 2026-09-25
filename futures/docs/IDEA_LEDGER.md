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
