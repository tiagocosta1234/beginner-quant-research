# Pre-registration: overnight "try everything" grid (family N2, one selection procedure)

Written 2026-10-10 (time = the commit adding this file), BEFORE any run of this grid. the trader: "tenta de TUDO" on the overnight drift, after N1/N2 failed (OVERNIGHT_RESULT.md).

## Grid (fixed now; every combination is one variant)
Markets and their local cash session (entry minute before the local close -> exit minute after the next local open, in the market's own time zone, converted to the MT5 broker server clock):
US-EW (equal weight SP+NSDQ+DOW), SP, NSDQ, DOW: America/New_York; DAX: Europe/Berlin (close 17:30, open 09:00); NIKKEI: Asia/Tokyo (close 15:00, open 09:00); ASX: Australia/Sydney (close 16:00, open 10:00); XAUUSD: New York times.
Timing (3): entry 5 min before the close -> exit 5 min after the open; entry 2 min before -> exit 2 min after; entry 5 min before -> exit 60 min after the open.
Filters (10): none; trend (entry price above its 200-day mean of entry prices); trend 50-day; below the 200-day mean (counter-check); low volatility (trailing 20-night sd below its trailing 250-night median); high volatility; after a down day session; after an up day session; Mon+Tue nights only; trend 200 AND low volatility.
Weekend (2): Mon-Thu nights only; all nights including Friday->Monday.
Total 8 x 3 x 10 x 2 = 480 variants. Costs: quoted bid/ask at both minutes + 0.1 bp per side; filters use information known at the entry minute only.

## Selection, validation, decision
DEV 2022-24: per-variant t of the mean net bp per calendar weekday (0 on flat nights). Reality check: the best DEV t over the grid compared with its distribution under the null (each variant's nightly series demeaned, common stationary block bootstrap, 300 replications). Variants with DEV t above the null's 95th percentile go to VAL 2025 (survive if VAL mean > 0); survivors form an equal-weight portfolio opened ONCE on 2026-01 .. 2026-09 (mean > 0 to pass).
Goal relevance (only for a survivor of all three): sized so that its worst historical night is <= 1,000 USD, the USD per day it adds; and the size it would need for 500 USD a day together with its worst night at that size.

## Honest prior
About 15% that any variant beats the reality check and survives 2025 and 2026 (the trend filter has the best literature support); about 0% that the overnight can be the 70%-this-month system (mean a few bp against a 50-90 bp nightly sd).
