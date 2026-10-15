# Pre-registration BRK-IMOM (breakout day, round 28; written 2026-10-15 13:50 local, local clock, before any code or result)
Question: does the opening move (the break away from yesterday's close in the first 30 minutes) continue into the close? Published basis: Gao, Han, Li and Zhou (2018, Journal of Financial Economics, "Market intraday momentum"): the first half-hour return (previous close to 10:00 NY) predicts the last half-hour return of the S&P 500 ETF, more strongly together with the 12th half-hour (15:00-15:30).
Sessions as in round 1 (`breakouts.session`: US indices / crypto 09:30-16:00 NY, energy 09:00-14:30 NY, DAX 09:00-17:30 Berlin, NIKKEI 09:00-15:00 Tokyo, ASX 10:00-16:00 Sydney, FX / metals 08:00-17:00 London). Prices = MT5 broker M1 mid for the signal, bid/ask for the trade.
- r_first = mid at session open + 30 min / mid at the previous session close - 1; r_12 = mid at close - 30 min / mid at close - 60 min - 1.
- **G1:** trade in the direction of r_first from close - 30 min to the close (market orders at the minute opens; no stop).
- **G2:** as G1, only on days when r_first and r_12 have the same sign.
Primary class: INDEX (SP, NSDQ, DOW, DAX, NIKKEI, ASX); other classes reported descriptively. Statistic: net bp per trade (one spread paid), Newey-West (lag 1) t of the daily class mean.
Yardsticks: long-only over the same half hour (drift) and a random side.
Gates (DEV 2022-24, VAL 2025, 2026 non-clean): 1. DEV mean > 0 and t >= 2.24 (Bonferroni 2). 2. VAL mean > 0 and t >= 1.65. 3. Beats the long-only half hour in DEV and in VAL.
Honest prior: about 10% (published, but the effect is reported weaker after 2013 and on futures with costs).
Amendment A1 (13:51, dry run only, no P&L seen): the US session close (16:00 NY) is 23:00 server most of the year, which the rollover rule forbids, so the dry run kept only the DST-mismatch weeks for US indices and crypto. All four reference times move one minute earlier: close = close - 1 min (also the previous close of the signal), the trade runs from close - 31 min to close - 1 min, r_12 = close - 61 to close - 31 min.
