# Pre-registration BRK-REGIME (breakout day, round 19; written 2026-10-15 12:30 local (commit time), before any code or result)
Question: was 2022's breakout edge tied to a MARKET-WIDE climate that a trader could have measured in real time? Events = round 1's session breakouts (hold to close, X4), 46 markets.
Climate measures (server-day closes, all known at the start of each day, ranks against the previous 250 days):
- **global_vol:** 20-day realized volatility of the equal-weight daily return of SP, NSDQ and DAX.
- **trendiness:** cross-market mean of |20-day return| / (20-day daily-return std x sqrt(20)) over the 46 markets (how trending the whole market is).
Cells (2): G1 trade breakouts only on days with global_vol rank >= 0.67; G2 only with trendiness rank >= 0.67.
Gates (DEV 2022-24, VAL 2025, 2026 non-clean): DEV mean >= +0.05 R and t >= 2.24 (daily NW lag 1; Bonferroni 2); VAL mean > 0 and t >= 1.65; beats the unfiltered breakouts by >= 0.05 R in DEV and VAL. Reported: correlation between the monthly breakout result and each climate measure.
Honest prior: about 8%.
