# Pre-registration: do the most promising batch EAs have an edge on the FX pairs in general?

Written 2026-10-08 ~20:50 local, BEFORE any result of this screen. Requested by the trader while out ("(original wording omitted)").

## Question
Each EA of the 1,220-EA batch was run once, on one symbol, in 2026. A real edge should not depend on the one symbol an EA happened to be screened on. Which of the EAs with the best-looking 2026 numbers keep an edge across the 28 FX pairs, and then in 2025 and 2024?

## Candidates (11 EAs; chosen BEFORE any cross-pair result, from the 2026 single-symbol real-tick batch)
Filters on the 2026 run: net > 0, >= 30 round trips, profit factor >= 1.3 (tier 2: >= 1.2), top-3 trades <= 35% (tier 2: 45%) of the net, positive in both halves of 2026 (tier 2: at least one), equity drawdown <= 10% (tier 2: 15%), then the source code was read for martingale / grid / zone recovery / lot multiplier / averaging-down / a second "hedge" symbol; rejected by hand: New Martin, Babi Ngepet, Daily Zone Recovery (martingale / grid), Improve (needs a hedge symbol), e-News-Lucky (news trading is out), Angry Bird and Exp_ColorJFatl_Digit_ReOpen (known grid / pyramiding), BADX (failed 2024 and 2025 earlier), SDB 77900 (already tested on FX in lab iteration 30), tiny-edge EAs.
- Tier 1: 13462 Exp_ColorSchaffMFITrendCycle (USDJPY H1), 74818 Market Miner (EURUSD H1), 1294 Exp_ADX_Smoothed (XAUUSD H4), 11256 Exp_TSI_DeMarker (XAUUSD H4), 19655 GalacticExplosion (EURUSD H1), 21759 RSI_Expert (USDJPY M15), 17339 Waddah Attar Win (EURUSD M15), 77236 GDS Renko Bollinger 4-Mode (XAUUSD M1), 17568 SupportResistTrade (EURUSD M1).
- Tier 2: 16938 Exp_Fractal_RSI (AUDUSD H4), 22909 Exp_XFisher_org_v1 (USDJPY H4).

## Stage 1 (2026-01-01 .. 2026-09-30)
Each EA on each of the 28 FX pairs (MT5 broker symbols, its own timeframe, default inputs, USD 100,000, real ticks, MT5 broker commission and swap: the same settings as every earlier screen; the MT5 broker terminal is free now that the bot no longer uses it). The EA's own single-symbol result (results_2026) and rows of the old multi-symbol screen (same period and settings) are reused instead of rerun.
- EDGE on a pair: >= 30 round trips, net > 0 after commission and swap, profit factor >= 1.2, top-3 trades <= 40% of the net.
- STAGE-1 PASS: edge on >= 10 of the 28 pairs. (If an EA had a 12% chance of an "edge" on a pair by luck, 10 of 28 happens about 2% of the time; 11 EAs give about 0.2 false passes.)

## Stage 2 (only STAGE-1 passers, only on the pairs where they had an edge)
Same runs for 2025 and for 2024. EDGE2 on a pair-year: >= 20 round trips, net > 0, profit factor >= 1.1. CONFIRMED: in BOTH 2025 and 2024, EDGE2 on >= 60% of those pairs (and at least 5 pairs).

## Not done by this screen (the next steps, each needs the trader's go)
MT5 broker-data verification of the confirmed EAs (MT5 broker bars, modelled ticks before Oct 2025, real ticks after; MT5 broker's symbols accept only IOC fills, so sources need the same FOK -> IOC patch), pass speed and the floating-equity MT5 broker replay, correlation with the live pair. Nothing here goes near the live account; all tester runs use the MT5 broker terminal only.

## Amendment 1 (2026-10-08 ~23:55 local): grid / basket disqualifier
Written after 44 of 298 stage-1 runs, before any stage-2 run. Reason: 74818 Market Miner meets the registered edge rule on 13 of its first 18 pairs (profit factor 2 to 7), but its deals show it is an averaging basket that my code reading missed: 0.01-lot entries with no stop, up to 1,504 positions open at once on GBPCHF, positions held up to 188 days. Where price returns it closes everything at a small profit; where it does not (GBPCHF -88,609 USD, EURCHF -47,130 USD) the account would be dead on MT5 broker (2.5% daily loss, 8% floor). The registered rule (trips, PF, top-3) cannot see this.
- Rule added: an EA that holds MORE than 20 positions at the same moment in ANY stage-1 cell (own run, multi-symbol seed or new run) is a GRID and is disqualified. It cannot PASS stage 1 whatever its profit factor, and its remaining stage-1 cells are not run.
- The threshold (20) was fixed BEFORE the other EAs' counts were computed. Computing them afterwards, on the cells already held, the rule also catches 17339 Waddah Attar Win (25 open at once, median hold 36 days, max 84 days, from its EURUSD seed) and 16938 Exp_Fractal_RSI (50 open at once, median hold 86 days, max 257 days, from its AUDUSD seed): both are stop-less accumulators like 74818. 19655 GalacticExplosion peaks at 18 and stays in. So three EAs are disqualified, not one; I first wrote "only 74818" and that was wrong. The threshold is not adjusted to change who is caught.
- The other 8 EAs are judged exactly as registered above. Disqualified EAs stay in the report with the number of simultaneous positions, so the reasoning is auditable.
- Implementation: `GRID_MAXPOS`, `max_open()`, `grid_table()` in `fx_allpairs.py`; the screen was restarted (it resumes from `fxall/status.csv`) so the running process uses the amended code.

## Decision
No stage-1 pass => the batch holds no cross-pair FX edge among its best-looking EAs; reported as such. Passers that fail stage 2 are reported as 2026-only. Only CONFIRMED EAs are proposed for the MT5 broker-data stage.
