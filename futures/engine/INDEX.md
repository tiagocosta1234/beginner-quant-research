# Futures research engine index

Each round is one idea: a script (its docstring states the question and, usually, the answer) and its outputs.
Most rounds are descriptive or pre-registered tests on CME 1-minute data with fees and slippage; the great
majority did not hold up out of sample. Rounds about account-rule simulation were removed from this public copy,
so the numbering has gaps.

## Volume profile, POC and value area (11)

| Round | Question / finding | Files |
|---|---|---|
| 178 | Round 178: a genuinely new idea class -- Volume Profile / Point of Control (POC) reversion, from Auction Market Theory (Steidlmayer, CBOT, 1 | [round178_volume_profile_poc.py](round178_volume_profile_poc.py) + round178_results.json |
| 183 | Round 183: robustness pass on Round 178's NQ Volume Profile / POC lead, per CURRENT_STATE.md's own note ("worth a robustness pass... before  | [round183_poc_robustness.py](round183_poc_robustness.py) + round183_results.json |
| 184 | Round 184: a genuinely distinct extension of the Market Profile framework that produced this ledger's strongest surviving lead (Round 178/18 | [round184_value_area_breakout.py](round184_value_area_breakout.py) + round184_results.json |
| 185 | Round 185: robustness pass on Round 184's NQ Value Area rejection lead (OOS P=0.972, the second-closest miss in this ledger). Same disciplin | [round185_value_area_robustness.py](round185_value_area_robustness.py) + round185_results.json |
| 186 | Round 186: does combining NQ's two Market Profile leads (POC reversion, Round 178/183; Value Area rejection, Round 184/185) produce somethin | [round186_nq_marketprofile_combo.py](round186_nq_marketprofile_combo.py) + round186_results.json |
| 187 | Round 187: after Round 186's combined Market Profile leads still didn't pass the pass-speed gate at any sizing tried (best <=15-day pass rat | [round187_daily_gap_fade.py](round187_daily_gap_fade.py) + round187_results.json |
| 193 | Round 193: asked directly to stop optimizing/combining the existing NQ Market Profile family and go find a genuinely NEW trading idea -- the | [round193_daily_gap_continuation.py](round193_daily_gap_continuation.py) + round193_results.json |
| 198 | Round 198: "we need a strategy that fits our plan" -- resumed the idea-hunt with a genuinely new construction, checked against IDEA_LEDGER.m | [round198_meta_labeling_poc.py](round198_meta_labeling_poc.py) + round198_results.json |
| 199 | Round 199: extends Round 198's meta-labeling construction to the Value Area REJECTION leg (Round 184, continuation=False -- the variant Roun | [round199_meta_labeling_va.py](round199_meta_labeling_va.py) + round199_results.json |
| 245 | Round 245 (2026-09-30): the "mega ML" meta-labeling filter on the POC leg. the trader: "start building the mega ML on the POC leg". Design f | [round245_poc_mega_ml.py](round245_poc_mega_ml.py) + round245_results.json |
| 246 | Round 246 (2026-09-30): Profile Rotation -- the frequent, high-win-rate version of the repo's one evidenced effect, designed from the broker | [round246_profile_rotation.py](round246_profile_rotation.py) + round246_results.json |

## Fair-value gaps, OTE and ICT ideas (35)

| Round | Question / finding | Files |
|---|---|---|
| 11 | Round 11: Bias-aligned unmitigated-FVG reaction trading.  | [round11_fvg_bias.py](round11_fvg_bias.py) + round11_mgc_results.txt, round11_mnq_results.txt |
| 12 | Round 12: Confirmation-candle FVG reaction (vs. Round 11's first-touch baseline) + breakeven management overlay. Nasdaq (MNQ) only, per the  | [round12_fvg_confirmation.py](round12_fvg_confirmation.py) + round12_mnq_results.txt |
| 13 | Round 13: refinements to Round 12's confirmation-candle FVG entry. MNQ (Nasdaq) only, per the trader's "keep pushing on it" instruction foll | [round13_fvg_refinements.py](round13_fvg_refinements.py) + round13_mnq_results_phase12.txt, round13_mnq_results_phase3.txt |
| 31b | Round 31b: extend Round 31's combined MNQ+MGC sweep to higher risk levels.  | [round31b_risk_sweep.py](round31b_risk_sweep.py) |
| 31c | Round 31c: out-of-sample check on Round 31's MNQ+MGC combined sweep.  | [round31c_recent_regime_oos.py](round31c_recent_regime_oos.py) |
| 34 | Round 34: finer sizing sweep around Round 31b's coarse peak (multiplier steps of 0.5-1.0x), now using Round 32's CORRECTED "first target cro | [round34_fine_sizing_sweep.py](round34_fine_sizing_sweep.py) |
| 38 | Round 38: with the phantom-fill bug fixed (2026-09-20) and the combined MNQ+MGC portfolio sizing sweep now showing no viable point (round34  | [round38_post_fix_viability_sweep.py](round38_post_fix_viability_sweep.py) |
| 39 | Round 39: re-examining Rounds 20-29's MNQ-only, tested-but-not-deployed entries (FVG-confirmation + weekly-bias, and the simple 1H-EMA-slope | [round39_reexamined_variant.py](round39_reexamined_variant.py) + round39_mgc_sweep.csv, round39_mnq_sweep.csv |
| 46 | Round 46: higher-timeframe (4H/Daily) FVG confluence as a GATE on top of the one already-confirmed real edge (Round 39's tod_last_third-filt | [round46_htf_fvg_gate.py](round46_htf_fvg_gate.py) |
| 52 | Round 52: "busted FVG" -- trades the FAILURE of a Fair Value Gap, not the gap itself. Prior FVG work in this repo (Rounds 11-13, 20) traded  | [round52_busted_fvg.py](round52_busted_fvg.py) |
| 56 | Round 56: VWAP-Z run alone (not combined with the TOD filter, not MGC) -- sweep risk/trade to find where P(success) against the real 2026-10 | [round56_vwapz_alone_70pct_search.py](round56_vwapz_alone_70pct_search.py) + round56_fixed_risk_tier_results.csv, round56_variable_sizing_results.csv |
| 89 | Round 89: the trader asked directly for the MES/MYM/M2K/MGC/SIL numbers to be made "trustworthy/real" after Round 88 flagged them as thin-sa | [round89_ote_multi_symbol_significance.py](round89_ote_multi_symbol_significance.py) |
| 125 | Round 125: ICT "Judas swing" at the New York open, mechanical version.  | [round125_judas_swing.py](round125_judas_swing.py) |
| 125b | Round 125b: does putting the stop beyond the "protected" high/low help?  | [round125b_protected_level_stops.py](round125b_protected_level_stops.py) |
| 127 | Round 127: ICT standard-deviation projections as reversal levels ("top/bottom tick").  | [round127_stdv_projection_fade.py](round127_stdv_projection_fade.py) + round127_results.json |
| 128 | Round 128: ICT high- vs low-resistance liquidity (HRL vs LRL) as a direction call.  | [round128_hrl_vs_lrl.py](round128_hrl_vs_lrl.py) + round128_results.json |
| 129 | Round 129: ICT 4-hour "Power of 3" (accumulation-manipulation-distribution inside one 4H candle), with an optional "near all-time highs -> l | [round129_4h_po3.py](round129_4h_po3.py) + round129_results.json |
| 134 | Round 134, batch C: smarter targets, independent confirmation. Pre-registered 2026-09-26 -- rules, variants and verdict rules committed befo | [round134_batch_c.py](round134_batch_c.py) + round134_results.json |
| 135 | Round 135, batch D: 25 years of daily futures, inside Broker's trading day. Pre-registered 2026-09-26 -- rules, variants and verdict rules c | [round135_batch_d.py](round135_batch_d.py) + round135_results.json |
| 136 | Round 136, batch E: currencies by trading hours, and scheduled-event days. Pre-registered 2026-09-26 -- rules, variants and verdict rules co | [round136_batch_e.py](round136_batch_e.py) + round136_results.json |
| 150 | Round 150, batch P: fair value gaps (FVG), plain and with the popular "secrets", 1:1 target, held to the pass-speed gate. Pre-registered 202 | [round150_batch_p.py](round150_batch_p.py) + round150_results.json |
| 159 | Round 159: the trader asked to try all ICT strategies. Checked what's already in the ledger first (k=200) so this doesn't re-test what's don | [round159_ict_order_blocks_silver_bullet.py](round159_ict_order_blocks_silver_bullet.py) + round159_results.json |
| 160 | Round 160: invert every ICT strategy in the ledger that hasn't already been inverted. the trader: "try to invert all of them." Checked first | [round160_invert_remaining_ict.py](round160_invert_remaining_ict.py) + round160_results.json |
| 161 | Round 161: the trader asked, after the P=0.73 explanation for ledger row 217 (Round 160's "INVERTED MNQ 4H Po3 10:00-14:00, both directions" | [round161_po3_2026_all_symbols.py](round161_po3_2026_all_symbols.py) |
| 162 | Round 162: "keep testing new idea classes." Checked IDEA_LEDGER.md first (k=218) -- ZN=F (10-Year Treasury note futures) has never appeared  | [round162_rates_lead_equity.py](round162_rates_lead_equity.py) + round162_results.json |
| 166 | Round 166: the trader asked to build an original strategy, not another borrowed named concept (ICT, a YouTube scalper, a published anomaly). | [round166_dip_family_ensemble.py](round166_dip_family_ensemble.py) + round166_results.json |
| 189 | Round 189: /watch'd Revelio Trading's "How to identify the best Fair Value Gaps (backed by data)" (YouTube qkzJknH5IJk) for real this time - | [round189_fvg_real_secrets.py](round189_fvg_real_secrets.py) + round189_results.json |
| 290 | Round 290 (2026-10-01, PRE-REGISTERED): an ALWAYS-IN-THE-MARKET 1-minute ICT-confluence algorithm on MT5 broker index CFDs (the trader: "wha | [round290_ict_confluence_always_in_market.py](round290_ict_confluence_always_in_market.py) + round290_results.json |
| 294 | Round 294 (2026-10-02, PRE-REGISTERED): the trader's "BrokerAPI: FVG + VWAP Killzone Sentinel" Pine indicator -- as written, and with every  | [round294_fvg_vwap_killzone_sentinel.py](round294_fvg_vwap_killzone_sentinel.py) + round294_placebo.json, round294_posthoc.json, round294_results.json |
| 294 | Round 294, POST-HOC CHECKS (2026-10-02; written AFTER the pre-registered run, descriptive only, no ledger row, no new verdict). Why: in samp | [round294_posthoc_checks.py](round294_posthoc_checks.py) + round294_placebo.json, round294_posthoc.json, round294_results.json |
| 303 | Round 303 (2026-10-02, PRE-REGISTERED): a MASSIVE MULTI-ASSET TECHNICAL-ANALYSIS SWEEP on MT5 broker's 44 non-crypto instruments (the trader | [round303_multi_asset_ta_sweep.py](round303_multi_asset_ta_sweep.py) + round303_results.json |
| 308 | Round 308 (2026-10-02, PRE-REGISTERED): the trader asked for "a 1 minute ICT monstrous strategy that achieves a high win rate on the long te | [round308_ict_monster_1m.py](round308_ict_monster_1m.py) + round308_results.json |
| 309 | Round 309 (2026-10-02, PRE-REGISTERED): the trader: "make a 1 minute strategy that achieves a high win rate on the long term" (the ICT stack | [round309_1min_high_winrate_mean_reversion.py](round309_1min_high_winrate_mean_reversion.py) + round309_results.json |
| 318 | Round 318 (2026-10-03, PRE-REGISTERED): does the first 30 minutes' return predict the last 30 minutes' return (Gao, Han, Li, Zhou intraday m | [round318_first30_last30_intraday_momentum.py](round318_first30_last30_intraday_momentum.py) + round318_results.json |
| 320 | Round 320 (2026-10-03, PRE-REGISTERED): walk-forward ridge on cross-asset DAILY features predicting the next-day ES close-to-close return.  | [round320_cross_asset_ridge_es.py](round320_cross_asset_ridge_es.py) + round320_results.json |

## Opening range and breakouts (20)

| Round | Question / finding | Files |
|---|---|---|
| 39 | Round 39: Overnight-gap / opening-drive CONTINUATION -- a price-gap-triggered entry, genuinely different from every entry family tried in Ro | [round39_gap_open_drive.py](round39_gap_open_drive.py) + round39_mgc_sweep.csv, round39_mnq_sweep.csv |
| 48 | Round 48: Initial Balance (IB) fade -- genuinely different mechanic from everything tried so far. ORB (opening-range BREAKOUT, trading WITH  | [round48_ib_fade.py](round48_ib_fade.py) |
| 70 | Round 70: a genuinely different entry idea, not a repackaged inversion of VWAP-Z. User asked for a strategy that (a) trades relatively frequ | [round70_breakout_momentum.py](round70_breakout_momentum.py) |
| 72 | Round 72: combine TOD + VWAP-Z + Round 71's two-stage breakout into ONE portfolio with a single SHARED daily cap (not three independent $3,0 | [round72_combined_three_way.py](round72_combined_three_way.py) + round72_daily_pnl.csv |
| 145 | Round 145, batch L: a currency month-end flow, a classic daily breakout, a close-location bounce, and a lunar-cycle anomaly. Pre-registered  | [round145_batch_l.py](round145_batch_l.py) + round145_results.json |
| 148 | Round 148, batch N: intraday breakouts through levels, held to the pass-speed gate. Pre-registered 2026-09-26, committed before any result i | [round148_batch_n.py](round148_batch_n.py) + round148_results.json |
| 152 | Round 152: the inverse of Round 151's Q3 -- FADE the first break of the 08:30 news range. Pre-registered 2026-09-26, committed before this v | [round152_news_fade.py](round152_news_fade.py) + round152_results.json |
| 167 | Round 167: "build a strategy from scratch." Round 166 showed combining already-found small effects has a hard, computed ceiling (inverse-var | [round167_volume_confirmed_orb.py](round167_volume_confirmed_orb.py) + round167_results.json |
| 168 | Round 168: "continue until you find the strategy needed." Round 167 found that volume confirmation on an opening-range breakout has a genuin | [round168_volume_confirmed_levels.py](round168_volume_confirmed_levels.py) + round168_results.json |
| 169 | Round 169: two follow-ups to Round 167's genuine (if sub-bar) finding, after Round 168 showed the volume-confirmation effect does NOT genera | [round169_orb_volume_extended.py](round169_orb_volume_extended.py) + round169_results.json |
| 171 | Round 171: the trader exported real 1-minute data from Databento for ES, NQ, GC and SI (full-size futures, continuous front-month), 2019-06/ | [round171_databento_orb_replication.py](round171_databento_orb_replication.py) + round171_results.json |
| 172 | Round 172: the trader asked to invert the two cells from Round 171's Databento replication that came up looking positive at a glance (NQ no- | [round172_orb_databento_inverted.py](round172_orb_databento_inverted.py) + round172_results.json |
| 173 | Round 173: the trader asked what could raise Sharpe (smooth the equity curve), and agreed to test the most direct lever -- the payoff SHAPE, | [round173_orb_sharpe_optimized_exit.py](round173_orb_sharpe_optimized_exit.py) + round173_results.json |
| 221 | Round 221 (pre-registered, new idea class, 2026-09-30): opening-range FAILURE fade -- continuing the "new branch" search after Round 220's | [round221_orb_failure_fade.py](round221_orb_failure_fade.py) + round221_results.json |
| 306 | Round 306 (2026-10-02, PRE-REGISTERED): the two Expert Advisors in forex/expert_advisors -- "Range Breakout EA" and "Ninja Turtle Scalper EA | [round306_ea_range_breakout_and_donchian_scalper.py](round306_ea_range_breakout_and_donchian_scalper.py) + round306_results.json |
| 324 | Round 324 (2026-10-03, PRE-REGISTERED; the 24 cells are logged as ONE ledger row, k + 1): enter AFTER the opening drive -- does the move sin | [round324_post_open_drive_entry.py](round324_post_open_drive_entry.py) + round324_results.json |
| 324b | Round 324b (2026-10-03, DESCRIPTIVE control, no ledger row): is Round 324's MT5 broker follow-the-opening-drive result just being long? Run  | [round324b_always_long_control.py](round324b_always_long_control.py) |
| 333 | Round 333 (2026-10-03, PRE-REGISTERED; ONE ledger row, k + 1): day-level paired test of "follow the opening drive at 10:30" on the MT5 broke | [round333_follow_1030_paired_R.py](round333_follow_1030_paired_R.py) |
| 338 | Round 338 (2026-10-04, PRE-REGISTERED; ONE ledger row, k + 1): is the 10:30 follow-the-opening-drive effect concentrated in STRONG drives?  | [round338_opening_drive_strength.py](round338_opening_drive_strength.py) |
| 340 | Round 340 (2026-10-04, PRE-REGISTERED; ONE ledger row, k + 1): the @quantstackai "never trade the open" 5-minute breakout (Instagram DeE2Zk6 | [round340_quantstack_open_breakout.py](round340_quantstack_open_breakout.py) + round340_grid.csv |

## VWAP and mean reversion (39)

| Round | Question / finding | Files |
|---|---|---|
| 14 | Round 14, Part 2: short-horizon statistical mean-reversion / momentum on 15-min z-score extremes. Structurally different from every prior ro | [round14_meanreversion.py](round14_meanreversion.py) + round14_part2_results.txt |
| 30 | Round 30: Swing-based support/resistance BOUNCE, MGC -- proper walk-forward validation of the promising in-sample result found interactively | [round30_support_resistance.py](round30_support_resistance.py) + round30_sr_bounce_results.csv |
| 30b | Round 30b: fixes a real gap found in Round 30's S/R bounce validation -- the signal generator fired on every level touch independently (~14. | [round30b_sequential_fix.py](round30b_sequential_fix.py) + round30b_sequential_results.csv |
| 42 | Round 42: gap FADE (inverse of Round 39's gap continuation) -- Round 39 found gap-continuation is a CONFIRMED, statistically significant LOS | [round42_gap_fade.py](round42_gap_fade.py) |
| 49 | Round 49: VWAP Z-score mean reversion -- pure statistical mechanics, distinct from everything tried (this repo's prior "VWAP" work, per the  | [round49_vwap_zscore.py](round49_vwap_zscore.py) |
| 51 | Round 51: time-decay exit -- applies to BOTH tonight's confirmed real MNQ edges (Round 39 tod_last_third, Round 49 VWAP Z-score). Instead of | [round51_time_decay_exit.py](round51_time_decay_exit.py) |
| 55 | Round 55: asymmetric partial-profit + runner exit, applied to tonight's best combined MNQ signal set (tod_last_third + VWAP-Z). Genuinely di | [round55_partial_runner.py](round55_partial_runner.py) |
| 56 | Round 56: confidence-weighted position sizing for MGC's swing S/R bounce edge.  | [round56_mgc_confidence_sizing.py](round56_mgc_confidence_sizing.py) + round56_fixed_risk_tier_results.csv, round56_variable_sizing_results.csv |
| 57 | Round 57: TOD filter re-sized to $1,600/trade (8x the $200 reference) and VWAP-Z re-sized to $400/trade (2x reference), per direct request.  | [round57_tod1600_vwapz400_combined.py](round57_tod1600_vwapz400_combined.py) |
| 58 | Round 58: double the combined sizing from Round 57 (TOD $1,600 -> $3,200, VWAP-Z $400 -> $800), real backtests at the new sizes (not scaled) | [round58_combined_2x_stats.py](round58_combined_2x_stats.py) |
| 65 | Round 65: VWAP-Z trend-day cooldown filter.  | [round65_vwapz_trend_cooldown.py](round65_vwapz_trend_cooldown.py) |
| 71 | Round 71: hunting for a real (not hypothetical) strategy with a genuinely better payoff ratio -- avg win meaningfully larger than avg loss - | [round71_asymmetric_payoff.py](round71_asymmetric_payoff.py) |
| 90 | Round 90: the trader asked directly -- if Round 89's bootstrap bar is real, does the ORIGINAL TOD/VWAP-Z ("the trader") strategy, the one ac | [round90_manual_significance_check.py](round90_manual_significance_check.py) |
| 142 | Round 142, batch J: weekend gaps, a classic multi-day mean-reversion system, and index relative value. Pre-registered 2026-09-26, committed  | [round142_batch_j.py](round142_batch_j.py) + round142_results.json |
| 147 | Round 147, batch M: high win-rate intraday level fades, held to the pass-speed gate. Pre-registered 2026-09-26, committed before any result  | [round147_batch_m.py](round147_batch_m.py) + round147_results.json |
| 158 | Round 158: the inverse of Round 157 -- FADE copper's prior-day move instead of following it. Pre-registered 2026-09-27, committed before thi | [round158_copper_fade_inversion.py](round158_copper_fade_inversion.py) + round158_results.json |
| 181 | Round 181: the regular, every-trading-day overnight gap, never tested in this ledger. Checked first: Round 142's `gap_fade` only fires after | [round181_daily_gap_fade_follow.py](round181_daily_gap_fade_follow.py) + round181_results.json |
| 194 | Round 194: continuing the pivot to genuinely new idea classes after Rounds 187/193 closed both directions of the naive daily-open-gap trigge | [round194_quad_witching_reversal.py](round194_quad_witching_reversal.py) + round194_results.json |
| 197 | Round 197: continuing the idea-hunt after Round 196 closed supply/demand zones (0/4). Checked IDEA_LEDGER.md first (k=375) -- no round has t | [round197_lunch_lull_reversal.py](round197_lunch_lull_reversal.py) + round197_results.json |
| 222 | Round 222 (pre-registered, new idea class, 2026-09-30): outside-bar (engulfing-candle) reversal -- continuing the new-branch search after | [round222_outside_bar_reversal.py](round222_outside_bar_reversal.py) + round222_results.json |
| 228 | Round 228 (2026-09-30): bounded ML meta-labeling on the trader's VWAP-Z leg. Plan: futures/docs/ML_META_LABELING_PLAN.md (written the same | [round228_vwapz_meta_labeling.py](round228_vwapz_meta_labeling.py) + round228_results.json |
| 243 | Round 243 (2026-09-30), verification: does the LIVE S/R bounce bot (live_bot/support_resistance_bounce_strategy.py) trade what the backtest  | [round243_sr_live_parity.py](round243_sr_live_parity.py) + round243_results.json |
| 283 | Round 283 (2026-10-01, PRE-REGISTERED): SPREAD REVERSION between near-identical index CFDs (idea 2 of the brainstorm the trader approved). H | [round283_index_pair_spread_reversion.py](round283_index_pair_spread_reversion.py) + round283_results.json |
| 285 | Round 285 (2026-10-01, PRE-REGISTERED): MULTI-DAY DIP REVERSAL on index CFDs (idea 3 of the brainstorm the trader approved: "go ahead with i | [round285_multi_day_dip_reversal.py](round285_multi_day_dip_reversal.py) + round285_results.json |
| 286 | Round 286 (2026-10-01, PRE-REGISTERED): INDEPENDENT-DATA CONFIRMATION of Round 285's lead -- "long a 2-sigma 3-day dip, held one day". the t | [round286_dip_reversal_independent_confirmation.py](round286_dip_reversal_independent_confirmation.py) + round286_results.json |
| 291 | Round 291 (2026-10-01, PRE-REGISTERED): does the CONFIRMED dip-reversal rule work OUTSIDE equity indices -- FX, metals, energy? (the trader: | [round291_dip_reversal_fx_metals_energy.py](round291_dip_reversal_fx_metals_energy.py) + round291_results.json |
| 292 | Round 292 (2026-10-01, PRE-REGISTERED): LONGER HOLDING PERIODS for the confirmed dip-reversal lead (the trader: "try the 2-5 day holding per | [round292_dip_reversal_longer_holds.py](round292_dip_reversal_longer_holds.py) + round292_results.json |
| 310 | Round 310 (2026-10-02, PRE-REGISTERED): the trader: "try other ways to make it profitable" (after Round 309: four 1-minute mean-reversion tr | [round310_1min_fade_profitability_ways.py](round310_1min_fade_profitability_ways.py) + round310_results.json |
| 311 | Round 311 (2026-10-02, PRE-REGISTERED): the trader: "analyze the current strategy applied to the chart, invert it and try to optimize its pr | [round311_reversal_signal_detector_invert_optimize.py](round311_reversal_signal_detector_invert_optimize.py) + round311_grid.csv, round311_results.json |
| 312 | Round 312 (2026-10-02, PRE-REGISTERED): the trader: "actually put it as it was but add more pips, look at the eurusd performance, can you sp | [round312_reversal_detector_eurusd_tweaks.py](round312_reversal_detector_eurusd_tweaks.py) + round312_grid.csv, round312_results.json |
| 313 | Round 313 (2026-10-02, PRE-REGISTERED): independent confirmation of Round 312's only lead, on pairs the search never touched. Round 312 (the | [round313_reversal_detector_five_pairs_confirmation.py](round313_reversal_detector_five_pairs_confirmation.py) + round313_results.json |
| 314 | Round 314 (2026-10-02, PRE-REGISTERED): the trader: "we need much more frequent trades though" (the Reversal Signal Detector at stop 4 ATR / | [round314_reversal_detector_frequency_ladder.py](round314_reversal_detector_frequency_ladder.py) + round314_results.json |
| 316 | Round 316 (pre-registered, single hypothesis): does a VIX >= 25 filter improve the dip-reversal rule?  | [round316_dip_vix_filter.py](round316_dip_vix_filter.py) |
| 317 | Round 317 (single hypothesis, descriptive; first run happens after this file is written, no dry-run mode).  | [round317_dollar_fade.py](round317_dollar_fade.py) |
| 325 | Round 325 (2026-10-03, PRE-REGISTERED; the 12 cells are logged as ONE ledger row, k + 1): multi-hour INTRADAY dip reversal on ES and NQ -- t | [round325_intraday_dip_reversal.py](round325_intraday_dip_reversal.py) + round325_results.json |
| 327 | Round 327 (2026-10-03, PRE-REGISTERED; the 2 cells are logged as ONE ledger row, k + 1): a causal regime switch between multi-hour reversal  | [round327_regime_switch_intraday.py](round327_regime_switch_intraday.py) + round327_results.json |
| 329 | Round 329 (2026-10-03, PRE-REGISTERED, DESCRIPTIVE -- no ledger row, k stays 2031): does adding the two sparse leads (daily dip reversal, pr | [round329_table_plus_edge_overlay.py](round329_table_plus_edge_overlay.py) + round329_results.json |
| 330 | Round 330 (2026-10-03, PRE-REGISTERED; the 6 cells are logged as ONE ledger row, k + 1): intraday gold / silver ratio reversion, inside the  | [round330_intraday_gold_silver_ratio.py](round330_intraday_gold_silver_ratio.py) + round330_results.json |
| 331 | Round 331 (2026-10-03, PRE-REGISTERED, PROVISIONAL: Yahoo daily futures closes, not MT5 broker data; ONE ledger row, k + 1): daily cross-sec | [round331_index_cross_section_daily_reversal.py](round331_index_cross_section_daily_reversal.py) + round331_results.json |

## Trend, momentum and time of day (7)

| Round | Question / finding | Files |
|---|---|---|
| 15 | Round 15: pure time-of-day / day-of-week directional drift, no price-structure trigger at all. Every prior round (1-14) required SOME price  | [round15_seasonality.py](round15_seasonality.py) + round15_results.txt |
| 39 | Round 39: Does filtering MNQ's random-entry+ATR-trail edge by WHEN (volatility regime or time-of-day), rather than WHICH DIRECTION, concentr | [round39_volatility_filtered_mnq.py](round39_volatility_filtered_mnq.py) + round39_mgc_sweep.csv, round39_mnq_sweep.csv |
| 143 | Round 143: do the two surviving "buy equity weakness in an uptrend" leads hold on data they have never seen? Pre-registered 2026-09-26, comm | [round143_dip_family_1990s.py](round143_dip_family_1990s.py) + round143_results.json |
| 196 | Round 196: asked directly, after the earnings-calendar data source turned out to be a dead end (Finnhub's free tier only serves a rolling ne | [round196_supply_demand_zones.py](round196_supply_demand_zones.py) + round196_results.json |
| 226 | Round 226 (the trader, 2026-09-30): "test it in another sample" -- Round 225 already rebuilt the trader's TOD-leg logic on Databento NQ (sam | [round226_manual_confluence_more_samples.py](round226_manual_confluence_more_samples.py) + round226_results.json |
| 307 | Round 307 (2026-10-02, PRE-REGISTERED, DESCRIPTIVE -- no ledger row): a BACKTEST OF MANUAL'S JESSE STRATEGY `XAUSTBreakFree` (SuperTrend reg | [round307_xau_supertrend_donchian_backtest.py](round307_xau_supertrend_donchian_backtest.py) + round307_results.json |
| 339 | Round 339 (2026-10-04, PRE-REGISTERED; ONE ledger row, k + 1): unconditional half-hour drift of gold (XAUUSD) by time of day on MT5 broker b | [round339_gold_halfhour_drift.py](round339_gold_halfhour_drift.py) + round339_grid.csv |

## Machine learning and meta-labeling (4)

| Round | Question / finding | Files |
|---|---|---|
| 137 | Round 137, batch F: walk-forward machine learning across 9 futures markets. Pre-registered 2026-09-26 -- features, models, hyperparameters,  | [round137_batch_f.py](round137_batch_f.py) + round137_results.json |
| 149 | Round 149, batch O: a 1:1 intraday edge, searched for by walk-forward models. Pre-registered 2026-09-26, committed before any result is run. | [round149_batch_o.py](round149_batch_o.py) + round149_results.json |
| 319 | Round 319 (2026-10-03, PRE-REGISTERED): half-hour slot scan on gold (GC) and silver (SI) futures over the whole 24-hour day, causal prior-sl | [round319_metals_halfhour_slot_scan.py](round319_metals_halfhour_slot_scan.py) + round319_grid.csv, round319_results.json |
| 326 | Round 326 (2026-10-03, PRE-REGISTERED; the 4 cells are logged as ONE ledger row, k + 1): does the multi-hour CONTINUATION seen post hoc on E | [round326_continuation_metals.py](round326_continuation_metals.py) + round326_results.json |

## Sizing, risk and Monte Carlo (7)

| Round | Question / finding | Files |
|---|---|---|
| 24 | Round 24: two extensions of the ONE validated finding (Round 19-23's random-entry + ATR-trailing-stop exit on MNQ, $75 risk/trade, 1 trade/d | [round24_grid_and_session.py](round24_grid_and_session.py) + round24_sizing_search.csv |
| 26 | Round 26: does DYNAMIC, equity-scaled position sizing beat Round 25's best fixed-risk trade-off (P(success)~24.4% / P(ruin)~66.3% at $1,900/ | [round26_dynamic_sizing.py](round26_dynamic_sizing.py) + round26_dynamic_sizing_grid.csv |
| 31f | Generate sample equity paths for the updated combined-portfolio equity curve artifact, at Round 31's recommended sizing (MNQ $225 / MGC $600 | [round31f_chart_data.py](round31f_chart_data.py) + round31f_chart_data.json |
| 275 | Round 275 (2026-10-01, DESCRIPTIVE sensitivity, no edge claim, no ledger row): what does respecting MT5 broker's recommended risk per trade  | [round275_risk_cap_sensitivity.py](round275_risk_cap_sensitivity.py) + round275_results.json |
| 342 | Round 342 (2026-10-04, DESCRIPTIVE, no ledger row): check the 'optimal risk per trade' video (Monte Carlo of account tests: 40% win rate, 2: | [round342_video_risk_framework_check.py](round342_video_risk_framework_check.py) |
| 344 | Round 344 (2026-10-04, PRE-REGISTERED; ONE ledger row, k + 1): 25 risk-management schemes on the MT5 broker 1-Step $100K test.  | [round344_risk_management_25.py](round344_risk_management_25.py) |
| 344b | Round 344b (descriptive chart, no ledger row): Monte Carlo fan chart of the deployed 1-Step plan (S01 TABLE), every start day x 20 coin draw | [round344b_master_monte_carlo_chart.py](round344b_master_monte_carlo_chart.py) |

## Costs, data and verification (14)

| Round | Question / finding | Files |
|---|---|---|
| 33 | Round 33: is Round 31/32's 83-86% success figure robust, or a single-MC-seed fluke? Re-run the SAME combined portfolio (MNQ $225 / MGC $600) | [round33_seed_robustness.py](round33_seed_robustness.py) |
| 73 | Round 73: fixed-points bracket exit -- 15pt stop, move to +2pt (a small locked-in profit, not exact breakeven, to clear commission/slippage) | [round73_fixed_points_bracket.py](round73_fixed_points_bracket.py) |
| 139 | Round 139, batch H: two data types never used before -- implied volatility (VIX) and crypto futures. Pre-registered 2026-09-26 -- signals, s | [round139_batch_h.py](round139_batch_h.py) + round139_results.json |
| 140 | Round 140: does Round 139's lead -- "buy equities the day after a VIX spike" -- hold on data it has never seen? Pre-registered 2026-09-26, c | [round140_vix_spike_1990s.py](round140_vix_spike_1990s.py) + round140_results.json |
| 146 | Round 146: does Round 145's IBS lead hold on data it has never seen? Pre-registered 2026-09-26, committed before any result is run. | [round146_ibs_1990s.py](round146_ibs_1990s.py) + round146_results.json |
| 177 | Round 177: formalizing the exploratory scan's standout finding (unregistered diagnostic pass over all 4 Databento symbols, not itself a ledg | [round177_volume_spike_reaction.py](round177_volume_spike_reaction.py) + round177_results.json |
| 231 | Round 231 (2026-09-30): Round 192's disciplined bracket re-run NET of costs. PRE-REGISTRATION -- design and reporting fixed before any net n | [round231_round192_net_of_costs.py](round231_round192_net_of_costs.py) + round231_results.json |
| 232 | Round 232 (2026-09-30): re-run the eleven scripts that import Round 192's gross-of-costs `build_daily()` series, net of costs. | [round232_downstream_net_rerun.py](round232_downstream_net_rerun.py) |
| 251 | Round 251 (2026-10-01): ONE hypothesis from Round 250, tested only on data never used for it. the trader: "one last cheap check". PRE-REGIST | [round251_late_continuation_replication.py](round251_late_continuation_replication.py) + round251_results.json |
| 258 | Round 258 (2026-10-01): a new strategy search for US100 and gold only, built on two mechanisms, on MT5 broker's own tick-built bid/ask bars. | [round258_us100_gold_sessions_news.py](round258_us100_gold_sessions_news.py) + round258_results.json |
| 271 | Round 271 (2026-10-01, PRE-REGISTERED): is there a frequent 1:1 trade generator with a net-of-cost win rate above break-even on MT5 broker's | [round271_one_to_one_generator.py](round271_one_to_one_generator.py) + round271_results.json |
| 272 | Round 272 (2026-10-01, PRE-REGISTERED SENSITIVITY): Round 272's 104 cells re-priced with the costs MEASURED on the MT5 broker free trial. Th | [round272_repriced_measured_costs.py](round272_repriced_measured_costs.py) + round272_results.json |
| 297 | Round 297 (2026-10-02, PRE-REGISTERED, DESCRIPTIVE -- no edge claim, no ledger row): the DEPLOYED 1-Step pass policy (forex/specs/round275_o | [round297_deployed_policy_harsh_costs.py](round297_deployed_policy_harsh_costs.py) + round297_results.json |
| 302 | Round 302 (2026-10-02, PRE-REGISTERED): is there a HIGH-FREQUENCY (seconds-scale) strategy on MT5 broker's US100.cash that survives the real | [round302_tick_level_hft.py](round302_tick_level_hft.py) + round302_results.json |

## Crypto and other markets (12)

| Round | Question / finding | Files |
|---|---|---|
| 23 | Round 23: re-test of Round 22's "does relaxing 1-trade/day multiply the edge" question, fixing a methodological gap Round 22 flagged in its  | [round23_multi_trade_v2.py](round23_multi_trade_v2.py) + round23_mnq_grid.csv, round23_sizing_search.csv |
| 154 | Round 154: a genuinely new idea class, not a re-skin of anything in the ledger (k=195 as of this pre-registration). the trader: "keep testin | [round154_btc_weekend_gap_leads_equity.py](round154_btc_weekend_gap_leads_equity.py) + round154_results.json |
| 155 | Round 155: another genuinely new idea class -- checked against `IDEA_LEDGER.md` first (k=196). 6E=F (Euro futures, an inverse dollar proxy)  | [round155_dollar_leads_gold.py](round155_dollar_leads_gold.py) + round155_results.json |
| 163 | Round 163: a second new idea class today (after Round 162's rates/discount- rate test). Checked IDEA_LEDGER.md first (k=219) -- turn-of-mont | [round163_day_of_week_seasonality.py](round163_day_of_week_seasonality.py) + round163_results.json |
| 164 | Round 164: a sixth cross-asset lead. Checked IDEA_LEDGER.md first (k=221) -- CL=F (WTI crude oil futures) has been loaded by round135_batch_ | [round164_oil_leads_equity.py](round164_oil_leads_equity.py) + round164_results.json |
| 176 | Round 176: the Gold/Silver ratio (GSR), a genuinely new METHODOLOGY for this ledger -- relative value / pairs trading, not a directional lea | [round176_gold_silver_ratio.py](round176_gold_silver_ratio.py) + round176_results.json |
| 182 | Round 182: a seventh cross-asset lead. Checked IDEA_LEDGER.md first (k=300): crypto (154), dollar (155), copper (157/158), rates (162), and  | [round182_gold_leads_equity.py](round182_gold_leads_equity.py) + round182_results.json |
| 188 | Round 188: asked directly whether combining ALL of NQ's tested intraday leads and letting it trade would work. Checked the correlation FIRST | [round188_nq_triple_combo.py](round188_nq_triple_combo.py) + round188_results.json |
| 301 | Round 301 (2026-10-02, PRE-REGISTERED, DESCRIPTIVE -- no edge claim, no ledger row): which drawn LEVELS on the 1-minute US100 chart have a h | [round301_level_rebound_rates.py](round301_level_rebound_rates.py) + round301_results.json |
| 334 | Round 334 (2026-10-03, PRE-REGISTERED; ONE ledger row, k + 1): BTCUSD intraday patterns on MT5 broker H1 bars, trades held INSIDE one server | [round334_btc_hourly_intraday.py](round334_btc_hourly_intraday.py) + round334_grid.csv, round334_results.json |
| 335 | Round 335 (2026-10-03, PRE-REGISTERED; ONE ledger row, k + 1): the 1-minute BTCUSD signal battery on real MT5 broker bid / ask minute bars.  | [round335_btc_1min_signal_battery.py](round335_btc_1min_signal_battery.py) + round335_grid.csv, round335_results.json |
| 336 | Round 336 (2026-10-03, PRE-REGISTERED; ONE ledger row, k + 1): walk-forward gradient boosting on 24 causal 1-minute BTCUSD features, trading | [round336_btc_1min_ml_walkforward.py](round336_btc_1min_ml_walkforward.py) + round336_results.json |

## Other rounds (66)

| Round | Question / finding | Files |
|---|---|---|
| 13 | Round 13 Phase 3: 4H gap-reaction filter (Refinement 3) applied on top of the Best Combo selected from Phases 1+2 (see round13_mnq_results_p | [round13_phase3_gapfilter.py](round13_phase3_gapfilter.py) + round13_mnq_results_phase12.txt, round13_mnq_results_phase3.txt |
| 17 | Round 17: Prior-day / prior-week reference-level signals -- MNQ + MGC.  | [round17_prior_ref.py](round17_prior_ref.py) + round17_results.txt |
| 18 | Round 18: stack the least-bad components found across Rounds 12/13/17 on MNQ 15m HTF, the best-performing configuration to date (Round 17's  | [round18_stacked.py](round18_stacked.py) + round18_results.txt |
| 19 | Round 19: Random entry + managed exit -- decoupling "is the entry-timing any good" from "is the exit/management any good", a question every  | [round19_random_entry.py](round19_random_entry.py) + round19_results.txt |
| 20 | Round 20: does a REAL entry beat Round 19's random-entry baseline, holding the exit fixed at Round 19's validated ATR-trailing style? MNQ on | [round20_entry_comparison.py](round20_entry_comparison.py) + round20_results.txt |
| 21 | Round 21: does PYRAMIDING (scale-in) the exit convexity Round 19 validated change its buffer-safe expectancy, in either direction? | [round21_pyramid.py](round21_pyramid.py) + round21_results.txt |
| 22 | Round 22: does relaxing the "1 trade/day" convention multiply Round 19's validated exit-convexity edge into a usable daily pace? | [round22_multi_trade.py](round22_multi_trade.py) + round22_mnq_summary.csv, round22_results.txt, round22_sizing_search.csv |
| 27 | Round 27: grid-search MGC's OWN (stop_mult, trail_mult) for the Round 19 validated exit style, independent of the MNQ-specific parameters (1 | [round27_mgc_grid.py](round27_mgc_grid.py) + round27_mgc_grid_trades.csv, round27_sizing_search.csv |
| 31d | Round 31d: sanity-check Round 31c's suspiciously perfect 100% success result.  | [round31d_pool_diagnostic.py](round31d_pool_diagnostic.py) |
| 31e | Round 31e: does the Round 31c "100% success" hold up against the ACTUAL worst real 20-consecutive-trading-day stretch in the recent fold (no | [round31e_worst_real_window.py](round31e_worst_real_window.py) |
| 41 | Round 41: does the "one random entry per day" convention itself cap the MNQ edge below what's needed for the deadline, independent of per-tr | [round41_multi_entry_mnq.py](round41_multi_entry_mnq.py) |
| 44 | Round 44: day-of-week seasonality -- genuinely untried anywhere in this repo's ~100+ prior variants (checked docs/EDGE_VALIDATION_RESULTS.md | [round44_day_of_week.py](round44_day_of_week.py) |
| 45 | Round 45: cross-instrument lead-lag -- genuinely different mechanism class from everything else tried in this repo (checked docs/EDGE_VALIDA | [round45_cross_instrument.py](round45_cross_instrument.py) |
| 47 | Round 47: intraday 15m ATR(14) threshold gate on top of the confirmed tod_last_third MNQ edge -- "disable trading if ATR is below X" (avoid | [round47_atr_threshold_gate.py](round47_atr_threshold_gate.py) |
| 53 | Round 53: the most favorable configuration tonight's entire search produced -- all three confirmed real MNQ signals (Round 39 tod_last_third | [round53_final_combined_check.py](round53_final_combined_check.py) |
| 54 | Round 54: generate full-history trade logs (ts, pnl) for every real, confirmed edge found across tonight's session and the earlier campaign, | [round54_generate_equity_curves.py](round54_generate_equity_curves.py) |
| 69 | Round 69: a GENUINE, verified <= $2,000 max daily loss, not a soft after-the-fact breaker. | [round69_true_2000_daily_cap.py](round69_true_2000_daily_cap.py) |
| 120b | Round 120b: does the edge survive Broker's flat-by-close rule?  | [round120b_overnight_hold_check.py](round120b_overnight_hold_check.py) |
| 120c | Round 120c (descriptive): Broker's trading day runs 5:00 PM CT -> 3:10 PM CT, so a position opened after the 6:00 PM ET reopen may be held i | [round120c_legal_overnight_window.py](round120c_legal_overnight_window.py) |
| 122 | Round 122: published intraday effects, judged by round120_goal_judge with every realism rule on -- pre-registered 2026-09-26, committed befo | [round122_published_effects_search.py](round122_published_effects_search.py) |
| 122b | Round 122b: is the turn-of-month lead from Round 122 real? Check it on ~30 years of independent daily history before trusting 180 MNQ trades | [round122b_tom_long_history.py](round122b_tom_long_history.py) |
| 124 | Round 124: CodeTrading's "Trading with Python: Simple Scalping Strategy" (youtube.com/watch?v=C3bh6Y4LpGs, 2024-01-11) -- claimed 200%+ in a | [round124_codetrading_scalper.py](round124_codetrading_scalper.py) |
| 126 | Round 126, batch B: four session-structure ideas never tested with honest exits. Pre-registered 2026-09-26 -- rules, variants and the bar ar | [round126_batch_b.py](round126_batch_b.py) + round126_results.json |
| 130 | Round 130: re-check the two live_bot strategies never tested flat at the close.  | [round130_live_bot_strategies_recheck.py](round130_live_bot_strategies_recheck.py) + round130_results.json |
| 131 | Round 131: invert the losing strategies.  | [round131_inverted_losers.py](round131_inverted_losers.py) + round131_results.json |
| 132 | Round 132: try to break the one lead from Round 131 -- "STDV continuation".  | [round132_stdv_continuation.py](round132_stdv_continuation.py) + round132_results.json |
| 138 | Round 138, batch G: a sub-hour pattern scan (1-minute bars, 5-30 minute holds). Pre-registered 2026-09-26 -- the scan, selection rule, valid | [round138_subhour_scan.py](round138_subhour_scan.py) + round138_results.json |
| 141 | Round 141, batch I: flow-driven calendar effects -- Treasury supply, month-end index extension, and options expiration. Pre-registered 2026- | [round141_batch_i.py](round141_batch_i.py) + round141_results.json |
| 144 | Round 144, batch K: institutional flows, the RSI(2) mechanism beyond equity longs, calendar and volatility regimes, and cross-sectional mome | [round144_batch_k.py](round144_batch_k.py) + round144_results.json |
| 151 | Round 151, batch Q: three intraday structures not yet tested here -- same-slot persistence, the overnight session after a big day, and the 0 | [round151_batch_q.py](round151_batch_q.py) + round151_results.json |
| 153 | Round 153: stop-loss and take-profit tuning, done so it can't fool us -- choose the exit on the in-sample years only, judge that one choice  | [round153_exit_grid.py](round153_exit_grid.py) + round153_results.json |
| 156 | Round 156: a third new idea class today. Checked against `IDEA_LEDGER.md` first (k=197) -- turn-of-month (specific days around the month bou | [round156_halloween_seasonal.py](round156_halloween_seasonal.py) + round156_results.json |
| 157 | Round 157: a fourth new mechanism today. Checked against `IDEA_LEDGER.md` first (k=198) -- HG=F (copper) has never appeared in any test in t | [round157_copper_leads_equity.py](round157_copper_leads_equity.py) + round157_results.json |
| 165 | Round 165: a seventh new mechanism, and a different KIND of signal than any cross-asset lead tried so far. Checked IDEA_LEDGER.md first (k=2 | [round165_vix_term_structure.py](round165_vix_term_structure.py) + round165_results.json |
| 170 | Round 170: a third from-scratch construction. Rounds 166 (portfolio combination) and 167-169 (volume-as-a-confirmation-filter) both explored | [round170_cumulative_money_flow.py](round170_cumulative_money_flow.py) + round170_results.json |
| 174 | Round 174: the third lever from the trader's "how do we smooth this" list, after #2 (reshape the payoff, Round 173: tested properly, decayed | [round174_dip_family_confluence.py](round174_dip_family_confluence.py) + round174_results.json |
| 175 | Round 175: the last of the trader's four smoothing levers. Round 166 combined four signals from ONE family (equities, daily-close, "buy weak | [round175_cross_asset_class_ensemble.py](round175_cross_asset_class_ensemble.py) + round175_results.json |
| 179 | Round 179: the trader asked to add a filter to every "best" strategy from this session -- one trade a day, New York hours only. Checked what | [round179_rth_only_dip_family.py](round179_rth_only_dip_family.py) + round179_results.json |
| 180 | Round 180: formalizing the `/watch`ed video (2026-09-28, neurotrader, "Harmonic Pattern Recognition With Python", ODHlC9YuowY). A new idea c | [round180_harmonic_patterns.py](round180_harmonic_patterns.py) + round180_results.json |
| 192 | Round 192: Round 190's disciplined bracket (+$1,650 win / -$850 loss) was built by DISCRETIZING each day's already-fully-resolved real trade | [round192_intraday_disciplined_bracket.py](round192_intraday_disciplined_bracket.py) + round192_results.json |
| 195 | Round 195: continuing the pivot to genuinely new idea classes (Rounds 187/193 closed the daily-gap trigger; Round 194 closed quad-witching/r | [round195_es_nq_leadlag.py](round195_es_nq_leadlag.py) + round195_results.json |
| 205 | Round 205 (the trader, 2026-09-29): "calculate the sharpe ratio from the three and bunch of other numbers." The three from Round 204 ("Best  | [round205_three_strategy_stats.py](round205_three_strategy_stats.py) + round205_results.json |
| 220 | Round 220 (pre-registered, new idea class, 2026-09-30): "lets keep this strategy safe for now and lets try to look for a new branch of a str | [round220_money_flow_divergence.py](round220_money_flow_divergence.py) + round220_results.json |
| 223 | Round 223 (the trader, 2026-09-30): "lets try to improve the profit factor of manual on a new branch thorough aditional confluences, dont mo | [round223_manual_confluence_filters.py](round223_manual_confluence_filters.py) + round223_results.json |
| 224 | Round 224 (the trader, 2026-09-30): "dig into it and focus on getting trustworthy numbers" -- the rigorous follow-up to Round 223's headline | [round224_manual_confluence_robustness.py](round224_manual_confluence_robustness.py) + round224_results.json |
| 227 | Round 227 (the trader, 2026-09-30): "the target is to find the edge we're looking for the plan" -- continuing the search for a genuine new e | [round227_regime_switch_manual_disciplined.py](round227_regime_switch_manual_disciplined.py) + round227_results.json |
| 239 | Round 239 addendum (descriptive, added after the pre-registered run): the same top-10 Stage-A designs at much larger edges, to translate 'wh | [round239_edge_addendum.py](round239_edge_addendum.py) |
| 244 | Round 244 (2026-09-30): mixing confluences onto the two rule-compliant strategies with the most signal. the trader: "try to refine to mix co | [round244_confluence_mix.py](round244_confluence_mix.py) + round244_lead_by_year.json, round244_results.json |
| 257 | Round 257 (2026-10-01): a from-scratch daily-direction scan on the whole liquid MT5 broker universe, in the one window that pays no swap. th | [round257_daily_swapfree_scan.py](round257_daily_swapfree_scan.py) + round257_results.json |
| 277 | Round 277 (2026-10-01, PRE-REGISTERED): the support/resistance approach of the video "Automated Support and Resistance Detection in PYTHON"  | [round277_video_sr_pivots.py](round277_video_sr_pivots.py) + round277_results.json |
| 279 | Round 279 (2026-10-01, PRE-REGISTERED, DESCRIPTIVE -- no ledger row): our best strategies combined across many assets, Sharpe ratio and smoo | [round279_multi_asset_portfolio_vs_buy_hold.py](round279_multi_asset_portfolio_vs_buy_hold.py) + round279_results.json |
| 280 | Round 280 (2026-10-01, PRE-REGISTERED, DESCRIPTIVE -- no ledger row): a SWAP-AWARE long-short version of the Round 279 multi-asset portfolio | [round280_swap_aware_long_short.py](round280_swap_aware_long_short.py) + round280_results.json |
| 282 | Round 282 (2026-10-01, PRE-REGISTERED): SESSION-RELAY LEAD-LAG across index CFDs (idea 1 of the brainstorm the trader approved: "work on tha | [round282_session_relay_lead_lag.py](round282_session_relay_lead_lag.py) + round282_results.json |
| 284 | Round 284 (2026-10-01, PRE-REGISTERED): CROSS-SECTIONAL LONG-SHORT across MT5 broker instruments (idea 4 of the brainstorm the trader approv | [round284_cross_sectional_long_short.py](round284_cross_sectional_long_short.py) + round284_results.json |
| 298 | Round 298 (2026-10-02, PRE-REGISTERED): is there ANY day-of-week or hour-of-day filter -- a weekday, or a 30-minute slot of the day, in whic | [round298_day_of_week_and_hour_of_day_filters.py](round298_day_of_week_and_hour_of_day_filters.py) + round298_results.json |
| 299b | Round 299b (2026-10-02, POST-HOC CONTROL, DESCRIPTIVE -- written after seeing Round 299's results and committed before it is run): is Round  | [round299b_random_skip_control.py](round299b_random_skip_control.py) + round299b_results.json |
| 304 | Round 304 (2026-10-02, PRE-REGISTERED, TWO-STAGE): is there a SECOND STREAM among SINGLE INSTRUMENTS? (the trader: "yes", to 'look for a sec | [round304_single_instrument_second_stream.py](round304_single_instrument_second_stream.py) + round304_results.json, round304_stage1.json |
| 315 | Round 315 (2026-10-02, PRE-REGISTERED, DESCRIPTIVE -- no ledger row): how much does it matter that the TradingView / OANDA chart and the MT5 | [round315_feed_sensitivity.py](round315_feed_sensitivity.py) + round315_results.json |
| 321 | Round 321 (2026-10-03, PRE-REGISTERED, DESCRIPTIVE -- no ledger row, k stays 2025): does a LONG-BIASED direction beat the coin flip inside t | [round321_long_bias_bold_play.py](round321_long_bias_bold_play.py) + round321_results.json |
| 322 | Round 322 (2026-10-03, DESCRIPTIVE, no ledger row, k stays 2025): how much directional skill does the deployed 1-Step table need to pass mor | [round322_required_skill_curve.py](round322_required_skill_curve.py) + round322_results.json |
| 323 | Round 323 (2026-10-03, PRE-REGISTERED, descriptive scale: no ledger rows until a candidate exists; the 18 cells are logged as ONE ledger row | [round323_preopen_direction_battery.py](round323_preopen_direction_battery.py) |
| 328 | Round 328 (2026-10-03, PRE-REGISTERED; the 2 hypotheses are logged as ONE ledger row, k + 1): the pre-FOMC announcement drift (Lucca and Mos | [round328_pre_fomc_drift.py](round328_pre_fomc_drift.py) + round328_results.json |
| 337 | Round 337 (2026-10-03, PRE-REGISTERED; ONE ledger row, k + 1): does the pre-FOMC announcement drift (Round 328's rule, unchanged) appear on  | [round337_pre_fomc_other_markets.py](round337_pre_fomc_other_markets.py) |
| 341 | Round 341 (2026-10-04, DESCRIPTIVE, no ledger row, k stays 2042): what would an average of +4% a month take, using the best lead we have, un | [round341_four_percent_month_feasibility.py](round341_four_percent_month_feasibility.py) |
| 343 | Round 343 (2026-10-04, PRE-REGISTERED; ledger rows: the screen + one per master, k + 3 -- first written as one per cell, changed when record | [round343_master_strategy_1step.py](round343_master_strategy_1step.py) |
| 346 | Round 346 (2026-10-04, PRE-REGISTERED; ONE ledger row, k + 1): 15 public MT5 Expert Advisors from the MQL5 CodeBase, rebuilt from their publ | [round346_mql5_codebase_eas.py](round346_mql5_codebase_eas.py) |
