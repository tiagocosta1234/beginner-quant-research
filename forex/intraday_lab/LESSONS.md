# Intraday lab: lessons, flaws and winning patterns (the trader /goal 2026-10-06: 1 / 5 / 15 minute bars, self-developed, learn from mistakes)

Engine: `lab.py` (MT5 broker M1 bid/ask bars 2021-09..2026-10, 11 symbols, real spread, USD 6/lot commission on FX and gold, entry next bar open, stop-first). Pre-registered rules and results per iteration: `PREREG.md`. Raw results: `D:\finance\scratch\lab\`.
Phases: DEV 2021-10..2023-12, VAL 2024, HOLDOUT 2025-01..2026-10 (looked at only for candidates).

## Iterations
| # | Test | k | Result |
|---|---|---|---|
| 1 | End-to-end strategies (opening-range, Bollinger fade, Donchian, RSI2) x 1 / 5 / 15 min x 11 symbols | 132 | 0 candidates; net R equals minus the cost in R (1m -0.23 vs 0.24, 5m -0.13 vs 0.13, 15m -0.07 vs 0.07): gross edge about zero |
| 2 | Edge scanner: gross forward return of simple features (returns, range position, hour) at 3 / 12 / 48 bars | 175 | 2 hits, both gross +0.03..+0.04 ATR vs cost 0.31..0.34 ATR (a real micro-reversal, 8x too small) |
| 3 | Index / gold dip-buy with an unconditional-long control | 24 | 0 hits: index "dip-buy" = drift; gold net-positive cells equal gold's own long drift (excess t 0.2..1.6) |
| 4 | Direction-neutral cross-sectional momentum / reversal in FX6 and IDX4 | 72 | 0 hits: reversal gross +0.03..+0.08 ATR (val t up to 5.3 in FX6 5m k4 h4) vs cost 0.44..0.83 ATR (two legs) |

## Flaws and mistakes found (so we do not repeat them)
1. Searching end-to-end strategies first wastes tests: measure GROSS predictive content first, then compare with cost in ATR units.
2. Cost in R scales with 1 / (timeframe): 1 minute costs 0.24 R a trade, 15 minutes 0.07 R. One minute is not a viable trading timeframe with market orders.
3. Long-biased tests on trending assets are confounded by drift: always compare with the unconditional long over the same horizon (lesson 4 / iteration 3).
4. Two-legged (long-short) designs double the cost: a clean direction-neutral test still has to beat 2 x (spread + commission).
5. Indices carry no commission and the lowest cost per ATR (US30 0.12, US100 0.14), FX the highest (0.33-0.47 at 5 minutes): cost per ATR decides where an edge can live.

## Winning patterns (what is real)
- A micro mean-reversion after an extreme 1-bar move exists at 5 minutes on 10-11 of 11 symbols and is stable DEV to VAL (gross +0.04 ATR, t 5-6) but is far below any market-order cost; only passive execution could harvest it (not testable on bar data, simulated fills would flatter it).
- Gold intraday mean-reversion is the one structure that survives costs: the pair's trades (XAU5min, Stochastic Daily Breakout) earn about 85-88% of their profit beyond what holding gold with the same side and duration would earn (drift explains 12% / 15% of the 2022-26 profit; 2026 drift is about zero and the EAs still earned most of their money). Still one symbol, and the EA versions were tuned on this history.

## Next iterations (to pre-register before running)
- Gold-specific own EA: transparent mean-reversion on 5 / 15-minute bars with holding periods of hours, long AND short, tested against the always-long and coin-flip controls, then multi-symbol checks on XAGUSD-like instruments if data is added.
- Longer holds on 15-minute bars (8-24 hours) where cost per ATR is small, direction-neutral first.
- Conditioning on volatility regime and session as pre-registered filters (not tuned thresholds).

## Iteration 5 (gold, long and short fades, 4 / 8 / 24-hour holds, same-sign control; k = 18): 0 hits
Gold dip-buys keep the same sign in DEV, VAL and HOLD with a +0.3..+0.6 ATR excess over drift (t 1.5-1.6 in DEV): suggestive, not proven. Spike fades (short) show nothing. The other 10 symbols show no consistent effect (best pooled t 1.6). Lesson 6: the pair's short-side profits come from a mechanism these simple fades do not reproduce; reproducing the pair's logic from scratch is the next test.
Total hypotheses tested in the lab so far: 132 + 175 + 24 + 72 + 18 = 421.

## Iteration 6 (rebuild the pair's structure: 4-8 hour trend + short pullback entry, symmetric, 5-minute bars; k = 12): 0 hits
The EA entry profile (DEV trades only) shows with-trend pullback entries on both sides. Rebuilt as a rule it earns nothing in 2021-23, a little in 2024, and +2 ATR per 24-hour hold in 2025-26 on gold, but the trend-only control does as well: the gold trend regime, not the pullback, carries it. No consistent effect on the other 10 symbols (multi-symbol test failed).
Lesson 8: treat the pair as a gold-trend-regime strategy. Its multi-symbol credentials are weak; plan for the choppy-gold case (-2% / -7% years at 1.5x).
Hypotheses tested in the lab so far: 421 + 12 (gold) + 120 (10 symbols) = 553 cells.

## Iteration 7 (regime filter for the pair, k = 3): 0 hits
Trendiness measures (efficiency ratio, 60-day trend, variance ratio) do not separate the pair's flat 2022-23 from 2024-26 (ON minus OFF t between -2.4 and +2.0, wrong sign in some phases). The trades earned about 0 in 2022-23 whatever the regime.
Exploratory finding (iteration 8 to pre-register): gold's daily range grew 5x (USD 25 -> 126) and price 2.3x; the pair's dollar profit per trade at fixed lots follows it (XAU5min mean move -0.5, 2.8, 6.2, 10.6, 11.7 points for 2022-26) while the edge in ATR units stays small (0.0..0.35). Lessons 9-10: trend filters do not rescue the pair; judge it in ATR units and size by volatility; the 2026 dollar returns (+11% a month at 1.5x) are inflated by volatility and must not be extrapolated.
Hypotheses tested in the lab so far: 553 + 3 regime tests + 12 (a/b units) = 568 cells.

## Iteration 8 (volatility-targeted sizing of the pair, same total risk): decision rule fired
Sharpe 1.91 -> 1.01, MT5 broker 2-Step ladder pass 72% -> 52% (2022-23 starts 43% -> 4%), P(USD 500K live by 2027-12-31) 45% -> 10% (live 0.5x), P(net < 0) 40% -> 75%. Odds in `MILESTONES_500K.md` are the optimistic bound; the realistic range is about 10-45%. Lesson 11: judge at constant risk before quoting dollar returns. Code: `iter8_volscale.py`.

## Iterations 9-10 (own EA TP5: trend + pullback entries; ATR stop / target, then signal exits; k = 24 + 16): 0 hits
Gold: about 0 R with ATR stop / target (PF 0.8..1.02), negative with signal exits (-0.15..-0.31 ATR); the other 10 symbols are strongly negative (pooled VAL t down to -6 and -20). Lessons 12-13: the pair's entries are not its edge and simple exits destroy it; costs decide every short-hold design.
Hypotheses tested in the lab so far: 608 cells over 10 iterations. No transparent rule family earns after costs on 1 / 5 / 15-minute bars on any of 11 symbols; the pair's risk-adjusted Sharpe is about 1.0 (iteration 8).
Scripts: iter8_volscale.py, iter9_tp5.py, iter10_signal_exit.py.
## What I would try next (to pre-register)
1. Direction-neutral edges with LOW trade counts (a few trades a day) where cost per ATR is small: scheduled-event drift and the London / New York open on indices (cost 0.12-0.14 ATR) using holds of several hours.
2. Cross-instrument relative value inside the same session (US100 vs US500 vs US30 spread mean-reversion) with a hold of hours.
3. Look inside the pair: the two EAs are mean-reversion multi-system on gold; a basket of simple systems on gold with equal risk weights and signal exits, tested for portfolio Sharpe (diversification), not for single-rule edge.

## Iterations 11-12 (index cash-open drive; index pair relative value; k = 36 + 36): 0 hits
Iteration 11: at 2-6 hour holds the index cost is only 0.003-0.005 of the daily range, yet the open drive has no information (momentum cells 22% positive, fade 56%, all |net| < 0.02 ATR, t < 1.5). Iteration 12: US100 / US500 / US30 ratio fades earn gross +0.005..+0.037 vs cost 0.024..0.027 (net ~0 on DEV, negative in 2024 when the ratio trends).
Lessons 14-15. Go / no-go: no second edge from simple intraday rules by January (see PREREG.md). Hypotheses tested: about 680 cells over 12 iterations. Scripts: iter11_sessions.py, iter12_relval.py.

## Iteration 13 (reaction to the 8:30 ET US data-release slot, all weekdays; k = 36): 0 hits
No momentum or fade edge after real spreads (net -0.008..+0.008 daily ATR, t <= 0.7). Lesson 16: a time slot alone carries no information; an event calendar with surprise sizes would be needed (not available offline). Scripts: iter13_release.py. Hypotheses tested: about 716 cells over 13 iterations.

## Iterations 14-15: the best strategy as OUR OWN code (Stochastic Daily Breakout, verified Python port `sdb.py`)
Parity with the tester: 195 vs 197 trades, 191 of 197 entries matched, median entry price difference USD 0.02. Iteration 14: the rule with ATR-scaled stop / target has no multi-symbol edge (pooled non-gold mean R +0.03 DEV, +0.08 VAL, -0.03 HOLD, 0 hits) but is positive on gold in DEV, VAL and HOLD at every k (+0.07..+0.31 R); the original in R units: 2022 +0.21, 2023 -0.12, 2024 +0.26, 2025 +0.27, 2026 +0.46 (long +0.30, short +0.11). Iteration 15: all 81 parameter neighbours are positive overall (median +0.15 R), the author's set ranks first (+0.22 R): a plateau with a tuned peak, expect about 30% less than the headline.
Lessons 17-18. Scripts: sdb.py, iter14_sdb.py, iter15_sdb_sensitivity.py. Total tested in the lab: about 740 cells over 15 iterations.
Next (to pre-register): own improvements to SDB with a clean protocol (risk-based sizing, a session / day-of-week filter, a trailing exit) judged on the 81-neighbour plateau, not on the single best set; the same port treatment for any other open-source EA that survives the multi-symbol screen.

## Iteration 16 (cross-sectional FX momentum / reversal, 6 USD pairs, 1-24 h lookbacks, 1-12 h holds; k = 24): 0 hits
Mean gross Sharpe 0.00 on DEV; net negative in nearly every cell (hourly rebalancing loses 3-17 Sharpe points to costs). Lesson 19: pair diversification multiplies an existing per-pair edge by about sqrt(N / (1 + (N-1) rho)); it does not create one. Total tested: about 764 cells over 16 iterations. Script: iter16_fx_xsection.py.

## Iteration 18 (one-off exception to "no daily": FX trend, 6 USD pairs, 10-120 day lookbacks, time-series and cross-sectional; k = 11): 0 hits
Net Sharpe about 0 on DEV, negative on VAL and HOLD in most cells (best DEV 0.58, negative on VAL). Lesson 20: no multi-pair FX Sharpe on this data at any horizon tested (5 minutes to 4 months). Carry untested (no rate data). Total tested: about 775 cells over 17 test iterations. Script: iter18_fx_daily.py.

## Iterations 17-27 (2026-10-07, the "all forex pairs" push): no multi-pair FX Sharpe; one lead found and closed
17 hour-of-day USD drift 0/66; 18 daily FX trend 0/11 (approved one-off exception); 19 gold regime filter 0/3; 20 SDB filters 0/10; 21 synthetic-cross fade 0/12 with one near-miss; 22 plateau of that cell (hit: DEV 100% / VAL 85% of 27 cells positive); 23 with swap: ensemble Sharpe 0.44 DEV / 0.15 VAL, 2-Step pass 8-13% (swap = 4.4 bp a trade); 24 swap-aware selection meets the hit rule (DEV 1.0-1.45, VAL 0.8-0.9) but 2026 is -1.1 / -1.9; 25 same rule on 7 indices: no plateau; 26 controls: carry and placebo pass, leave-one-currency-out fails (4 of 6, needed 5): lead dropped; 27 weekly-extreme fade on gold: no plateau.
Lessons 21-27: (21) no hour-of-day flow at spreads; (22) a volatility regime does not rescue the pair; (23) the only stable SDB pattern is the long bias = gold's uptrend; (24) multi-day FX holds pay about 1.4 bp a night for two legs at this broker (swap is negative on both sides), so a 7-11 bp gross reversion nets little; (25) the cross effect is FX-specific, not general relative value; (26) plateau + placebo are necessary, not sufficient: check concentration (one or two currencies) and decay by year; (27) a premium that decays every year (18 -> 2 bp) is a regime, not a strategy; (28) printing out-of-sample columns before the hit test burns the window: print them only when the pre-registered gate passes (my iteration 21 error).
Total tested in the lab: about 880 cells over 27 iterations. Scripts: iter16..iter27 in forex/intraday_lab/.
28 lead-lag 0/180: gross at most 0.54 of cost (lesson 29).

## Iteration 29 (swing families on 12 FX pairs: Donchian 20 / 55, trend pullback, 2-sigma fade; k = 4): 0 hits, negative gross
Mean R net -0.08..-0.12 on DEV, worse on VAL for the two fade rules; gross is also negative, so no direction to flip. Lesson 30: textbook swing rules carry no edge on FX majors and crosses in 2021-26; manual setups built on them would lose about 0.1 R a trade. Data gap: 16 of 28 pairs still need the tick pull (second PC). Script: iter29_fx_swing.py.

LESSON 31 (iteration 30, 2026-10-07): on all 28 FX pairs none of the four swing families (Donchian 20 / 55, trend pullback, 2-sigma fade) nor the frozen SDB rule has a net edge (0 hits of 5). SDB pooled +0.017 R DEV, +0.125 R VAL, -0.12 R in 2025 and -0.135 R in 2026: it makes 34 trades a month on FX, so frequency is not its problem, the missing edge is. The gold result of SDB does not transfer to FX; a multi-pair FX Sharpe is still not available from any rule written so far.

LESSON 32 (iteration 31, 2026-10-07): SDB survives cost stress (spread x3 still +0.195 R) but not a feed change: on independent Databento GC futures it is +0.130 R (t 1.90) over 2021-10..2026-09, -0.160 R (t -1.63) over the never-used 2019-06..2021-09, and +0.036 R (t 0.63) over all 7 years. The edge is regime-specific (2022, 2024-26). Do not describe it as a structural gold edge; treat MT5 broker pass odds as conditional on the current regime, and test on the actual firm feed before paying.

LESSON 33 (iteration 32, 2026-10-07): need-based (bold) sizing does not raise the 60-day MT5 broker pass probability of SDB; the binding limits are 3.4 trades a month and the 2% daily profit cap (at least 4 profitable days for 8%). Best fixed: 2.0% risk, 1.0% day stop: 5.1% within 60 days (MT5 broker feed), 1.2% on GC. Only more independent trades with an edge can raise it.

LESSON 34 (iteration 33, 2026-10-07): six frozen textbook intraday families on MT5 broker gold (London / NY opening-range breakouts, previous-day breakout, squeeze, pullback, failed-break fade; 15-minute bars) have no edge: 0 of 6 pass; the frequent ones (26-45 trades a month) lose 0.05-0.2 R a trade after costs, the two range breakouts sit near zero. A second gold edge of these kinds does not exist in this data.

LESSON 35 (iteration 34, 2026-10-07): the frozen SDB rule loses on seven other commodities (pooled DEV -0.205 R, VAL -0.129 R, 0 of 5 years positive). It earns only on gold, and only in some years.

LESSON 36 (iteration 35, 2026-10-07): SDB works only on H1 (M30 / H2 / H4 about zero or negative) and the EA was published on 2026-10-01 after an automated search of more than 2 million candidates on 2021-2026 XAUUSD history (author statement on the MQL5 CodeBase page). Treat it as a likely curve-fit: the 2021-2026 results are the author's in-sample window. Only trades after 2026-10-01 are out-of-sample; keep the forward log (forex/forward_test) running and do not pay on backtest evidence alone.

LESSON 37 (iteration 36, 2026-10-07 night): the frozen SDB rule on the four MT5 broker-relevant index CFDs (US100, US500, US30, GER40; pre-registered bar t >= 2.5 net of MT5 broker swap and positive in >= 3 of 5 years, k = 4) has 0 hits: net-of-swap mean R -0.016 (t -0.26), -0.111 (t -1.53), +0.036 (t +0.47), -0.026 (t -0.37). With MT5 broker's gold swap included, SDB on gold itself is +0.159 R net (t +2.30 over 201 trades, 4 of 5 years positive): below the k-adjusted bar even in the sample it was searched on, and the swap costs it 27% of its gross edge (0.219 R). SDB is therefore a gold-only, regime-specific rule; there is no other MT5 broker instrument to diversify it with. Swap-free account is the way to run it (forex/forward_test/firm_sim_swap.py).

LESSON 38 (2026-10-08, forward_test/PREREG_PASS60.md): a pre-registered 108-variant search over SDB's stop / target distance, order expiry, risk size and day stop, chosen on 2021-23 and checked on 2024-26, found NO setting with a 60-day MT5 broker Pro pass probability of 25% on both halves (0 of 108). Frozen: 0% DEV / 14% VAL; best DEV-selected variant (0.8% stop / target): 8.8% / 17.1% with 24% breach + halt on VAL. More trades (6.3 a month) halves the edge per trade. The 60-day pass depends on the gold regime, not on tuning; "expected to pass in 60 days" needs a higher-Sharpe strategy, not an optimisation of this one.

LESSON 39 (2026-10-08, forward_test/when_it_loses.py, pre-registered bar k = 27, t <= -3.1 and negative in both halves): WHEN does frozen SDB lose? Not on a weekday, hour or month: 0 reliably bad buckets and 0 of 27 negative in both DEV (2021-23) and VAL (2024-26). Weakest weekdays are Monday (net R -0.008, but -0.55 DEV and +0.43 VAL) and Wednesday (+0.012); best are Tuesday (+0.33) and Friday (+0.30), none significant. The losses are a REGIME: DEV net R -0.041 (80 trades) vs VAL +0.290 (121); 2023 -0.171 (44% wins), 2021 -0.17, 2024 +0.17, 2025 +0.24, 2026 +0.45; deepest drawdown -9.5 R from 2023-01-13 to 2023-12-01 (11 months), longest losing streak 4. The one structural pattern: HOLD LENGTH. Trades held longer than 4 days (97 of 201) average +0.008 R net of swap (win 56%), trades closed within 4 days +0.30 R (win 66%): long holds pay swap and add no edge. It is known only at the exit, so it is a hypothesis for a pre-registered time-stop test, not a filter.

LESSON 40 (2026-10-08, inversion queue, forex/ea_batch/inv_confirm.py result CONFIRMED ['16081' Exp_CandlesticksBW EURUSD, '15888' Exp_JFatl_Digit_System GBPUSD]): both confirmations are an ARTIFACT, not an inverted edge. In all six year-runs (3 years x 2 EAs) 99-100% of the positions close on ONE day (e.g. 2023-09-05, 2024-08-19, 2025-04-10 for 16081; 2023-06-14, 2024-07-12, 2025-05-21 for 15888) and that day carries 100% of the P&L; the EAs open one 0.10-lot position after another and never exit (up to 387 positions = 38.7 lots open at once on a USD 100K account) until the tester's stop-out liquidates the account, which is the "-85K a year". Lots are constant 0.10 (no martingale); hold times median 50-125 days. The mirrored P&L is the mirror of a margin stop-out; the t-statistics of 25-27 come from treating hundreds of simultaneous, identical-exit positions as independent trades (one bet per year). The scoring rule "30 positions, inverted net > 0, no single position > 50% of the profit" cannot see this. FIX TO ADD: reject a candidate if more than 50% of positions or of the P&L close on the same day, or the run ends before the last day of the period (account exhausted). Consequence: the same stop-out artifact probably explains most of the "-80K a year" EAs in the batch; 0 of 9 inversion candidates are valid; the inversion idea is closed unless a candidate survives the same-day test.

LESSON 41 (2026-10-08, forex/ea_batch/inv_realize.py, pre-registered k = 32, bar: net > 0 in each of 2023 / 2024 / 2025, pooled t >= 3.1, no day with > 50% of the profit, <= 20 positions open): mirroring every ORIGINAL entry (opposite direction, 0.10 lot, MT5 broker M1 bid / ask) with a REALISED exit (take profit TP pips / stop SL pips, 60-day time stop) after the stop-out artifact of LESSON 40. Exp_JFatl_Digit_System (15888, GBPUSD): 6 of 16 cells HIT (10/160, 20/80, 20/160, 40/80, 40/160, 80/40), a plateau: every TP >= 20 with SL >= 80 is positive in all three years (e.g. 40/160: +3,710 / +6,459 / +3,780 USD a year at 0.10 lot, 618 trades, win 92%, worst day -1,085, max closed drawdown -1,406, 17 positions open at most; 20/80: +1,690 / +1,159 / +840, t 4.4). Exp_CandlesticksBW (16081, EURUSD): 0 of 16 hit (2023 negative for most cells; only the widest stops are positive in all years but 33 open positions and 46% of the profit on one day). So the EA entries carry a REAL short-horizon fade signal on GBPUSD in 2023-25, at least in this sample. CAVEATS: the t-statistics (4 - 11) are inflated because the 618 positions overlap in clusters; only about 5-8 months a year (until the original's stop-out) have entries; 2026 was the selection window; 2022 is untested (needs a year-run of the original EA on the main PC); floating (open-position) drawdown is not in the table; high win rate with a small take profit and a large stop is a tail-risk shape. NEXT: run 15888 for 2022 (hold-out) and 2021, then a floating-equity MT5 broker replay at scaled lots (about 0.2 - 0.3 lot). Not a strategy yet.
