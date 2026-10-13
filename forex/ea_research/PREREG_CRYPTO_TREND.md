# Pre-registration: daily trend following on MT5 broker's crypto CFDs (BTCUSD+ primary)

Written 2026-10-09 ~09:30 local, BEFORE any simulation (the M1 export of the four symbols had just been started). Own-EA programme, new family F5. Why this family: it is the one idea on the list that is both different in kind from the gold pair (no shared driver, trades seven days a week, one decision a day, costs of a few basis points per flip instead of per trade) and backed by a documented effect (time-series momentum / moving-average trend in crypto); nothing here was found by searching this data. The previous rounds are in `JJSIM_NQ_RESULT.md` and `INDEX_DAILY_RESULT.md`; trials already logged: 22 of 40.

## Instruments, data, clock
`BTCUSD+` primary (1 lot = 2 coins); replication `ETHUSD+`, `LTCUSD+`, `XRPUSD+`. MT5 broker's own M1 bars (bid OHLC + bar spread) exported with `ea_batch/mt5data_m1_export.py` to `forex/data_mt5/<NAME>_M1_rates.parquet` (not committed), 2021-12-01 .. 2026-10-08; the symbols have bars on all seven weekdays. A day = a server calendar day (00:00-24:00 server); day open = open of its first M1 bar, day close = close of its last M1 bar (bid).

## Rule C1 (primary): 50-day trend, always in the market, long or short
At every day open the position for that day is LONG if the previous day's close is above the simple average of the previous 50 daily closes, otherwise SHORT; the position is carried (not rebuilt) while the sign does not change. Return of day t = side x (close_t / close_{t-1} - 1) for a position carried over from t-1; on a flip the old position is closed and the new one opened at the open of the new day, the day's return being measured from that open. Cost of a flip (round trip: close one side, open the other) = the average bar spread of the first 5 M1 bars of the day (as a fraction of price) + 4 basis points of slippage (2 bp per fill); no cost on days without a flip; swap-free account. First position of the sample: opened at the first day open with the same cost.
Statistic unit: return per unit of notional; daily series including every calendar day (crypto trades weekends); t = mean daily return / (sd / sqrt(days)); annualised Sharpe = mean / sd x sqrt(365); max drawdown of the cumulative daily return; number of flips.

## Amendment 1 (2026-10-09 ~09:28 local, written after `--check` and BEFORE any trial was run): the crypto M1 history starts later than registered
`--check` shows MT5 broker's M1 bars for all four crypto symbols start on 2022-04-03 (the D1 history goes back to 2021, the M1 history does not). DEV therefore runs from the first day with a valid average (about 2022-05-23 for the 50-day rule, about 2022-07-12 for the 100-day rule) to 2024-12-31, about 2.6 years instead of 2.9; the acceptance bars are NOT relaxed (DEV t >= 2.0 over a shorter sample is the harder test). Measured data facts: complete days (median 1,440 bars, weekends included), median opening spread BTC 0.082%, ETH 0.174%, XRP 0.179%, LTC 0.712% (so a BTC flip costs about 12 bp with the 4 bp of slippage, an LTC flip about 75 bp).

## Periods (fixed now)
Warm-up 2021-12-01 .. 2022-01-31 (needed for the 50-day average, no result taken), DEV 2022-02-01 .. 2024-12-31, VAL 2025-01-01 .. 2025-12-31, HOLD-OUT 2026-01-01 .. 2026-09-30 (opened ONCE, only if C1 passes DEV and VAL).

## Trials (6, all in `LEDGER.csv`; only C1 can be accepted)
C1 primary. C2 the 20-day average. C3 the 100-day average. C4 long or flat (no shorts). C5 C1 with a 3 x ATR(14 daily) trailing stop on the held side (stop checked on the day's M1 high / low, re-entry only at the next sign change). C6 position scaled by 1 / (20-day realised daily volatility) normalised to its DEV mean (volatility targeting; reported only, no cost change).

## Acceptance of C1 (all must hold)
1. DEV: mean daily return after costs > 0 and daily t >= 2.0.
2. VAL: mean > 0 and daily t >= 0.5.
3. HOLD-OUT 2026 (one look): mean > 0.
4. Replication, `ETHUSD+`, `LTCUSD+`, `XRPUSD+` with the same rule over 2022-02 .. 2025-12: positive mean on at least two of the three.
A variant that beats C1 in DEV is only a candidate for a later registered round. If C1 fails 1-2 the round ends, no hold-out, no replication.

## If C1 is accepted: MT5 broker test and portfolio fit
Position sized as a fraction of the 100K account: notional N (1 lot of `BTCUSD+` = 2 coins), stand-alone MT5 broker Pro 100K replay (8% target with 2% a day counted, 2.5% hard daily line on equity incl. the floating P&L of the held position, 8% floor, our 2.0% daily loss cap, swap-free) for N = 20%, 40%, 60% of equity (BTC's daily volatility is about 3%: 100% would put a normal bad day at the 2.5% line), every start day of 2022-2025; correlation with the gold pair's daily P&L (weekend crypto P&L summed into the next business day) and overlap on the pair's 10 worst days; combined pass and breach with the 2% caps on the SUM of the daily lows (pessimistic). Gate: P(pass within 62 business days) up by >= 5 points with breach <= 5% and not worse than the pair alone. Only then an MQL5 EA (one daily decision, fixed lots, hard stop on every order, IOC fills, magic number, AccountGuard-compatible), validated against the Python positions; nothing goes near the live account without the trader's go. MT5 broker's "identical trades across users" rule is a risk for any public rule; this one is simple enough that the lot size and the timing of our own EA are the only differences we can offer.

## Honest prior
Moderate for a positive sign (crypto trend is among the best-documented single-asset effects) but a short, regime-dominated sample (2022 bear, 2023-24 bull): DEV alone can look good because it contains two clean trends, and the effect has weakened as the market matured. VAL 2025 and the HOLD-OUT 2026 are the real test. The stand-alone return is small next to the gold pair (a 40% notional earns about 3% a year per Sharpe point on a 100K account at BTC's volatility), so the realistic value is diversification and weekend coverage, not pass speed.
