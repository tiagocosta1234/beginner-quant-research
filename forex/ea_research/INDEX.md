# Forex research index

Every test in this folder that has a written result, grouped by family. The verdict is the first verdict word found
in the result file (most tests were pre-registered with a fixed bar; NOT SHOWN means the bar was not met).

## Swap, carry and overnight holds (13)

| Test | Verdict | Files |
|---|---|---|
| BRK-B12 result (breakout day round 12, 2026-10-15 12:03): overnight range, initial balance, intermarket confir | LEAD | [result](BRK_B12_RESULT.md) / [prereg](PREREG_BRK_B12.md) |
| D2PLUS_RESULT - four refinements of D2 from the trader's 50-hypothesis list (2026-10-15, local clock 19:01) | PASSED | [result](D2PLUS_RESULT.md) / [prereg](PREREG_D2PLUS.md) |
| D2_MT5RULE_RESULT - the D2 book under MT5 broker Pro's exact daily-line and profit-cap rules (2026-10-15, PC c | PASS | [result](D2_MT5RULE_RESULT.md) / [prereg](PREREG_D2_MT5RULE.md) |
| D2_MT5WEEKLY_RESULT - D2 under MT5 broker's written reply (2026-10-15, local clock 19:23) | CLOSED | [result](D2_MT5WEEKLY_RESULT.md) / [prereg](PREREG_D2_MT5WEEKLY.md) |
| V: scheduled US macro events (pre-FOMC drift; release-day continuation): result (2026-10-10, local local clock) | CLOSED | [result](EVENT_MACRO_RESULT.md) / [prereg](PREREG_EVENT_MACRO.md) |
| GN3 result - gold at the Shanghai open and Nasdaq through its overnight range: 0 of 4 pass (2026-10-18 11:05 L | PASS | [result](GN3_RESULT.md) / [prereg](PREREG_GN3.md) |
| GN5 result - Nasdaq overnight-range breakout (GN3 O1) out of time on 2020-21 NQ futures: FAIL (2026-10-18 11:1 | FAIL | [result](GN5_RESULT.md) / [prereg](PREREG_GN5.md) |
| GN6 result - the overnight-range breakout on S&P 500, Dow and gold: 0 of 3; not a mechanism (2026-10-18 11:18  | FAIL | [result](GN6_RESULT.md) / [prereg](PREREG_GN6.md) |
| N2: overnight try-everything grid (480 variants): result (2026-10-10, local local clock) | BEATS | [result](OVERNIGHT_GRID_RESULT.md) / [prereg](PREREG_OVERNIGHT_GRID.md) |
| N: US index overnight (15:55 ET -> 09:35 ET) on MT5 broker: result (2026-10-10, local local clock) | FAIL | [result](OVERNIGHT_RESULT.md) / [prereg](PREREG_OVERNIGHT.md) |
| SWAPFREE_D2X_RESULT - a wider swap-free book does not beat D2 (2026-10-15, local clock 15:26) | DOES NOT BEAT | [result](SWAPFREE_D2X_RESULT.md) / [prereg](PREREG_SWAPFREE_D2X.md) |
| SWAPFREE_DRIFT_RESULT - long-only risk-balanced book on MT5 broker's swap-free terms (2026-10-15, local clock 15: | PASS | [result](SWAPFREE_DRIFT_RESULT.md) / [prereg](PREREG_SWAPFREE_DRIFT.md) |
| XMKT_RESULT - the trader's 50-hypothesis list: triage, D2 refinements and the untested cross-market / daily it | PASS | [result](XMKT_RESULT.md) / [prereg](PREREG_XMKT.md) |

## Blind tests and manual reads (16)

| Test | Verdict | Files |
|---|---|---|
| Result: risk allocation across SDB / XAU5 / ManualDip (2026-10-13) | PASS | [result](ALLOC_RESULT.md) / [prereg](PREREG_ALLOC.md) |
| BRK100B result - 100 ideas on information the breakout tests never used (MT5 broker spread, CME volume, cross- | PASS | [result](BRK100B_RESULT.md) / [prereg](PREREG_BRK100B.md) |
| BRK30 result - 30 untouched breakout ideas on the 38 MT5 broker: 0 pass, most lose the spread | PASS | [result](BRK30_RESULT.md) / [prereg](PREREG_BRK30.md) |
| BRK-SPREAD result (breakout day round 16, 2026-10-15 12:20): relative-spread breakouts lose (two legs = double | PASS | [result](BRK_SPREAD_RESULT.md) / [prereg](PREREG_BRK_SPREAD.md) |
| The daily card replayed on the last six weeks (2026-09-01 .. 2026-10-15, MT5 broker terminal M1 bars, read-onl | NO EDGE | [result](CARD_RECENT_RESULT.md) |
| Family DD result: the frozen ManualDip rule on metals, energy and FX majors (2026-10-12) | see file | [result](DIP_OTHER_RESULT.md) / [prereg](PREREG_DIP_OTHER.md) |
| PRESAMPLE3 result (breakout day round 35, 2026-10-15 14:25, local clock): JPY crosses at the London open do not p | PASS | [result](PRESAMPLE3_RESULT.md) / [prereg](PREREG_PRESAMPLE3.md) |
| Family SM result: ManualSDB on 12 other MT5 broker (2026-10-12) | FAILS | [result](SDB_MARKETS_RESULT.md) / [prereg](PREREG_SDB_MARKETS.md) |
| How optimistic is the M1 engine? Session breakouts and random entries replayed on MT5 broker real ticks (2026- | NO EDGE | [result](TICK_GAP_RESULT.md) |
| USDJPY London-open breakout re-checked for MT5 broker's zero-spread minutes (2026-10-16 18:24 local, local clock | LEAD | [result](USDJPY_SPREADFIX_RESULT.md) |
| Family VD result: implied-vol regime vs ManualDip trade returns (2026-10-12) | see file | [result](VOL_DIP_RESULT.md) / [prereg](PREREG_VOL_DIP.md) |
| Blind replay, batch 1 (January 2026, London, the trader's own entries): gate passed, no verdict yet, 2026-10-1 | PASSED | [result](ema12/BLIND_JAN2026_RESULT.md) |
| EMA1000 with no spread and with limit orders (run 20 Oct 2026 12:08-12:20, main PC, local clock) | NO EDGE | [result](ema12/EMA1000_NOCOST_RESULT.md) / [prereg](ema12/PREREG_EMA1000_NOCOST.md) |
| 12 EMA backtest (the trader's FX Replay, gold): MT5 broker replay and Monte Carlo (2026-10-19 02:2x local clock,  | PASS | [result](ema12/EMA12_REPLAY_RESULT.md) |
| EMA12 result: the mechanical 12 EMA session-open rule has no edge on MT5 broker gold or Nasdaq (0 of 32), 2026 | NO EDGE | [result](ema12/EMA12_RESULT.md) / [prereg](ema12/PREREG_EMA12.md) |
| MANUALRULE result: the trader's described 12 EMA + FVG setup, mechanical version, 0 of 12 on MT5 broker gold a | NO EDGE | [result](ema12/MANUALRULE_RESULT.md) / [prereg](ema12/PREREG_MANUALRULE.md) |

## Breakouts and opening ranges (83)

| Test | Verdict | Files |
|---|---|---|
| BEST3M_CYCLE_RESULT - an MT5 broker evaluation trading every symbol's best recent breakout at once (2026-10-15 | FAIL | [result](BEST3M_CYCLE_RESULT.md) / [prereg](PREREG_BEST3M_CYCLE.md) |
| BRK result (2026-10-14 ~22:55): classic breakouts on 46 MT5 broker - NO EDGE (two weak leads) | NO EDGE | [result](BREAKOUTS_RESULT.md) / [prereg](PREREG_BREAKOUTS.md) |
| BRK100C result - another 100 ideas (CME microstructure, MT5 broker liquidity-weighted prices, minute lead-lag, | LEAD | [result](BRK100C_RESULT.md) / [prereg](PREREG_BRK100C.md) |
| BRK100 result - 100 more untested breakout tests on 46 MT5 broker: 0 pass | PASS | [result](BRK100_RESULT.md) / [prereg](PREREG_BRK100.md) |
| BRK26 result - 26 more new breakout concepts (named indicators and price-action patterns): 0 pass | PASS | [result](BRK26_RESULT.md) / [prereg](PREREG_BRK26.md) |
| BRK2 result - Asian-range breakout and relative box tick-volume filter: 0 of 4 pass | PASS | [result](BRK2_RESULT.md) / [prereg](PREREG_BRK2.md) |
| BRK50B result - 50 more breakout ideas on gold and Nasdaq: 0 pass | PASS | [result](BRK50B_RESULT.md) / [prereg](PREREG_BRK50B.md) |
| BRK50 result - 54 new breakout ideas, 0 pass; one lead worth an out-of-time check (I20, fading the day after a | PASS | [result](BRK50_RESULT.md) / [prereg](PREREG_BRK50.md) |
| BRK-ANATOMY (breakout day round 9, 2026-10-15 11:58, descriptive): what happens after a session breakout on MT | see file | [result](BRK_ANATOMY_RESULT.md) |
| BRK-B20 result (breakout day round 20, 2026-10-15 12:46): demanding more of the breakout changes nothing | PASS | [result](BRK_B20_RESULT.md) / [prereg](PREREG_BRK_B20.md) |
| BRK-CAL result (breakout day round 32, 2026-10-15 14:06, local clock): calendar days do not switch breakouts on | PASS | [result](BRK_CAL_RESULT.md) / [prereg](PREREG_BRK_CAL.md) |
| BRK-CLASSICS result (breakout day round 8, 2026-10-15 11:57): the named breakout strategies do not pass either | PASS | [result](BRK_CLASSICS_RESULT.md) / [prereg](PREREG_BRK_CLASSICS.md) |
| BRK_CONFIRM result - a candle close beyond the box: fewer bounces, but worse trades (0 of 4 pass) | PASS | [result](BRK_CONFIRM_RESULT.md) / [prereg](PREREG_BRK_CONFIRM.md) |
| BRK-COST result (breakout day round 10, 2026-10-15 11:59): the cost share of the box is the strongest breakout | LEAD | [result](BRK_COST_RESULT.md) / [prereg](PREREG_BRK_COST.md) |
| BRK-DONCH result (breakout day round 21, 2026-10-15 12:48): intraday Donchian (turtle) breakouts are slightly  | PASS | [result](BRK_DONCH_RESULT.md) / [prereg](PREREG_BRK_DONCH.md) |
| BRK-EXITS result (breakout day round 1, 2026-10-15 11:30): no exit makes the session breakout pay | PASS | [result](BRK_EXITS_RESULT.md) / [prereg](PREREG_BRK_EXITS.md) |
| BRK-FLAG result (breakout day round 22, 2026-10-15 12:50): bull / bear flag breakouts are WORSE than random en | PASS | [result](BRK_FLAG_RESULT.md) / [prereg](PREREG_BRK_FLAG.md) |
| BRK_FVG result - an unmitigated FVG between entry and stop helps the breakout a little, not enough (0 of 4 pas | PASS | [result](BRK_FVG_RESULT.md) / [prereg](PREREG_BRK_FVG.md) |
| BRK-HOURS result (breakout day round 25, 2026-10-15 13:41, local clock): no hour of the day makes 60-minute break | PASS | [result](BRK_HOURS_RESULT.md) / [prereg](PREREG_BRK_HOURS.md) |
| BRK-IMOM result (breakout day round 28, 2026-10-15 13:52, local clock): no intraday momentum from the opening mov | PASS | [result](BRK_IMOM_RESULT.md) / [prereg](PREREG_BRK_IMOM.md) |
| BRK-L2NY result (breakout day round 36, 2026-10-15 14:44, local clock): the London-morning range broken in New Yo | PASS | [result](BRK_L2NY_RESULT.md) / [prereg](PREREG_BRK_L2NY.md) |
| BRK-LAG result (breakout day round 31, 2026-10-15 14:05, local clock): the laggard does not catch up | PASS | [result](BRK_LAG_RESULT.md) / [prereg](PREREG_BRK_LAG.md) |
| BRK-META result (breakout day round 5, 2026-10-15 11:50): a model trained on past breakouts adds ~0.1 R by pic | PASS | [result](BRK_META_RESULT.md) / [prereg](PREREG_BRK_META.md) |
| BRK-ML2 result (breakout day round 33, 2026-10-15 14:11, local clock): a model can find the LOSING breakouts, not | PASS | [result](BRK_ML2_RESULT.md) / [prereg](PREREG_BRK_ML2.md) |
| BRK-MT5SIM (breakout day round 14, 2026-10-15 12:16): what the least-bad breakout systems would do on the MT5  | PASS | [result](BRK_MT5SIM_RESULT.md) |
| BRK-NEWSDAY result (breakout day round 15, 2026-10-15 12:17): news days and weekdays do not change breakouts | PASS | [result](BRK_NEWSDAY_RESULT.md) / [prereg](PREREG_BRK_NEWSDAY.md) |
| BRK_PATTERNS result - classic chart-pattern breakouts: 0 of 15 pass | PASS | [result](BRK_PATTERNS_RESULT.md) / [prereg](PREREG_BRK_PATTERNS.md) |
| BRK-PYRAMID result (breakout day round 29, 2026-10-15 13:55, local clock): adding to winning breakouts makes them | PASS | [result](BRK_PYRAMID_RESULT.md) / [prereg](PREREG_BRK_PYRAMID.md) |
| BRK-REGIME result (breakout day round 19, 2026-10-15 12:31): market-wide climate does not switch breakouts on | PASS | [result](BRK_REGIME_RESULT.md) / [prereg](PREREG_BRK_REGIME.md) |
| BRK-RETEST result (breakout day round 2, 2026-10-15 11:42): retests and failed breakouts are worse than the pl | FAILED | [result](BRK_RETEST_RESULT.md) / [prereg](PREREG_BRK_RETEST.md) |
| BRK-ROUND result (breakout day round 27, 2026-10-15 13:49, local clock): no round-number effect; a fill-minute bu | PASS | [result](BRK_ROUND_RESULT.md) / [prereg](PREREG_BRK_ROUND.md) |
| BRK-SAR result (breakout day round 18, 2026-10-15 12:29): stop-and-reverse is the worst breakout trade of the  | PASS | [result](BRK_SAR_RESULT.md) / [prereg](PREREG_BRK_SAR.md) |
| BRK-SQUEEZE result (breakout day round 26, 2026-10-15 13:43, local clock): squeeze breakouts are no better than r | PASS | [result](BRK_SQUEEZE_RESULT.md) / [prereg](PREREG_BRK_SQUEEZE.md) |
| BRK-SWING result (breakout day round 17, 2026-10-15 12:23): holding breakouts for days, or aligning them with  | PASS | [result](BRK_SWING_RESULT.md) / [prereg](PREREG_BRK_SWING.md) |
| BRK-TICKS result (breakout day round 13, 2026-10-15 12:43): what the ticks do in the first 30 seconds does not | PASS | [result](BRK_TICKS_RESULT.md) / [prereg](PREREG_BRK_TICKS.md) |
| BRK_TWOWAY result - 22 confluences cannot tell a break from a bounce at the box edge (0 of 4 pass) | PASS | [result](BRK_TWOWAY_RESULT.md) / [prereg](PREREG_BRK_TWOWAY.md) |
| BRK-USDIDX result (breakout day round 23, 2026-10-15 12:52): a USD-index breakout is not a better signal than  | PASS | [result](BRK_USDIDX_RESULT.md) / [prereg](PREREG_BRK_USDIDX.md) |
| BRK-VOLREG result (breakout day round 3, 2026-10-15 11:45): volume and volatility regime do not separate good  | PASS | [result](BRK_VOLREG_RESULT.md) / [prereg](PREREG_BRK_VOLREG.md) |
| BRK-WEEK result (breakout day round 4, 2026-10-15 11:47): bigger boxes cut the cost, not the noise; two small  | PASS | [result](BRK_WEEK_RESULT.md) / [prereg](PREREG_BRK_WEEK.md) |
| BRK-XS result (breakout day round 6, 2026-10-15 11:52): cross-market selection does not pick better breakouts | PASS | [result](BRK_XS_RESULT.md) / [prereg](PREREG_BRK_XS.md) |
| COST-OOS result (breakout day round 11, 2026-10-15 12:01): the cost filter avoids losses out of sample but doe | PASS | [result](COST_OOS_RESULT.md) / [prereg](PREREG_COST_OOS.md) |
| CRTF result (2026-10-14 ~22:45): Candle Range Theory traded as in reel 12 - NO EDGE | NO EDGE | [result](CRTF_RESULT.md) / [prereg](PREREG_CRTF.md) |
| CRT result (2026-10-14 ~22:30): daily Candle Range Theory on 46 MT5 broker - NO EDGE | NO EDGE | [result](CRT_RESULT.md) / [prereg](PREREG_CRT.md) |
| FX3-OPEN result (2026-10-14): regional equity-session lead into EURUSD / GBPUSD / USDJPY | LEAD | [result](FX3_OPEN_RESULT.md) / [prereg](PREREG_FX3_OPEN.md) |
| F2m: fade the NR7 breakout on the 28 FX pairs: result (2026-10-09 afternoon, local) | FAILS | [result](FX_NR7_FADE_RESULT.md) / [prereg](PREREG_FX_NR7_FADE.md) |
| F2: NR7 breakout on the 28 MT5 broker FX pairs: result (15:13 local, 2026-10-09) | FAILS | [result](FX_NR7_RESULT.md) / [prereg](PREREG_FX_NR7.md) |
| GF: opening-gap fade on SP / NSDQ / DOW (MT5 broker M1 bid/ask): result (2026-10-11) | CLOSED | [result](GAP_FADE_RESULT.md) / [prereg](PREREG_GAP_FADE.md) |
| GN10 result - the late-day reversal on big-move days does not pass development on MT5 broker; hold-out not ope | PASS | [result](GN10_RESULT.md) / [prereg](PREREG_GN10.md) |
| GN11 result - BRK-WEEK's two leads fail out of time on 2020-21 futures (0 of 2) | FAIL | [result](GN11_RESULT.md) / [prereg](PREREG_GN11.md) |
| GN12 result - post-release breakouts on scheduled US event days do not pay (0 of 4) | PASS | [result](GN12_RESULT.md) / [prereg](PREREG_GN12.md) |
| GN13 result - bond-trend-aligned breakouts: a near miss on the indices that flips sign with the stock-bond reg | PASS | [result](GN13_RESULT.md) / [prereg](PREREG_GN13.md) |
| GN1 result - gold and Nasdaq long-only breakouts in the 200-day uptrend: 0 of 5 pass (2026-10-18 10:52 local, | PASS | [result](GN1_RESULT.md) / [prereg](PREREG_GN1.md) |
| GN2 result - gold and Nasdaq breakouts the day after a pullback or a dip: 0 of 4 pass (2026-10-18 10:59 local | PASS | [result](GN2_RESULT.md) / [prereg](PREREG_GN2.md) |
| GN7 result - 5-minute opening-range breakout on high relative-volume days (CME volume): 0 of 2 pass (2026-10-1 | PASS | [result](GN7_RESULT.md) / [prereg](PREREG_GN7.md) |
| GN8 result - the VIX regime does not switch the New York breakout on or off (0 of 4) | PASS | [result](GN8_RESULT.md) / [prereg](PREREG_GN8.md) |
| GR: gold range system at H1 / daily horizons (MT5 broker M1 bid/ask): result (2026-10-11) | FAIL | [result](GOLD_RANGE_RESULT.md) / [prereg](PREREG_GOLD_RANGE.md) |
| INDEX-OOS result (breakout day round 7, 2026-10-15 11:54): today's index-breakout leads do NOT replicate on ne | PASS | [result](INDEX_OOS_RESULT.md) / [prereg](PREREG_INDEX_OOS.md) |
| LF: reversal after the London 4pm fix (7 USD majors, MT5 broker M1 bid/ask): result (2026-10-11) | CLOSED | [result](LONDON_FIX_RESULT.md) / [prereg](PREREG_LONDON_FIX.md) |
| LON_COMBO_RESULT - MT5 broker cycles of the 7 kept London rules, alone and in all 127 combinations (2026-10-15 | PASS | [result](LON_COMBO_RESULT.md) / [prereg](PREREG_LON_COMBO.md) |
| LON_PERSYM_RESULT - one London-open breakout strategy per symbol, chosen and validated separately (2026-10-15, | FAILED | [result](LON_PERSYM_RESULT.md) / [prereg](PREREG_LON_PERSYM.md) |
| LON_RISK_RESULT - risk-per-trade sweep for the 7 kept London rules and their 127 combinations (2026-10-15, PC  | PASS | [result](LON_RISK_RESULT.md) / [prereg](PREREG_LON_RISK.md) |
| MONTHEND_FX_RESULT - month-end FX rebalancing into the London 16:00 fix (2026-10-15, local clock 15:19) | CLOSED | [result](MONTHEND_FX_RESULT.md) / [prereg](PREREG_MONTHEND_FX.md) |
| ORB11_ENTRY_RESULT - every reasonable ENTRY on the trader's 30-minute London / NY ORB, plus a 2020-21 out-of-t | FAILED | [result](ORB11_ENTRY_RESULT.md) / [prereg](PREREG_ORB11_ENTRY.md) |
| ORB11_GRID_RESULT - every stop / target on the trader's 30-minute London / NY ORB (2026-10-15, local clock 16:09) | PASS | [result](ORB11_GRID_RESULT.md) / [prereg](PREREG_ORB11_GRID.md) |
| ORB11_ICTSTOP_RESULT - ICT-style stops on the trader's 30-minute London / NY ORB (2026-10-15, local clock 18:06) | LEAD | [result](ORB11_ICTSTOP_RESULT.md) / [prereg](PREREG_ORB11_ICTSTOP.md) |
| ORB11_RESULT - the trader's 30-minute London / New York opening-range breakout with a 1:1 target, all 46 MT5 b | PASS | [result](ORB11_RESULT.md) / [prereg](PREREG_ORB11.md) |
| ORBX result - London opening-range breakout + news-day / trend filters: 0 of 3 pass | PASS | [result](ORBX_RESULT.md) / [prereg](PREREG_ORBX.md) |
| Family I (2026-10-09 21:49 local): gold 30-minute opening-range breakout at the London and New York opens, 1% | FAIL | [result](ORB_GOLD_RESULT.md) / [prereg](PREREG_ORB_GOLD.md) |
| ORB-REFINE result (2026-10-15 ~10:40 local): six refinements of the card's two breakouts - none passes; one l | LEAD | [result](ORB_REFINE_RESULT.md) / [prereg](PREREG_ORB_REFINE.md) |
| ORB trend-direction breakouts in 2026 (HOLD-OUT OPENED at the trader's request, exploratory) - 2026-10-15 ~11: | PASS | [result](ORB_TREND_2026_RESULT.md) |
| PRESAMPLE2 result (breakout day round 34, 2026-10-15 14:23, local clock): the other four markets do NOT confirm;  | FAIL | [result](PRESAMPLE2_RESULT.md) / [prereg](PREREG_PRESAMPLE2.md) |
| PRESAMPLE result (breakout day round 24, run 2026-10-15 14:14, written 14:16, local clock): the USDJPY London bre | FAILS | [result](PRESAMPLE_RESULT.md) / [prereg](PREREG_PRESAMPLE.md) |
| R16_CONF result - no confluence improves reel 16's NY-box breakout (0 of 8 kept) | PASS | [result](R16_CONF_RESULT.md) / [prereg](PREREG_R16_CONF.md) |
| TRB-ADAPT (2026-10-15 ~11:35 local): can a trader who keeps adapting catch each year's best breakout? No. | see file | [result](TRB_ADAPT_RESULT.md) |
| TRB-BEST (2026-10-15 ~11:20 local): the best breakout the grid finds in 2022-24, and what it did in 2025 and  | FAILED | [result](TRB_BEST_RESULT.md) |
| TRB-LUCK result (breakout day round 30, 2026-10-15 13:59, local clock): "a different best breakout every year" is | see file | [result](TRB_LUCK_RESULT.md) / [prereg](PREREG_TRB_LUCK.md) |
| TRB result (2026-10-14 ~23:10): reel 13's breakout method, run walk-forward - NO EDGE; the selection picks noi | NO EDGE | [result](TRB_RESULT.md) / [prereg](PREREG_TRB.md) |
| UJ_CONF result - USDJPY London breakout: no confluence clears the bar, two repeat in 2025 (0 of 9 kept) | PASS | [result](UJ_CONF_RESULT.md) / [prereg](PREREG_UJ_CONF.md) |
| The USDJPY London breakout on the MT5 broker account from today, alone and next to the gold EA pair (2026-10-1 | PASS | [result](USDJPY_MT5SIM_RESULT.md) |
| USDJPY London breakout: sensitivity map (2026-10-15 14:20, local clock; diagnostic, not a test) | see file | [result](USDJPY_SENS_RESULT.md) |
| USDJPY London breakout on MT5 broker REAL TICKS (2026-10-15 14:29, local clock; diagnostic): the last year is abo | PASS | [result](USDJPY_TICKS_RESULT.md) |
| VOLREGIME_RESULT - volatility-regime filter on opening-range breakouts and fades (2026-10-16, local clock ~10:05  | NO EDGE | [result](VOLREGIME_RESULT.md) / [prereg](PREREG_VOLREGIME.md) |
| WEEKEND_GAP_RESULT - fading the weekend reopen gap (2026-10-15, local clock 15:41) | CLOSED | [result](WEEKEND_GAP_RESULT.md) / [prereg](PREREG_WEEKEND_GAP.md) |

## Machine learning and agents (5)

| Test | Verdict | Files |
|---|---|---|
| ANALOG result (2026-10-14 ~21:50): chart pattern memory over all 46 MT5 broker - NO EDGE | NO EDGE | [result](ANALOG_RESULT.md) / [prereg](PREREG_ANALOG.md) |
| K: confluence panel -- 29 MT5 broker, daily bars 2020-2026, a hand-built confluence count vs two models that l | PASSED | [result](CONFLUENCE_PANEL_RESULT.md) / [prereg](PREREG_CONFLUENCE_PANEL.md) |
| EURUSD-ML result (2026-10-14): walk-forward ridge and gradient boosting over 35 features | see file | [result](EURUSD_ML_RESULT.md) / [prereg](PREREG_EURUSD_ML.md) |
| ICT2 result (2026-10-14 ~22:20): SMT divergence, ICT 2022 model, NWOG on MT5 broker - NO EDGE | NO EDGE | [result](ICT2_RESULT.md) / [prereg](PREREG_ICT2.md) |
| Market demo screen (stage 1 = real ticks 2025Q4 + 2026; stage 2 = modelled 2022-2025) | FAIL | [result](MARKET_DEMO_RESULT.md) |

## News, calendar and macro (8)

| Test | Verdict | Files |
|---|---|---|
| Clean guard simulation at TICK level on MT5 broker's real gold ticks (last 12 months): result (2026-10-09 16:3 | CLOSED | [result](CLEAN_GUARD_TICK_RESULT.md) |
| Dynamic sizing from the live state, 2026-10-14 (the trader: "we have to pass the account this month"; chose "m | PASS | [result](DP_OCT14_RESULT.md) |
| EURUSD-LAB2 result (2026-10-14): calendar timing, cross-pair relative, tick-volume surge, pivots (36 cells) | CLOSED | [result](EURUSD_LAB2_RESULT.md) / [prereg](PREREG_EURUSD_LAB2.md) |
| F: strategy factory for the 70%-this-month goal: result (2026-10-10, local local clock) | CLOSED | [result](FACTORY_RESULT.md) / [prereg](PREREG_FACTORY.md) |
| M: slow fundamental bias + mechanical 15-minute pullback entries on 28 FX pairs (M1) and SP / NSDQ / DOW (M2): | FAIL | [result](MACRO_TA_RESULT.md) / [prereg](PREREG_MACRO_TA.md) |
| US releases on MT5 broker real ticks: how far prices jump in 10 seconds (2026-10-15 14:39, local clock; descripti | see file | [result](NEWS_GAPS_RESULT.md) |
| Family SE result: three documented index anomalies (2026-10-12) | FAIL | [result](SEASONAL_EVENT_RESULT.md) / [prereg](PREREG_SEASONAL_EVENT.md) |
| M: turn of the month on MT5 broker index CFDs (SP, NSDQ, DOW, DAX): result (2026-10-10, local local clock) | FAIL | [result](TURN_OF_MONTH_RESULT.md) / [prereg](PREREG_TURN_OF_MONTH.md) |

## Crypto and weekends (11)

| Test | Verdict | Files |
|---|---|---|
| Four classic technical-analysis rules on 1-minute BTCUSD (MT5 broker bars): result (2026-10-09 15:43 local, 2 | FAIL | [result](BTC_M1_TA_RESULT.md) / [prereg](PREREG_BTC_M1_TA.md) |
| Four classic technical-analysis rules on 5-minute BTCUSD (MT5 broker bars): result (2026-10-09 15:47 local, 2 | FAIL | [result](BTC_M5_TA_RESULT.md) / [prereg](PREREG_BTC_M5_TA.md) |
| Item A (the trader 2026-10-09 "(original wording omitted)"): live pass probability with a confidence interval, weekend policy,  | PASS | [result](CLEAN_A_RESULT.md) |
| CD: dip reversal in MT5 broker's crypto CFDs: result (2026-10-11) | CLOSED | [result](CRYPTO_DIP_RESULT.md) / [prereg](PREREG_CRYPTO_DIP.md) |
| CM1 result: the Bollinger + RSI(2) 4 h rule inverted (short) on crypto (2026-10-12) | BEAT | [result](CRYPTO_MIRROR_RESULT.md) / [prereg](PREREG_CRYPTO_MIRROR.md) |
| Daily trend following on MT5 broker's crypto CFDs: result (2026-10-09 ~09:30 local) | FAILS | [result](CRYPTO_TREND_RESULT.md) / [prereg](PREREG_CRYPTO_TREND.md) |
| W: crypto on weekends (BTC + ETH on MT5 broker): result (2026-10-10, local local clock) | FAIL | [result](CRYPTO_WEEKEND_RESULT.md) / [prereg](PREREG_CRYPTO_WEEKEND.md) |
| CX: weekly cross-sectional crypto momentum / reversal (8 MT5 broker coins): result (2026-10-11) | CLOSED | [result](CRYPTO_XS_RESULT.md) / [prereg](PREREG_CRYPTO_XS.md) |
| ICT result: liquidity sweeps, fair value gaps and killzones on 46 MT5 broker symbols (2026-10-12) | LEAD | [result](ICT_SCAN_RESULT.md) / [prereg](PREREG_ICT_SCAN.md) |
| Improvement round (2026-10-12): all legs together, performance throttle | PASS | [result](IMPROVE_ROUND_RESULT.md) |
| R2X result: the daily RSI(2) dip rule on DAX/NIKKEI/ASX and on BTC/ETH (2026-10-12) | PASS | [result](R2X_RESULT.md) / [prereg](PREREG_R2X.md) |

## Mean reversion and fades (11)

| Test | Verdict | Files |
|---|---|---|
| CA result: the trader's Bollinger + RSI(2) 4-hour rule on every MT5 broker symbol (2026-10-12) | FAIL | [result](CORE4_ALL_RESULT.md) / [prereg](PREREG_CORE4_ALL.md) |
| CB1 result: the trader's Core 4 + Bollinger 4-hour RSI(2) variant on MT5 broker data (2026-10-12) | FAILS | [result](CORE4_BB_RESULT.md) / [prereg](PREREG_CORE4_BB.md) |
| DA: confirmed index dip-reversal as an add-on to the gold pair on MT5 broker: result (2026-10-11) | PASS | [result](DIP_ADDON_RESULT.md) / [prereg](PREREG_DIP_ADDON.md) |
| FO result: the trader's Fibonacci 79% + order-block idea on MT5 broker Nasdaq, causal version (2026-10-12) | FAIL | [result](FIB_OB_RESULT.md) / [prereg](PREREG_FIB_OB.md) |
| GN9 result - no late-day continuation on big-move days; on US indices the last half hour REVERSES the day (0 o | PASS | [result](GN9_RESULT.md) / [prereg](PREREG_GN9.md) |
| I20_CONF result - no confluence improves the post-expansion-day fade consistently (0 of 7 kept) | CLOSED | [result](I20_CONF_RESULT.md) / [prereg](PREREG_I20_CONF.md) |
| Family ID result: the RSI(2) dip rule at H1 and H4 on six indices (2026-10-12) | FAIL | [result](INTRADAY_DIP_RESULT.md) / [prereg](PREREG_INTRADAY_DIP.md) |
| E1: the LeoTrades morning US500 pullback setup, mechanical version, on SP / NSDQ / DOW (MT5 broker M1 bars): r | FAILS | [result](LEO_EMA_PULLBACK_RESULT.md) / [prereg](PREREG_LEO_EMA_PULLBACK.md) |
| RSI(2) leg result: does a third leg (US RSI(2) dips) move P(pass)? (2026-10-12) | PASS | [result](RSI2_LEG_RESULT.md) / [prereg](PREREG_RSI2_LEG.md) |
| UJ_C3C5_OOT result - both USDJPY confluences fail on the 2026 hold-out, and reverse (not confirmed) | FAIL | [result](UJ_C3C5_OOT_RESULT.md) / [prereg](PREREG_UJ_C3C5_OOT.md) |
| SWEEP36 result: a sweep reversal with the trader's confirmation on all 46 MT5 broker (run 20 Oct 2026 16:23-16 | NO EDGE | [result](ema12/SWEEP36_RESULT.md) / [prereg](ema12/PREREG_SWEEP36.md) |

## Trend and momentum (14)

| Test | Verdict | Files |
|---|---|---|
| T1: vol-scaled daily trend basket (28 FX + gold + NSDQ/SP/DOW) on MT5 broker prices: result (2026-10-09 16:06  | FAILS | [result](DAILY_TREND_BASKET_RESULT.md) / [prereg](PREREG_DAILY_TREND_BASKET.md) |
| FX3-TRENDBRACKET result (2026-10-14): the practice rule over all EURUSD days 2022-25 | FAILS | [result](FX3_TRENDBRACKET_RESULT.md) / [prereg](PREREG_FX3_TRENDBRACKET.md) |
| ICT3_RESULT - the remaining ICT concepts as complete strategies on every MT5 broker symbol (2026-10-15, PC clo | CLOSED | [result](ICT3_RESULT.md) / [prereg](PREREG_ICT3.md) |
| NA: noise-area intraday momentum on SP / NSDQ / DOW (MT5 broker M1 bid/ask): result (2026-10-11) | PASSED | [result](NOISE_AREA_RESULT.md) / [prereg](PREREG_NOISE_AREA.md) |
| Z: "Trade with Pat" supply/demand zones (youtube WnzC8qnfhUA) on 35 MT5 broker: result (2026-10-10, local PC  | FAILS | [result](SD_ZONES_RESULT.md) / [prereg](PREREG_SD_ZONES.md) |
| SC result: systematic setup scan over 46 MT5 broker symbols (2026-10-12) | CLOSED | [result](SETUP_SCAN_RESULT.md) / [prereg](PREREG_SETUP_SCAN.md) |
| N3: one-look 2026 confirmation of trend-filtered index nights: result (2026-10-10, local local clock) | PASS | [result](TREND_NIGHTS_CONFIRM_RESULT.md) / [prereg](PREREG_TREND_NIGHTS_CONFIRM.md) |
| TREND-PORT result (2026-10-14): multi-asset trend portfolio on the MT5 broker universe, 2021-2025 | PASS | [result](TREND_PORT_RESULT.md) / [prereg](PREREG_TREND_PORT.md) |
| Trend-pullback rule H1 on five MT5 broker: result (2026-10-09 ~10:55 local, local clock) | FAILS | [result](TREND_PULLBACK_RESULT.md) / [prereg](PREREG_TREND_PULLBACK.md) |
| XS_MOM_IDX_RESULT - cross-country index momentum, market-neutral (2026-10-15, local clock 15:43) | CLOSED | [result](XS_MOM_IDX_RESULT.md) / [prereg](PREREG_XS_MOM_IDX.md) |
| EMA1000 with a pullback limit order (run 20 Oct 2026 14:38-15:10, main PC, local clock) | CLOSED | [result](ema12/EMA1000_PULLBACK_RESULT.md) / [prereg](ema12/PREREG_EMA1000_PULLBACK.md) |
| EMA1000 result: 1,000 variations of the 12 EMA rule on all 46 MT5 broker (run 20 Oct 2026 10:11-10:15, main PC,  | NO EDGE | [result](ema12/EMA1000_RESULT.md) / [prereg](ema12/PREREG_EMA1000.md) |
| JAN2026 result: the two mechanical 12 EMA rules look in January 2026 like they did in 2022-25 (no edge), 2026- | NO EDGE | [result](ema12/JAN2026_RESULT.md) / [prereg](ema12/PREREG_JAN2026.md) |
| TRAP12 result: the trader's 22 Oct "failed break at the 12 EMA" setup as a mechanical rule (run 22 Oct 2026 15 | FAILED | [result](ema12/TRAP12_RESULT.md) / [prereg](ema12/PREREG_TRAP12.md) |

## Execution, costs and data checks (3)

| Test | Verdict | Files |
|---|---|---|
| Family AL result: five hypotheses on data we never used (2026-10-12) | FAIL | [result](ALT_DATA_RESULT.md) / [prereg](PREREG_ALT_DATA.md) |
| EURUSD-OF result (2026-10-14): order-flow proxies from real ticks, 15-60 minute horizons | CLOSED | [result](EURUSD_OF_RESULT.md) / [prereg](PREREG_EURUSD_OF.md) |
| Tick audit (2026-10-14 ~23:25): the M1 backtester agrees with MT5 broker real ticks | see file | [result](TICK_AUDIT_RESULT.md) |

## Other tests (57)

| Test | Verdict | Files |
|---|---|---|
| Can a strategy in hand be added to the live gold pair as a second leg for the 30 Oct deadline? (2026-10-14; th | PASS | [result](ADDON_LEG_RESULT.md) |
| When do the +2,000 days happen? (2026-10-13, big_day_anatomy.py) | see file | [result](BIG_DAY_ANATOMY_RESULT.md) |
| The daily card on the MT5 broker account from today: pass vs breach by risk per trade (2026-10-15 13:37, PC cl | PASS | [result](CARD_SIZING_RESULT.md) |
| Clean guard simulation: which levers really raise P(pass by 30 November) (local clock about 12:05, 2026-10-09) | PASS | [result](CLEAN_GUARD_RESULT.md) |
| X: combine every tested strategy with a fixed selection rule and per-strategy risk limits: result (2026-10-10, | PASS | [result](COMBINE_ALL_RESULT.md) / [prereg](PREREG_COMBINE_ALL.md) |
| K2 / K2b / K3: hourly confluence panel (42 MT5 broker, real bid/ask) and sparse hour x market seasonality: res | CLOSED | [result](CONFLUENCE_H1_RESULT.md) / [prereg](PREREG_CONFLUENCE_H1.md) |
| P: CFTC COT positioning on 13 MT5 broker: result (2026-10-10, local local clock) | FAIL | [result](COT_RESULT.md) / [prereg](PREREG_COT.md) |
| Daily profit lock: flatten and stop for the day once the day's P&L touches the cap (2026-10-13) | CLOSED | [result](DAILY_LOCK_RESULT.md) |
| Mandatory daily loss stop and daily profit stop, ranked by time to pass (2026-10-13, day_stops_grid.py) | PASS | [result](DAY_STOPS_RESULT.md) |
| Dynamic sizing for the October deadline (2026-10-10 00:50 local; the trader: "the chance is still too low, keep studying" | PASS | [result](DP_SIZING_RESULT.md) |
| XS: non-gold screen of the 1,220 CodeBase EAs: result (2026-10-11) | CLOSED | [result](EA_SCREEN_NONGOLD_RESULT.md) / [prereg](PREREG_EA_SCREEN_NONGOLD.md) |
| Family H (2026-10-09 21:42 local): the search for a second edge "far greater than the current one" - three st | FAILS | [result](EDGE_H_RESULT.md) / [prereg](PREREG_EDGE_H.md) |
| OE: WTI around the EIA inventory report (MT5 broker M1 bid/ask): result (2026-10-11) | CLOSED | [result](EIA_OIL_RESULT.md) / [prereg](PREREG_EIA_OIL.md) |
| EURUSD-EA1 result (2026-10-14): 24-cell search over six price-state archetypes, EURUSD only | CLOSED | [result](EURUSD_EA1_RESULT.md) / [prereg](PREREG_EURUSD_EA1.md) |
| Fastest-pass configuration after MT5 broker's reply (2026-10-11; planning simulation) | PASS | [result](FASTEST_CONFIG2_RESULT.md) |
| Fastest-pass configuration for the live MT5 broker account (2026-10-11; planning simulation, not an edge trial | PASS | [result](FASTEST_CONFIG_RESULT.md) |
| FM result: the Fibonacci 79% + order-block idea inverted (short), 2026 (2026-10-12) | FAIL | [result](FIB_OB_MIRROR_RESULT.md) / [prereg](PREREG_FIB_OB_MIRROR.md) |
| FX3-FIT2026 (2026-10-14, the trader: "be extremely profitable on 2026 on those 3 pairs") | see file | [result](FX3_FIT2026_RESULT.md) |
| FX3-JPY22 result (2026-10-14): the USDJPY 22:00 server-hour lead does not confirm | LEAD | [result](FX3_JPY22_RESULT.md) / [prereg](PREREG_FX3_JPY22.md) |
| RB: currencies weaken in their own working hours (MT5 broker M1 bid/ask): result (2026-10-11) | CLOSED | [result](FX_HOURS_RESULT.md) / [prereg](PREREG_FX_HOURS.md) |
| FXS result: intraday session scan over the 28 MT5 broker FX pairs (2026-10-12) | see file | [result](FX_SESSIONS_RESULT.md) / [prereg](PREREG_FX_SESSIONS.md) |
| GN4 result - market-profile value-area rules on Nasdaq and gold: 0 of 4 pass (2026-10-18 11:09 local, PC cloc | PASS | [result](GN4_RESULT.md) / [prereg](PREREG_GN4.md) |
| Item B (the trader 2026-10-09 "(original wording omitted)"): three gold-only trials, all fail (ledger 54 -> 57) | FAIL | [result](GOLD_B_RESULT.md) / [prereg](PREREG_GOLD_B.md) |
| Gold "convex" second leg (H1 Donchian, tight ATR stop, chandelier trail): result (2026-10-09 ~10:14 local) | FAILED | [result](GOLD_DONCHIAN_RESULT.md) / [prereg](PREREG_GOLD_DONCHIAN.md) |
| GOLD-FIX result (2026-10-14 ~20:20): trading around the LBMA gold auctions on MT5 broker gold, 2022-2025 | CLOSED | [result](GOLD_FIX_RESULT.md) / [prereg](PREREG_GOLD_FIX.md) |
| GT: USDJPY into / after the Tokyo fix (MT5 broker M1 bid/ask): result (2026-10-11) | CLOSED | [result](GOTOBI_RESULT.md) / [prereg](PREREG_GOTOBI.md) |
| What each lever is worth for "pass by 30 November" (37 business days), 2022-26 starts (local clock about 11:55, 2 | PASS | [result](GUARD_VALUE_RESULT.md) |
| HWR result - high win rate and small daily wins are achievable; a profit that passes MT5 broker is not (0 of 3 | PASS | [result](HWR_RESULT.md) / [prereg](PREREG_HWR.md) |
| ICT_GRID_RESULT - every combination of the core ICT concepts on every MT5 broker symbol (2026-10-15, local clock  | see file | [result](ICT_GRID_RESULT.md) / [prereg](PREREG_ICT_GRID.md) |
| One-trade-a-day rules on MT5 broker's US index CFDs: result (2026-10-09 ~09:04 local) | PASSED | [result](INDEX_DAILY_RESULT.md) / [prereg](PREREG_INDEX_DAILY.md) |
| I1: first-30-minute move predicts the last 30 minutes on NSDQ / SP / DOW (MT5 broker M1 bars): result (2026-10 | FAILS | [result](INDEX_INTRADAY_MOM_RESULT.md) / [prereg](PREREG_INDEX_INTRADAY_MOM.md) |
| JJ Simon "6 PM / 8 PM session" setup automated on MT5 broker's Nasdaq CFD: result (2026-10-09 ~01:15 local) | FAILS | [result](JJSIM_NQ_RESULT.md) |
| Family S (2026-10-09 23:54 local): our own GoldenShot-style micro-scalp - three trials, all fail (ledger 72 - | FAIL | [result](MICRO_SCALP_RESULT.md) / [prereg](PREREG_MICRO_SCALP.md) |
| Families TS, PI, LL result (2026-10-12) | FAIL | [result](MORE_EAS_RESULT.md) / [prereg](PREREG_MORE_EAS.md) |
| MPROFILE result (2026-10-14 ~22:10): market-profile plays on 46 MT5 broker - NO EDGE | NO EDGE | [result](MPROFILE_RESULT.md) / [prereg](PREREG_MPROFILE.md) |
| Families IM and GS result (2026-10-12) | FAIL | [result](NEW_EAS_RESULT.md) / [prereg](PREREG_NEW_EAS.md) |
| No-hedge rule (2026-10-10 01:34 local; the trader: "(original wording omitted)" / "(original wording omitted)") | CLOSED | [result](NOHEDGE_RESULT.md) |
| NOV30 result: chance of passing by 30 Nov 2026 from the live state (2026-10-18 23:5x local clock, main PC) | PASS | [result](NOV30_RESULT.md) / [prereg](PREREG_NOV30.md) |
| NQ3 result: the three Nasdaq strategies of the Matio video on MT5 broker NSDQ (2026-10-12) | FAIL | [result](NQ3_RESULT.md) / [prereg](PREREG_NQ3.md) |
| The switched-off gold EA pair, re-simulated from today's account state (2026-10-15 14:03, local clock) | PASS | [result](PAIR_FROM_TODAY_RESULT.md) |
| Regime overlay on the pair's size: result (2026-10-09 ~10:35 local) | CLOSED | [result](PAIR_OVERLAY_RESULT.md) / [prereg](PREREG_PAIR_OVERLAY.md) |
| Can P(pass the MT5 broker test) reach 70%, and by when? (2026-10-10, local local clock) | PASS | [result](PASS70_RESULT.md) |
| PASS_CEILING_OCT_RESULT - the most any strategy can reach by 30 Oct 2026 (2026-10-15, local clock 20:00) | PASS | [result](PASS_CEILING_OCT_RESULT.md) |
| REELS_16_17 result - the reels' patterns partly replicate, the edges do not (0 of 4 pass) | PASS | [result](REELS_16_17_RESULT.md) / [prereg](PREREG_REELS_16_17.md) |
| RS1 result: gold 200-day-average risk switch for the pair (2026-10-12) | PASS | [result](RISK_SWITCH_RESULT.md) / [prereg](PREREG_RISK_SWITCH.md) |
| Frozen SDB on silver (XAGUSD+): result (2026-10-09 ~10:15 local; CORRECTED ~10:19) | FAIL | [result](SDB_SILVER_RESULT.md) / [prereg](PREREG_SDB_SILVER.md) |
| X1: SDB entries with a 1.9% trailing exit instead of the fixed 1.9% target, MT5 broker gold: result (2026-10-0 | FAILS | [result](SDB_TRAIL_EXIT_RESULT.md) / [prereg](PREREG_SDB_TRAIL_EXIT.md) |
| SR result (2026-10-14): objective swing-level support/resistance trading, 46 symbols x H1/H2/H4 | see file | [result](SR_RESULT.md) / [prereg](PREREG_SR.md) |
| G: Griff's "stacked value areas" (youtube D9rx8-cXmSs) on 28 FX pairs + 6 indices: result (2026-10-10, local  | FAIL | [result](STACKED_VA_RESULT.md) / [prereg](PREREG_STACKED_VA.md) |
| G-T: best target for the stacked-value-area entries: result (2026-10-10, local local clock) | see file | [result](STACKED_VA_TARGETS_RESULT.md) / [prereg](PREREG_STACKED_VA_TARGETS.md) |
| R: intraday pairs stat-arb on six linked MT5 broker pairs: result (2026-10-10, local local clock) | FAIL | [result](STATARB_INTRADAY_RESULT.md) / [prereg](PREREG_STATARB_INTRADAY.md) |
| UT Bot portfolio on 2026 with 500 USD risk per trade (2026-10-14, EXPLORATORY; the trader asked "combine all s | PASSED | [result](UTBOT_PORT2026_RESULT.md) |
| UTBOT result (2026-10-14): UT Bot Alerts on 46 MT5 broker symbols x 8 intraday timeframes | NO EDGE | [result](UTBOT_RESULT.md) / [prereg](PREREG_UTBOT.md) |
| UTBOT-VARIANTS result (2026-10-14): Key Value 2, Key Value 3, Heikin Ashi on, 46 symbols x 8 timeframes | NO EDGE | [result](UTBOT_VARIANTS_RESULT.md) / [prereg](PREREG_UTBOT_VARIANTS.md) |
| VALIDATED_BOOK_RESULT - account plans built only from legs that survived an out-of-time test (2026-10-15, PC c | PASS | [result](VALIDATED_BOOK_RESULT.md) / [prereg](PREREG_VALIDATED_BOOK.md) |
| Family VR result: implied-vol regime vs the gold pair's daily P&L (2026-10-12) | see file | [result](VOL_REGIME_RESULT.md) / [prereg](PREREG_VOL_REGIME.md) |
| DISP24 result: a displacement candle in the first 15 minutes on all 46 MT5 broker (run 20 Oct 2026 20:04, towe | see file | [result](ema12/DISP24_RESULT.md) / [prereg](ema12/PREREG_DISP24.md) |
