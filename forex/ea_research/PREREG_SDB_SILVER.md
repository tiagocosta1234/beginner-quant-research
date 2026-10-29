# Pre-registration: does the frozen SDB rule replicate on silver (XAGUSD+)?

Written 2026-10-09 ~09:30 local, BEFORE any silver run. Own-EA programme, family F4 (silver) in its cheapest and most informative form: a replication, not a new search. Why: SDB (our live ManualSDB, public rule 77900) was found by a 2M-candidate search on 2021-26 gold and is "probably curve-fit" (`memory: project-sdb-probably-curve-fit`); the only clean test left is the SAME frozen rule on a related market it was never tuned on. If SDB catches something real about how precious metals break out of a day's range, silver should show it with no re-fitting; if it fails, the live edge deserves less trust (and silver is no diversifier). Lab iteration 30 already showed the frozen SDB has no edge across 28 FX pairs, so a pass here would be specific to metals.

## Test
- EA: the CodeBase EA 77900 `StochDailyBreakout.ex5` with its default inputs (identical trade-for-trade to ManualSDB, `ManualSDB_VERIFY.md`): H1, Bollinger 9, stochastic 23 / 3 / 7, stop = target = 1.9% of the entry price, pending order expiry 9 bars, one position at a time, 0.01 lot. All percentages, so nothing is scaled to silver.
- Instrument `XAGUSD+` (MT5 broker, contract 5,000 oz, tick 0.001). Strategy Tester on the portable MT5 broker terminal (`data\mt5_mt5_tester`, never a live terminal), every tick based on real ticks where MT5 broker has them (since about 2025-09-25) and tester-modelled ticks from M1 bars before (as in `MT5DATA_RESULT.md`, flagged), deposit 100,000 USD, spread and swap as MT5 broker's feed has them (swap-free account: swap is zeroed in the analysis, as for gold).
- Periods: DEV 2022-01-01 .. 2024-12-31 (run per year), VAL 2025, HOLD-OUT 2026-01-01 .. 2026-09-30 (opened once, only if DEV and VAL pass). Gold control: the same EA on `XAUUSD+` from the existing MT5 broker runs (`ea_batch/mt5data/results_<year>/77900.csv`), analysed with the same code.
- Statistic: per-trade return in basis points of the entry price = side x (exit - entry) / entry (deals paired in order: one position at a time makes this exact); profit factor on those returns, win rate, mean, per-trade t = mean / (sd / sqrt(n)). Costs are inside the tester prices (bid/ask).

## Acceptance (single replication hypothesis, one-sided bar)
1. DEV: >= 100 trades, mean > 0, profit factor >= 1.10, per-trade t >= 1.65.
2. VAL: mean > 0 and profit factor >= 1.0.
3. HOLD-OUT 2026 (one look): mean > 0.
If DEV fails, the round ends: silver is not an SDB market and nothing is run on 2025-26. Logged as trials S1 (silver DEV), S2 (silver VAL), S3 (silver HOLD) in `LEDGER.csv` (31 of 40 after this round).
## If accepted
Correlation of silver SDB trades' daily P&L with gold SDB's (expected high); MT5 broker test and portfolio fit exactly as in `PREREG_JJSIM_NQ_SESSIONS.md` (second ManualSDB instance on XAGUSD+, own magic number, one more account-level guard consumer: the guard closes the whole account, so both instances share one day cap).
## Honest prior
Low to moderate. Gold and silver are driven by the same macro flows, so a real SDB mechanism should show; but SDB's gold record is only +4% of price a year net of 2022-25 noise outside 2025-26, the rule's search was gold-specific, and silver's spread is wider in relative terms (about 0.06 on 45 = 13 bp against gold's 1 bp).
