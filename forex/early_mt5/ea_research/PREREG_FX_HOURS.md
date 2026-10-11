# Pre-registration: Family RB, "currencies weaken in their own working hours" (written 2026-10-11, before any code or result)

Source: Breedon & Ranaldo (2013) "Intraday Patterns in FX Returns and Order Flow" (JMCB); Ranaldo (2009). Mechanism: domestic agents
buy foreign currency during their own working hours (importers, investors abroad), so the home currency depreciates in home hours and
recovers in foreign hours. Held for hours (not minutes), so the per-trade cost (about 0.4-0.8 bp on majors) is small against the move.
Contamination stated now: the K2b/K3 hour x market diagnostic (2026-10-10) looked at 2024-25 hourly cell P&L across all markets; it did not
test this rule, but DEV 2024 and VAL 2025 are not perfectly clean. The 2026 hold-out has never been opened for any hour-of-day rule.

## Data
MT5 broker M1 bid/ask, `.dt` conversion to Europe/London and Asia/Tokyo. Weekdays. Shorts use 1 - exit/entry (CX lesson). Cost: bid/ask + 0.1 bp each side.

## Variants (4, fixed now)
- RB1 European hours: at the open of 08:00 London SELL EURUSD, SELL GBPUSD, BUY USDCHF; exit at the open of 12:00 London.
- RB2 US hours: at the open of 14:00 London BUY EURUSD, BUY GBPUSD, SELL USDCHF (USD weakens in US hours); exit at the open of 19:00 London.
- RB3 = RB1 + RB2 on the same day (daily result = sum of the two windows' means).
- RB4 Tokyo hours: BUY USDJPY at the open of 09:00 JST, exit at the open of 15:00 JST (the yen weakens in Tokyo hours).
Daily result = mean over the pairs of the variant (RB3: RB1 mean + RB2 mean), in bp.

## Periods and acceptance
DEV 2022-01-01..2024-12-31, VAL 2025, HOLD 2026-01-01..2026-09-30 (once, only for passing variants).
Accept for the hold-out: DEV daily t >= 2.5 (4 variants + the K-family history), DEV mean > 0, VAL mean > 0.
Then the account tests (correlation <= 0.3, pass70 MIX uplift >= 3 points by 22 Dec, breach <= +1 point).
