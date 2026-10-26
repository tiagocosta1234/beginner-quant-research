# PREREG_PUBLISHED_EFFECTS: two published intraday futures effects, replicated on 2019-2026 data

Written Mon 26 Oct 2026 local (local clock), BEFORE any result of this test was computed. the trader: "then test more" (after every London-open rule, ML direction, wider stops and bigger targets failed).
Rationale: stop re-shuffling the same London entries; test effects that peer-reviewed papers found on earlier data, so 2019-2026 is (mostly) a post-publication replication.

## H1: the "overnight drift" at the European open (Boyarchenko, Larsen & Whelan, NY Fed SR 917 / RFS 2023)
Paper: almost all of the S&P 500 futures premium was earned between 02:00 and 03:00 ET; selloffs are followed by strong positive overnight returns.
Known before running: the authors' July 2026 Liberty Street post says the 02:00-03:00 window has averaged close to zero since 2021. Expected: fail.
- **H1a:** long ES and NQ every weekday from 02:00 ET to 03:00 ET (bar opens), no stop.
- **H1b:** same, only on days after a negative prior US day (16:00 ET to 16:00 ET close-to-close < 0).
- Descriptive: every other overnight hour (18:00-09:00 ET), and 2019-2020 vs 2021-2026.

## H2: US intraday momentum (Gao, Han, Li & Zhou, JFE 2018; Baltussen, Da, Lammers & Martens, JFE 2021)
Paper: the return from the prior close to 10:00 ET predicts the last 30 minutes (15:30-16:00 ET), across many futures (hedging-demand explanation).
- **H2:** ES, NQ, GC, SI: at 15:30 ET take the side of the sign of (prior-day 16:00 ET to today 10:00 ET), exit 16:00 ET, no stop. Secondary: the sign of (prior 16:00 to 15:30) ("rest of day", Baltussen).

## Data and costs
Databento 1-minute 2019-06..2026-09-25 (ES, NQ, GC, SI), timestamps in America/New_York, prices = the open of the first bar at or after each time (max 5 min late, else the day is skipped).
Costs (points, round trip, micro): ES 0.74, NQ 1.1, GC 0.32, SI 0.0112. $ per point per micro: ES 5, NQ 2, GC 10, SI 1000. Pooling is in units of the prior 14-day ATR (NY-date daily bars).

## Bar (three primaries H1a, H1b, H2; alpha 0.01 each)
Pass iff pooled mean net (ATR units) > 0 AND sign-flip P <= 0.01 (20,000 flips of each trade to its mirror, cost on both) AND mean net > 0 in at least 5 of the 7 years 2020-2026.
Every market, $ per micro per trade, trades per year and win rate are reported. All trades are inside one Broker trading day (02:00-03:00 ET and 15:30-16:00 ET are before the 16:10 ET flat rule).
