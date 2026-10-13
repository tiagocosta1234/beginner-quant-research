# Pre-registration: screen of MQL5 Market gold EAs on MT5 broker data through their free demo versions (the trader 2026-10-09 22:12: "avanca com a lista")

Written 2026-10-09 22:12 local (local clock), BEFORE any demo has been downloaded or run. Each EA tested on one timeframe is ONE trial in the lab ledger (family M, trials 63 onward); an EA with an unknown timeframe is run on M15 and H1 and counts as two. Standing constraints: nothing is bought (demos only; a purchase needs the trader's explicit go and his money), nothing goes live without the trader's go, MT5 broker rules apply (no grid / martingale / hedging / news trading).
Source of the candidates: Comet / MQL5 Market search "XAUUSD gold" sorted by rating (page 1), filtered by: (a) the description says no grid, no martingale, a hard stop on every trade, (b) at least 20 reviews and a rating of 4.0 or more, or a long public live signal, (c) a style that the lab already finds to be the only one that works on gold (breakout / momentum on M15-H1, not tick scalping), (d) a free demo (demos run only in the Strategy Tester, which is what we need). Marketing text, ratings and live-signal links are NOT evidence; they only select what to test.

## Procedure
the trader downloads the demo of each EA inside the TESTER terminal D:\finance\mt5_mt5_tester (portable copy, MQL5 community login typed by the trader himself): Ctrl+T > Market > search the name > Download demo. The files appear in MQL5\Experts\Market\. The runner `forex/ea_batch/market_demo_run.py` finds every .ex5 there (except the 5-minute EA already in use), reads the timeframe from `market_candidates.csv` and runs the MT5 broker-data tester jobs (portable tester terminal, never the live one): XAUUSD+, Model 4 (every tick based on real ticks), USD 100,000, the EA's DEFAULT inputs, MT5 broker spreads, no commission.
Stage 1 (the 100%-real-tick window): 2025Q4 (2025-10-01..12-31) and 2026 (2026-01-01..09-30). Stage 2 (only for stage-1 passers; modelled ticks): 2022, 2023, 2024, 2025.

## Metrics (from the tester's deals and report)
Trades (closing deals), net USD at the default lot, profit factor, win rate, average trade, trades a month, maximum concurrent open positions, maximum / minimum lot ratio (martingale / grid detector), the tester's maximum equity drawdown, net / max equity drawdown.

## Acceptance
Stage 1 (all, on the two real-tick windows together and each one separately for the sign): net > 0 in BOTH 2025Q4 and 2026; pooled PF >= 1.30; >= 60 trades; net / max equity drawdown >= 2; max concurrent positions <= 3 and max / min lot <= 3 (a grid or martingale EA is rejected here whatever its profit, MT5 broker rules and the daily-loss line); trades a month >= 5 (the trader wants frequent).
Stage 2: PF >= 1.0 in at least 3 of the 4 modelled years 2022-2025.
Gate for any use (not part of this screen): daily P&L correlation with the live pair <= 0.3, a clean-guard simulation of the EA at 1% risk showing an uplift in P(pass) of at least 5 points with at most 1 point of extra breach, a forward check on a demo account, and the trader's explicit go. Honest prior: about 3% per EA to pass stage 1 (the independent test of 20 popular gold strategies found 0 significant; marketing results are selected, and these demos run on MT5 broker prices with MT5 broker costs), and a first screening of 10 EAs therefore has about 25% to produce even one candidate.

## Amendment 2026-10-09 22:30 (before any run)
Impulse MT5 is dropped: its own listing describes a "momentum grid EA ... one unified grid framework", which the screen would reject anyway (MT5 broker and the grid / martingale detector). Timeframes were fixed from the sellers' own pages: Broker Gold EA M30 (the author's guide), Ghost Scalper H1 (listing), Lizard H1, TitanForge H1; the others stay M15 and H1 (two trials each). Authors / product ids are in market_candidates.csv; a product with the right name but another author is a DIFFERENT EA.

## Amendment 2026-10-11 (non-gold candidates; written before any non-gold demo run)
the trader: "continua a procura de mais EAs fora do ouro". Same procedure, stages and acceptance as above, on each EA's own symbol
(`market_candidates_nongold.csv`, column symbol): Quantum Commander (DOW+), ORB Revolution (NSDQ+), Market Anomalies (USDJPY+),
Range Breakout EA with Range Filters (USDJPY+ chart; its other built-in markets may trade too: the deals are split by symbol if the
report allows, else reported pooled), Chiroptera (EURUSD+ chart, multi-pair), Asura Strike US100 (NSDQ+). Selection from the MQL5
Market pages 1-3 on 2026-10-11: rating >= 4.0 with >= 15 reviews (Asura: none yet), the listing states no grid / martingale /
averaging, a stop on each trade or a stated SL input, a published live signal. Excluded on the listing text: Quantum Emperor (splits and
recovers losers), Quantum King (grid + martingale), Sentinel (recovery grid), Big Forex Players (lot step), Black Dragon (lot multiplier),
Hamster Scalping (virtual SL, order series). Extra gate before any use: correlation with the live pair <= 0.3 and the v5 account test.

## Amendment 2026-10-11 evening: FREE non-gold EAs only (the trader: no paid EA this year), written before any of them is downloaded or run
Candidates (market_candidates_nongold.csv, FREE): Havana EA (DOW+ M5), RangeBreakout EA MT5 by Claye Weight (NSDQ+ M15), Dark Venus MT5
(EURUSD+ M15), Dark Moon MT5 (EURUSD+ M15), Universal Breakout MT5 (USDJPY+ M15). Same stages and acceptance as above, default inputs.
NEW RULE (Quantum Commander lesson): only months AFTER the product's last update count as out-of-sample. Stage 1 still runs 2025Q4 + 2026,
but the verdict also reports the net after the last-update date; an EA whose post-update months are negative is rejected even if it
passes the stage-1 bar. (Havana: after 2025-05-16; RangeBreakout: after 2025-01-07; Dark Moon: after 2025-10-17; Dark Venus: after
2026-08-19, i.e. almost no out-of-sample data, reported but cannot be accepted on this window.)
