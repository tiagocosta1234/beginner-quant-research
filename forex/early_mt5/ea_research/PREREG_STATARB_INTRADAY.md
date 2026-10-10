# Pre-registration: intraday relative value (pairs stat-arb) between economically linked MT5 broker instruments (family R, six trials)

Written 2026-10-10 14:51 local (local clock), BEFORE any simulation of these rules. Context: the trader set the goal "precisamos de um novo sistema, 70% chance de passar o desafio este mes". The spec (`D:/finance/tmp/spec70.txt`, reproduced in the result) says such a system must earn about 500-600 USD a day on the 100K account with a daily Sharpe of 0.5-0.85 if it starts Monday 12 Oct; no EA among the 1,131 tested in 2026 comes near that even in-sample (best net / equity drawdown 6.9, the spec needs 20-30). Every indicator family on single instruments (daily and hourly panels, 2026-10-10) is closed. Relative value between linked instruments is the one intraday information source not yet tested here: two prices driven by a common factor whose difference mean-reverts. It is also the class where high daily Sharpe ratios exist in practice (many short, hedged trades), which is the only kind of Sharpe the spec allows.

## Data
MT5 broker M1 bid/ask bars (`forex/early_mt5/data_mt5/<MKT>_M1_rates.parquet`, server clock), 2021-12-01 .. 2026-10-02; nothing before 2020. For each pair the two legs are joined on common minutes.

## Pairs (fixed now by economic link, not by data)
R1 SP / DOW (US large caps), R2 SP / NSDQ (US large caps, tech tilt), R3 XAUUSD / XAGUSD (precious metals), R4 BRENT / WTI (crude), R5 AUDUSD / NZDUSD (antipodean FX vs USD), R6 EURUSD / GBPUSD (European FX vs USD). Leg A is the first name, leg B the second.

## Rule (identical for all six; no parameter is tuned)
- Bars: M5 bars of the mid (bid + ask) / 2 built from common minutes; a bar needs >= 3 minutes; its close is the mid of its last minute.
- Hedge ratio beta (per server day d): OLS slope of leg A's M5 log returns on leg B's over the previous 20 server days (both legs present), known before day d starts; a day with beta <= 0.2 or fewer than 1,000 return pairs is not traded.
- Spread and z-score at the close of bar k (all inputs up to bar k): with means, variances and covariance of log A and log B over the last 48 bars (4 hours), z = ((logA_k - mA) - beta (logB_k - mB)) / sqrt(vA + beta^2 vB - 2 beta cAB).
- Entry: z <= -2.0 -> long the spread (buy A, sell beta x B); z >= +2.0 -> short the spread (sell A, buy beta x B). Signals only from bars that close between 01:00 and 21:30 server time.
- Exit: z crosses 0 (z >= 0 for a long spread, <= 0 for a short), or 24 bars (2 hours) after entry, or the first bar closing at or after 21:50 server time, or when the next execution minute is missing (closure).
- Execution: at the OPEN of the M1 bar two minutes after the signal bar's close (never the first minute of an hour, never 23:00-01:00), at the quoted ask when buying and the bid when selling, plus 0.1 bp slippage per leg; if that minute is missing in either leg, the next common minute within 5 minutes, else no trade (or, for an exit, the last common minute's close).
- Size: leg A notional 100,000 USD, leg B notional beta x 100,000 USD (for statistics only; the Sharpe ratio is scale-free). One position per pair at a time.

## Statistics
Per pair and period: trades, trades per day, win rate, mean net bp per trade (on leg A notional), gross bp (at mids, no spread), profit factor, daily P&L (server date of exit), daily t, annualised and daily Sharpe, max drawdown, share of trades exited by the z-cross / time stop / session end. Periods: DEV 2022-01-01 .. 2024-12-31, VAL 2025, HOLD-OUT 2026-01-01 .. 2026-09-30 (one look, only for a pair that passes 1-2).

## Acceptance (Bonferroni, six trials)
1. DEV net: daily t >= 2.4 AND mean net bp per trade > 0 AND at least 300 trades.
2. VAL 2025 net: daily t >= 1.0 and mean net bp > 0.
3. HOLD-OUT 2026 net daily Sharpe > 0 (one look).
4. For the trader's goal (a new system with P(pass by 30 Oct) >= 70%): the accepted pairs together, sized within MT5 broker's 1%-risk-per-idea guideline and the guard, must reach a net daily Sharpe of at least 0.5 with a daily mean of at least 500 USD; only then is the clean simulation run for the goal. Anything weaker that passes 1-3 is reported as a candidate second leg (the 22 Dec target needs about +62 USD a day with low variance and correlation <= 0.3 with the pair).
5. Compliance before any use: MT5 broker prohibits hedging on the SAME asset and latency / account-to-account arbitrage; trading two different linked instruments is ordinary relative-value trading, but it is to be asked to MT5 broker in writing before going live.
If 1 fails the pair is closed (no hold-out).

## Honest prior
About 5% that at least one pair passes 1-3, and well under 1% for acceptance 4. Intraday relative-value residuals between index CFDs and FX majors are watched by everyone with low costs; the cheap pairs (indices, FX) have spreads of 0.4-0.9 bp per leg but small residual swings, and the pairs with larger swings (silver, crude) cost 5.5-7.5 bp per leg.

## Dry-run (2026-10-10, no P&L; `STATARB_INTRADAY_DRYRUN.txt`)
M5 bars per pair 312,518 (BRENT/WTI) to 360,016 (EURUSD/GBPUSD); hedge ratios (median, 5-95%): SP/DOW 0.96 (0.68-1.12), SP/NSDQ 0.69 (0.55-0.82), XAU/XAG 0.37 (0.29-0.49), BRENT/WTI 0.91 (0.83-0.93), AUD/NZD 0.83 (0.68-0.96), EUR/GBP 0.71 (0.54-0.95); bars with |z| >= 2 inside trading hours about 7,500-9,700 a year per pair. Round-trip spread cost (both legs, beta-weighted, bp of leg A), median: EUR/GBP 0.71, SP/NSDQ 1.38, AUD/NZD 1.55, SP/DOW 1.59, XAU/XAG 3.55, BRENT/WTI 11.32, plus 0.27-0.39 bp of slippage. Causality: z and beta at a bar are identical on data truncated after that bar; hand check of a bar close and the execution minute matches the raw minutes.
