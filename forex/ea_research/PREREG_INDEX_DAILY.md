# Pre-registration: one-trade-a-day rules on MT5 broker's US index CFDs (overnight drift and the New York opening-range breakout)

Written 2026-10-09 ~09:02 local, BEFORE any simulation of these rules. Part of the own-EA programme of `../PLAN_2026-10-09.md` (family F1, second round). Reason for this round: `JJSIM_NQ_RESULT.md` showed that `NSDQ+` costs about 2 points a trade (average spread 1.46 points plus slippage), which sank a 1.9-trades-a-night rule whose gross edge was about zero; a design that trades once a day and moves 100+ points per trade pays that toll about 50 times less. Both rules are well-known textbook anomalies, taken from general knowledge and NOT tuned on this data. Trials already used in the programme: 14 (jjsim_nq). Kill rule of the plan: 40 variants.

## Instruments, clock, data, costs
- Primary `NSDQ+`; replication (only for a rule that passes the primary tests) on `SP+` and `DOW+`. MT5 broker's own M1 bars (`forex/data_mt5/<NAME>_M1_rates.parquet`: bid OHLC + bar spread, 2021-12-01 .. 2026-10-08). MT5 broker server clock = New York + 7 hours: 09:30 NY = 16:30 server, 16:30 NY = 23:30 server, 15:45 NY = 22:45 server. The index CFDs trade 01:05-23:55 server (18:05-16:55 NY).
- Costs exactly as `jjsim_sessions.py`: buy at the ask (bid + the bar's spread), sell at the bid, short entries at the bid and covers at the ask; stops and market exits fill with slippage against us; slippage = 0.12 basis points of the price (0.3 point on a 25,000 Nasdaq, about 0.08 on the S&P, about 0.5 on the Dow), applied to every market entry, stop and market exit; no commission (the account is No Commissions); swap-free account. Both-levels-in-one-bar: the STOP is assumed first.
- Statistic unit: return in basis points of the entry price per trade; daily P&L = the day's sum of trade returns on the day they CLOSE, zero on days without a trade. t-statistic = mean daily bp / (sd / sqrt(number of days)). Points and R multiples are reported too.

## Rule A: overnight drift (long only)
Buy at the open of the first bar at or after 16:30 NY (must be before 16:50) on every NY weekday Monday-Friday; sell at the open of the first bar at or after 09:30 NY of the next NY weekday that has data (a Friday entry exits Monday). No stop, nothing else. (Weekend gaps included.)
## Rule B: opening-range breakout (one trade a day at most)
Range = high and low (bid) of the 09:30-10:00 NY bars. After 10:00, at the close of each M1 bar: close above the range high -> long, close below the range low -> short, the first signal of the day only, no signal at or after 15:00 NY; entry at the next bar's open. Stop at the opposite side of the range (R = distance from the entry to the stop), target 1.5 R, any position still open is closed at the open of the first bar at or after 15:45 NY. Days without a signal have no trade.

## Periods (fixed now)
DEV 2022-01-01 .. 2024-12-31, VAL 2025-01-01 .. 2025-12-31, HOLD-OUT 2026-01-01 .. 2026-09-30 (opened ONCE, only for a primary that passes DEV and VAL), Dec 2021 = mechanics check.

## Trials (8, all in `LEDGER.csv`; only A1 and B1 can be accepted; Bonferroni for two primaries)
A1 PRIMARY as above. A2 no Friday entries. A3 with a stop at -1.0% of the entry price. B1 PRIMARY as above. B2 target 1.0 R. B3 range 09:30-09:45. B4 stop at the middle of the range (target 1.5 R from that stop distance). B5 long signals only.

## Acceptance of a primary (A1 or B1; all must hold)
1. DEV: >= 400 trades for A1 / >= 300 for B1, mean return per trade > 0 after costs, profit factor >= 1.10, daily t >= 2.24.
2. VAL: mean > 0, profit factor >= 1.05, daily t >= 1.0.
3. HOLD-OUT 2026 (one look): net return > 0 and profit factor >= 1.05.
4. Replication on `SP+` and `DOW+` over 2022-2025 with the same rule: mean > 0 on both, or t >= 1 on one and t > -1 on the other.
A variant that beats its primary in DEV is only a candidate for a later registered round, never accepted. If neither primary passes 1-2, the round ends: reported as such, no hold-out opened.

## If a primary is accepted: MT5 broker test and portfolio fit
Exactly as `PREREG_JJSIM_NQ_SESSIONS.md` ("MT5 broker test"): stand-alone MT5 broker Pro 100K replay (8% target with 2% a day counted, 2.5% hard daily line, 8% floor, our 2.0% daily loss cap, swap-free; 2 and 4 lots of `NSDQ+` = 0.5 / 1.0 NQ contracts; for rule A the overnight floating loss is counted on the day it falls), correlation with the gold pair's daily P&L and overlap on the pair's 10 worst days, combined pass and breach on 2022-26 with the 2% caps on the SUM of the daily lows (pessimistic). Gate: P(pass within 62 business days) up by >= 5 points with breach <= 5% and not worse than the pair alone. Only then an MQL5 EA (fixed lots, hard stop on every order, IOC fills), validated against the Python trades; nothing goes near the live account without the trader's go.

## Honest prior
Rule A: a documented anomaly (most of the equity-index premium accrues overnight) whose size changes by regime and which a 1.5-2.0 point round-trip toll eats a visible part of; rule B: a classic with a modest and unstable edge. Neither was found by searching this data. A weak, noisy result in DEV/VAL means the round is closed, not re-tuned.
