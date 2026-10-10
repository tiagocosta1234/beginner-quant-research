# Pre-registration: the US index overnight return on MT5 broker (family N, two trials + a descriptive study)

Written 2026-10-10 (time = the commit adding this file), BEFORE any statistic of these rules is computed. the trader: "(original wording omitted)".

## Definitions (MT5 broker M1 bid/ask, times converted America/New_York -> Europe/Athens = MT5 broker server)
Markets SP, NSDQ, DOW. Night of day D (Mon-Thu only; Friday->Monday weekends are measured separately and NOT traded): enter at the open of the 15:55 ET minute of D, exit at the open of the 09:35 ET minute of the next business day D+1 (only if D+1 is the next calendar day). Buy at the ask, sell at the bid, plus 0.1 bp slippage per side; the CFD stays open through MT5 broker's rollover (17:00 ET) and no trade happens near it. Day session of D = 09:35 -> 15:55 ET (mids, descriptive only).

## Descriptive study (no acceptance; written now so it is not chosen after looking)
Per market and year: P(night > 0), mean, median, sd, skew, 1% / 5% quantiles, worst night, mean of the day session, and the same for the Friday->Monday window; P(night > 0) by weekday; conditional on the sign of the day session of D, and on the size of D's session move (terciles).

## Trials (equal notional SP + NSDQ + DOW, P&L in bp per night)
N1: long every Mon-Thu night.
N2: long only after a DOWN day session (09:35 -> 15:55 mid return of the equal-weight index < 0); flat otherwise.
Periods: DEV 2022-01 .. 2024-12, VAL 2025, HOLD-OUT 2026-01 .. 2026-09 (one look, only for a trial passing 1-2).

## Acceptance (Bonferroni, two trials)
1. DEV net mean per night > 0 and t >= 2.0.
2. VAL 2025 net mean > 0.
3. HOLD-OUT net mean > 0 (one look).
4. Goal relevance (only after 1-3): sized so that its worst historical night is at most 1,000 USD (MT5 broker's 1%-per-idea) and, separately, at larger sizes, the clean simulation with the pair gives P(pass by 30 Oct) and breach; any size whose worst night exceeds 2,000 USD is reported as unusable (MT5 broker's daily line is a hard breach and the guard cannot act inside a gap).

## Honest prior
About 30% for N1 passing 1-2 (the overnight premium is well documented, our earlier index-daily test found t +1.6 in DEV), about 15% for N2. Even a confirmed N1 is a modest second leg: a night's sd is about 0.6-0.9% and its mean a few bp.
