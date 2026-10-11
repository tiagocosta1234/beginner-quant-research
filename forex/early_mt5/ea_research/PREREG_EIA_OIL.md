# Pre-registration: Family OE, WTI around the weekly EIA crude inventory report (written 2026-10-11 ~16:20, before any code or result)

Idea: the EIA Weekly Petroleum Status Report (Wednesday 10:30 New York; Thursday 11:00 in weeks with a US federal holiday on Mon-Wed)
moves WTI sharply. Two documented directions exist (fast efficient adjustment vs. continuation of the first reaction), so the test is
two-sided and pays for it in the bar. Never tested here. Weekly, unrelated to gold. MT5 broker WTI+ spread about 4-5 bp.

## Data and rule
MT5 broker M1 bid/ask WTI+ (server clock -> New York with `.dt`). Release time R as above (pandas USFederalHolidayCalendar for the holiday shift).
first = mid at R+15 min close / mid at R-1 min close - 1 (the first reaction).
- OE1 MOMENTUM: at the open of minute R+16 trade IN the direction of first; exit at the open of the 14:30 NY minute.
- OE2 REVERSAL: the same, AGAINST first.
- OE3 PRE-RELEASE: long at the open of 09:00 NY on release day, exit at the open of minute R-1 (positioning drift into the number).
Only when |first| >= 0.5 x its 52-week std for OE1/OE2. Shorts' P&L = 1 - exit/entry. Cost: bid/ask + 0.1 bp each side. Result in bp.

## Periods and acceptance
DEV 2022-01-01..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-09-30 (one look, only for passing variants).
Accept: DEV t (per event) >= 2.6 (two-sided pair + 1), DEV mean > 0, VAL mean > 0, >= 80 DEV events.
