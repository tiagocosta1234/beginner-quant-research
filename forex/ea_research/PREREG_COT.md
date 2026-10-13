# Pre-registration: CFTC Commitments of Traders positioning on MT5 broker (family P, two trials)

Written 2026-10-10 (time = the commit adding this file), BEFORE the data is downloaded or any statistic computed. the trader: "go" (idea 4: positioning, the last information source not yet used).

## Data
CFTC legacy futures-only reports (public, cftc.gov/files/dea/history/deacotYYYY.zip, 2020-2026), saved in `D:\finance\data_macro\cot\`. Net speculative position = (non-commercial long - non-commercial short) / open interest. The report is as of Tuesday and released Friday 15:30 ET, so a report is used only from the following Monday.
Markets -> MT5 broker instrument (DJIA: consolidated code 12460+, the x$5 series has gaps; set before any statistic) (sign -1 where the MT5 broker quote is the inverse of the futures): GOLD -> XAUUSD; SILVER -> XAGUSD; WTI crude (NYMEX light sweet) -> WTI; E-mini S&P 500 -> SP; Nasdaq-100 mini -> NSDQ; DJIA (x$5) -> DOW; Euro FX -> EURUSD; Japanese yen -> USDJPY (-1); British pound -> GBPUSD; Australian dollar -> AUDUSD; Canadian dollar -> USDCAD (-1); Swiss franc -> USDCHF (-1); NZ dollar -> NZDUSD. 13 markets.

## Trials (weekly, equal notional per active market; P&L in bp, bid/ask at both ends)
Position held from Monday 01:30 server to the next Monday 01:30 (MT5 broker M1 bid/ask; nearest quoted minute within 30 minutes; weekends held).
P1 contrarian extremes: percentile of the net speculative % of OI within the previous 52 reports; >= 90th -> short the futures' direction, <= 10th -> long; else flat.
P2 positioning momentum: sign of the 4-week change in the net speculative % of OI -> trade in that direction (follow the flow).
Periods: warm-up 2020; DEV 2021-01 .. 2024-12, VAL 2025, HOLD-OUT 2026-01 .. 2026-09 (one look). Statistic: mean bp per active market-week, t over weeks of the portfolio's weekly mean.

## Acceptance (Bonferroni, two trials)
1. DEV: portfolio weekly mean > 0, t >= 2.24, >= 100 active weeks.
2. VAL 2025 mean > 0.
3. HOLD-OUT mean > 0.

## Honest prior
About 10% for P1 (COT extremes are a classic contrarian tool with mixed academic support), 8% for P2. Weekly signals over 13 markets give about 200 weeks of DEV: only a strong effect can pass. Even a pass is a slow overlay, not a fast-pass system.
