# Pre-registration: confluence panel on hourly bars -- 42 MT5 broker, real bid/ask costs, hour-of-day x market structure (family K2, four trials)

Written 2026-10-10 13:56 local (local clock), BEFORE any simulation of these rules. Follows `CONFLUENCE_PANEL_RESULT.md` (daily panel: all six trials closed, only drift made money). the trader (2026-10-10): "(original wording omitted)". Ledger 241 rows before this family; Bonferroni family here: four trials.

## Why this is a different question from the daily panel
The daily panel could only see patterns that last a day or more. Intraday structure (which hour of the server day, which market, what the last hours did, where price is against yesterday's range) has about 20 times more observations and the one thing that is documented to be non-random in FX, indices and metals: time-of-day effects tied to session opens and closes. Two lessons from the daily round are built in: (1) the test must beat a random re-timing of the same positions (circular-shift permutation), because drift fakes edge; (2) the model may use market identity and hour (`mkt`, `hour`), which the daily panel deliberately excluded, since hour x market is exactly where an intraday effect would live.

## Data
MT5 broker M1 bid/ask bars (`forex/data_mt5/*_M1_rates.parquet`, columns t, bo bh bl bc, ao ah al ac), server clock, 2021-12-01 to 2026-10-02 (nothing before 2020 is used). 42 markets: the 28 FX pairs; SP, NSDQ, DOW, DAX, NIKKEI, ASX; XAUUSD, XAGUSD; WTI, BRENT; BTCUSD, ETHUSD, LTCUSD, XRPUSD. Hourly bars from the server hour of t; a bar needs >= 20 M1 minutes; Saturday and Sunday bars (crypto) are dropped, so crypto is flat on weekends like everything else. The same integrity rule as the daily panel (bars after a market's last inconsistent bar only).
Prices: mid = (bid + ask) / 2. Bar k has start time T_k, features from all its M1 minutes; m_k = mid at the first minute of bar k (the OPEN, the price at which a decision taken at the close of bar k-1 is executed).

## Timing (no look-ahead)
A decision after bar k (features include everything up to the last minute of bar k) is executed at the first minute of the NEXT existing bar k+1 at its quoted bid/ask (so a decision before a weekend or an overnight closure is executed at the re-opening price, and no closure gap is "captured"). The position earns log(m_(k+2) / m_(k+1)) (held through bar k+1, marked at the next bar's open; a closure after bar k+1 is held through, gap risk included). Cost of a change of position = half the quoted spread at the first minute of bar k+1 (relative to mid) + 0.1 bp slippage, per unit of notional traded.

## Features (bars up to and including k; truncation-tested in the dry-run)
sigma_k = sqrt(EWMA, alpha 0.02, min 100 bars, of squared bar-to-bar log returns of the mid close). Returns r1 r2 r4 r8 r24 r72 r120 = log(c_k / c_(k-L)) / (sigma_k sqrt(L)) over bar index. Day structure (server date): move since the day's first bar open, move from the previous day's close, distance of the close to the previous day's high and low, in units of sigma_k sqrt(24). Position of the close in the last 24-bar and 120-bar range; RSI(14) on bar closes; ATR(6)/ATR(48); spread of the bar's last minute relative to sigma_k x mid, and relative to its own 120-bar median; hour (0-23), weekday, month, class code, market id (categorical). Context (same value for all markets at the same hour): USD proxy over 4 and 24 bars (equal-weight of -logret of EURUSD GBPUSD AUDUSD NZDUSD and +logret of USDJPY USDCAD USDCHF), SP over 4 and 24 bars, gold over 24 bars, real-yield change of the previous weekday (DFII10, lagged one weekday). Cross-section: rank of r8 and r24 among the markets with a bar at that hour.

## Label and models (fixed now)
y_h = log(m_(k+1+h) / m_(k+1)) / (sigma_k sqrt(h)) for h in {1, 4}, labels clipped to +-4 in training.
S1, S4 (seasonality, no features): prediction = n / (n + 200) x mean of y_h over the training rows of the same (market, hour).
G1, G4 (boosting): HistGradientBoostingRegressor(max_depth 3, learning_rate 0.05, max_iter 150, min_samples_leaf 1000, l2 10, random_state 0, categorical = market id), NaN native, pooled over all markets.
Walk-forward: test year Y in 2024 and 2025 (2026 only if the hold-out opens): fitted on rows whose label window ends before Jan 1 of Y; scale s = std of the OUT-OF-SAMPLE predictions of the same model fitted one year earlier on the year Y-1. Position per unit: z = prediction / s, pos = sign(z) x clip(|z| - 1, 0, 1) (no trade unless the prediction exceeds one scale-sigma; full size at two). Weight w = pos x 0.0005 / sigma_k (each market targets 5 bp of per-bar volatility at |pos| = 1, about 0.23% daily), P&L = sum over markets of w x bar return - sum |w_k - w_(k-1)| x cost.
Diagnostics that are NOT trials: IC by hour and class, shuffled-label control for G1, long-only drift yardstick over the same bars, results by class, share of P&L in the top 3 hours, truncation test, permutation importance of G1 on 2025.

## Periods and statistics
DEV 2024-01-01..2024-12-31 and VAL 2025 (both out-of-sample for the model), POOL = both (two years), HOLD-OUT 2026-01-01..2026-09-30 (one look). Statistics per period from the daily sums (server date) of bar P&L: net and gross annualised Sharpe (x sqrt 252), daily t, mean bp/day, profit factor, win rate, max drawdown, trades per day, mean net bp per executed position change, and the circular-shift permutation (1,000 random shifts of each market's position series by 120 or more bars inside the test window).

## Acceptance (Bonferroni, four trials; ALL of 1-4)
1. POOL 2024-25 net: daily t >= 2.4 AND net Sharpe >= 1.0 (two years, so in practice a Sharpe near 1.7).
2. Sign consistency: net Sharpe > 0 in both 2024 and 2025, and 2025 >= 0.3.
3. Permutation p <= 0.01 against the random circular shifts.
4. Mean daily cross-sectional rank IC > 0 with t >= 2.
5. HOLD-OUT 2026 net Sharpe > 0 (one look).
6. Gate for any use (as K): gold-pair correlation <= 0.3, clean-simulation uplift with <= 1 point of extra breach, MT5 broker-tester re-run, fixed risk, hard stops, AccountGuard-compatible, and the daily-loss line (a hard breach at 2.5%) respected by construction.
If 1 fails the trial is closed (no hold-out).

## Honest prior
About 2% that any of the four clears the bar. The documented intraday effects are small against FX/index/metal CFD spreads, our own intraday tests (micro-scalp ML, BTC M1/M5 rules, NQ session setups, index opening structure, trend-pullback) all lost, and only two years are out-of-sample, so the bar (a Sharpe near 1.7) is hard to reach by luck and hard to reach by skill. The test is still worth running because it is the first with enough breadth (42 markets) and real quote costs to say whether ANY hour-of-day x market structure survives, and because a clean negative lets us stop spending on indicator confluences and move the search to information we have not used (event timing, positioning) or accept the pair as the product.

## Dry-run counts (2026-10-10, no P&L; `CONFLUENCE_H1_DRYRUN.txt`)
1,235,539 market-bars, 42 markets (25,872 to 30,119 hourly bars each), 31 features, first usable bar 2021-12-08. Out-of-sample market-bars: DEV 2024 257,519 (262 server dates), VAL 2025 256,726 (261), POOL 514,245 (523 dates, 41.0 markets per bar-time), HOLD 2026 192,463 (195 dates). First fit (test 2024): 521,720 training rows; the scale model for 2024 uses 265,847 rows (test 2023). Median relative spread at the first minute: EURUSD 0.43 bp, GBPJPY 0.7, XAUUSD 0.8, SP 0.8, NSDQ 0.75, NIKKEI 2.3, WTI 5.5, BTCUSD 7.9, XRPUSD 18.9. Causality: 550 feature comparisons on truncated bars, 0 mismatches; context unchanged when the future is cut; hand check of the open, the close, r4, the next-bar return and the entry cost on gold matches the raw M1 minutes. Power: 523 daily observations and an effective breadth far below 42 (the markets share the same hours and the same USD / risk factors); a daily t of 2.4 over two years needs a Sharpe near 1.7, so a real but modest edge (Sharpe 0.5-1.0) would NOT be accepted and would be reported as "indicated, not established" together with its IC and the permutation p.
