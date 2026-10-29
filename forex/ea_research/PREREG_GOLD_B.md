# Pre-registration: three gold-only trials asked for by the trader ("(original wording omitted)", item B) - range-fade complement (G1) and two confirmation filters on the frozen SDB entries (G2 USD proxy, G3 real yield)

Written 2026-10-09 19:58 local (local clock), BEFORE any simulation of these rules. Ledger 54 before; trials 55 (G1), 56 (G2), 57 (G3). Bonferroni bar for a daily-t test: t >= 2.5. Standing constraints: gold is the one market with a live edge; NO news / event trading (the fundamentals are SLOW state variables); nothing goes live without the trader's explicit go; the SDB and the 5-minute EA stay as they are.
Honest prior: G1 about 3%, G2 and G3 about 3% each. Why so low: the lab has 54 failed trials outside gold; SDB is a 2M-candidate search on 2021-26 gold (probably curve-fit, its DEV/VAL/HOLD years are all inside the author's window); a filter on ~215 trades cannot reach significance unless the effect is huge (see "power" below). These trials are cheap answers to "is there any free lunch around the gold pair", not expected finds.

## G1 - gold mean-reversion in a quiet regime, a complement to the breakout SDB
Data: MT5 broker XAUUSD+ M1 bid / ask bars (forex/data_mt5), M15 bars built as in macro_ta.py (server clock). All indicators use completed bars only.
Regime: ADX(14) of the M15 bars (Wilder smoothing) < 20 at the signal bar.
Signal at the close of bar k (all conditions): LONG when bid close < lower Bollinger band (SMA20 - 2 sd of the last 20 closes) and the regime holds; SHORT when bid close > upper band. Entry at the OPEN of bar k+1 (long at the ask, short at the bid) plus 0.25 USD adverse slippage per side. Stop 1.5 x ATR14(k) from the entry; target = the SMA20 value at bar k (fixed at signal time); time exit at the open after 24 bars (6 hours). Stop first inside a bar (long: bid low <= stop, fill min(stop, bar open) minus slippage; short: ask high >= stop, fill max(stop, ask open) plus slippage). One position at a time; at most 2 new trades per server day; signals ignored 23:30-01:30 server (rollover) and when the next bar is more than 1 hour away (weekend gap exits at the next open). R = net P&L / (1.5 x ATR14).
Statistics: trades, win rate, mean R, profit factor on R, daily t (daily mean R over days with a closed trade), mean net USD per 1 oz, and the daily P&L correlation with the live pair (SDB + XAU5 at x1.2, MT5 broker data, clean-guard series 2025-10..2026-09) for the 12-month window.
Periods: DEV 2022-01-01..2024-12-31, VAL 2025, HOLD-OUT 2026-01-01..2026-09-30 (one look only if DEV and VAL pass).
Acceptance (all): DEV >= 300 trades, mean R > +0.05, PF >= 1.10, daily t >= 2.5; VAL mean R > 0, PF >= 1.05, daily t >= 1.0; HOLD mean R > 0; gate for any use: correlation with the pair <= 0.3, clean-simulation uplift in P(pass) with at most 1 point of extra breach, tester validation. If DEV fails the trial is closed, no hold-out.

## G2 - SDB entries confirmed by a USD proxy
The frozen SDB trade stream on MT5 broker prices: forex/ea_batch/mt5data/results_{2022,2023,2024,2025,2026}/77900.csv (tester runs, 0.01 lot; side deduced from the entry/exit prices and the profit sign). Outcome per trade = net P&L per 1 oz in bp of the entry price (swap zeroed as in the other SDB studies).
USD proxy at the entry day D: S = -r5(EURUSD) + r5(USDJPY), r5 = percent change of the daily closing price (server day, last M1 close) from D-6 to D-1 (the 5 sessions before the entry day, all known at entry). CONFIRMED when (long and S <= 0) or (short and S >= 0), i.e. a long taken while the dollar proxy is not rising, a short taken while it is not falling.
Statistics: per period (DEV 2022-24, VAL 2025, 2026): trades confirmed vs unconfirmed, mean bp of each, difference, PF of each; pooled 2022-25 permutation test (20,000 shuffles of the confirm label, one-sided) for the difference in mean bp.
Acceptance (all): confirmed keeps >= 40% of the trades; difference (confirmed - unconfirmed) > 0 in DEV and in VAL; pooled 2022-25 permutation p <= 0.05 (it is the single test of this trial); confirmed mean bp > 0 in DEV and VAL. 2026 is looked at once only if all of that passes.
Power note: about 215 trades in 2022-26 (roughly 150 in 2022-25); with a trade-level sd near 150 bp the permutation test only reaches p <= 0.05 for a difference around 50 bp or more, which would have to be economically huge. A failure therefore means "not shown", not "shown absent".

## G3 - SDB entries confirmed by the 10-year real yield
Same trade stream and outcome as G2. Data: FRED DFII10 (10-year TIPS yield, daily, public), saved in data\data_macro; point in time: the value of the previous business day (1-day lag). Real-yield change over the 5 sessions before the entry day: dy = DFII10(D-1) - DFII10(D-6) (percentage points).
CONFIRMED when (long and dy <= 0) or (short and dy >= 0) (gold tends to follow falling real yields).
Statistics and acceptance: identical to G2 (own permutation test).
Reported, not a trial: the 5-day correlation of gold returns with real-yield changes in the same sample, to show whether the relation even exists in this data.

## Reporting rule
Whatever the result, the numbers go in the LEDGER (trials 55-57 plus DIAG rows for controls), a RESULT file and the checkpoint. A filter that passes is a LEAD, not a deployment: it would need a fresh forward period (the SDB forward log) because both DEV and VAL are inside the SDB author's selection window.
