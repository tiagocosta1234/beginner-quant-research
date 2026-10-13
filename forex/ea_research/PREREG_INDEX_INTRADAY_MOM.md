# Pre-registration: does the first-30-minute move predict the last 30 minutes on MT5 broker's US index CFDs? (family I, one rule, three indices)

Written 2026-10-09 16:03 local (local clock), BEFORE any simulation of this rule. the trader (2026-10-09 ~15:55): "(original wording omitted)" (index intraday momentum, daily trend basket, SDB exits). The lab budget (48) is amended +3 (ledger 51), one primary variant per idea; Bonferroni bar: daily t >= 2.5.
Idea: documented intraday-momentum anomaly (the return from the previous close to 10:00 New York predicts the last half hour's return, strongest in index futures / ETFs). MT5 broker index spreads are small (median 0.75 bp NSDQ, 0.83 SP, 0.66 DOW), so costs do not dominate a once-a-day 30-minute trade, and the exposure (US index, afternoon) is unlike the gold pair.

## Rule I1 (fixed now, no tuning)
Clock: MT5 broker stores SERVER time (EET / EEST, Europe/Athens); New York time is derived with the real time zones (so the US/EU daylight-saving weeks line up). Instruments: NSDQ+, SP+, DOW+ (MT5 broker M1 bid/ask bars), each traded independently, equal weight in the pooled statistics.
Signal day D (Monday-Friday, only if the four bars below exist): r1 = bid close of the 09:59 NY bar of day D / bid close of the 15:59 NY bar of the PREVIOUS trading day (at most 4 calendar days earlier) - 1.
Trade: at the OPEN of the 15:30 NY bar of day D: long (at the ask open) if r1 > 0, short (at the bid open) if r1 < 0; exit at the OPEN of the 16:00 NY bar (long at the bid, short at the ask = bid + that bar's spread). 0.12 bp of the price slippage on each fill. No stop, one trade per instrument per day, size irrelevant (results in bp of the price). Early-close days (no 15:30 or 16:00 bar) are skipped by construction.
Statistics: trades, win rate, mean net bp per trade (and mid-to-mid gross: net + half of the entry and exit spreads + the slippage, diagnostic), profit factor, pooled daily t (daily mean of the three instruments' bp over days with at least one trade), mean bp per instrument.
Periods: DEV 2022-01-01..2024-12-31, VAL 2025, POOL 2022-2025, HOLD-OUT 2026-01-01..2026-09-30 (one look, only if DEV and VAL pass).

## Acceptance (Bonferroni, 51 variants)
1. DEV pooled: >= 500 trades, mean net > +1.0 bp, PF >= 1.10, daily t >= 2.5, mean > 0 on at least 2 of the 3 instruments.
2. VAL 2025 pooled: mean net > 0, PF >= 1.05, daily t >= 1.0.
3. HOLD-OUT 2026 pooled: mean net > 0 (one look).
4. Gate for any use: correlation of the daily P&L with the gold pair <= 0.2; in the clean simulation the leg raises P(pass by 22 Dec) with at most 1 point of extra breach; validation on MT5 broker data in the tester; fixed lots, hard stop, magic number, AccountGuard-compatible.
If 1 fails the idea is closed (no hold-out).

## Honest prior
About 10%. The effect is documented (US index futures, 1993-2013 and later) but has weakened, and costs/slippage on a 30-minute trade can still eat a 2-4 bp edge; the 3 indices are highly correlated (they are close to one test).
