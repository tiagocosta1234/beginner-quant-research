# Pre-registration: the MIRROR of F2 - fade the NR7 breakout on the 28 FX pairs (trial 40 of 40, the last of the budget)

Written 2026-10-09 15:13 local (local clock), BEFORE any simulation of this rule. Born from the F2 result (FX_NR7_RESULT.md): NR7 breakouts on FX reverse (pooled 2022-25 mean -0.207 R, t -6.8, 4/28 pairs positive). Because the idea comes from the 2022-2025 sample, that sample CANNOT validate it; only the untouched 2026-01..2026-09 months can. Ledger after this trial: 40 of 40: the lab budget is then spent.

## Rule F2m (fixed now, no tuning)
Signal and levels exactly as F2: NR7 on trading day d (range strictly the smallest of the last 7 trading days, server clock, MT5 broker M1 bars, days with >= 1,000 bars), levels H(d) and L(d) live during day d+1 only.
Trigger on day d+1: UPPER break = first M1 bar whose ASK high >= H(d); LOWER break = first M1 bar whose BID low <= L(d); if neither, no trade; if both inside the same M1 bar, no trade; otherwise the earlier one.
Entry (the fade): at the CLOSE of the trigger bar. Upper break: SELL at that bar's bid close x (1 - 0.2 bp). Lower break: BUY at that bar's ask close x (1 + 0.2 bp).
Risk distance R0 = H(d) - L(d) (the signal day's range), fixed. Stop: short at entry + R0 (ask high >= stop, filled at max(stop, that bar's ask open) x (1 + 0.2 bp)); long at entry - R0 (bid low <= stop, filled at min(stop, that bar's bid open) x (1 - 0.2 bp)); stop checked from the bar AFTER the entry bar. Exit otherwise at the last M1 close of day d+3 (short: ask close, long: bid close). No target. No trade if R0 < 5 x the signal day's mean spread. One position per pair at a time. R multiple = pnl / R0.
Periods: DEV 2022-24, VAL 2025, POOL 2022-25 (consistency only), HOLD-OUT 2026-01-01..2026-09-30 (the decision, ONE look).

## Acceptance
A. Consistency (not evidence): DEV pooled mean R > 0 and VAL pooled mean R > 0. If A fails the idea is closed WITHOUT opening 2026.
B. Decision on the 2026 hold-out, pooled over the 28 pairs: >= 300 trades, mean R >= +0.05, daily t >= 2.24, mean R > 0 on at least 18 of 28 pairs.
C. For any use: it must raise P(pass by 22 Dec) of the pair in the clean simulation without more than 1 point of extra breach, then a live check on MT5 broker data / execution before any money.
## Honest prior
About 10%. The sign is established in-sample, but stops, entry at the bar close and costs reshape the magnitude (mirroring a -0.2 R continuation rule does not give +0.2 R), and one 9-month hold-out is a small test. Value if it passes: an independent once-a-day FX leg. Value if it fails: closes the compression family and spends the last trial.
