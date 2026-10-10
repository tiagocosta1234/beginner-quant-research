# Pre-registration: does a narrow-range day (NR7) precede a breakout that pays on the 28 FX pairs? (family F2, own rule)

Written 2026-10-09 15:11 local (local clock), BEFORE any simulation of this rule. Ledger at 38 of 40 (37 + trend_pullback H1); this round is ONE registered trial (F2) on all 28 pairs pooled (the pairs are replication, not extra trials); ONE trial stays in reserve (F3). Kill rule of the plan: 40 variants or Friday 23:00. the trader asked to keep working in the lab (2026-10-09 ~15:10).
Why this idea: it is a different driver from gold trend (volatility compression on FX), uses 28 independent-ish instruments for sample size, and trades once per signal with a stop at the other side of the day's range, so the risk per trade is small and known.

## Rule F2 (all parameters fixed now, no tuning)
Data: MT5 broker's own M1 bid and ask bars (forex/early_mt5/data_mt5/<PAIR>_M1_rates.parquet), server clock; a trading day = a server calendar day with at least 1,000 M1 bars (drops the Saturday sliver). Daily high H and low L from the BID bars; range = H - L.
Signal day d: range(d) is strictly the smallest of the last 7 trading days (NR7, today included).
Orders for the NEXT trading day d+1 only (OCO): BUY STOP at H(d), SELL STOP at L(d). A buy fills when the M1 ASK high >= H(d) at max(H(d), that bar's ask open) + 0.2 bp of the price; a sell fills when the M1 BID low <= L(d) at min(L(d), that bar's bid open) - 0.2 bp. First trigger wins, the other order is cancelled; if both would trigger inside the same M1 bar, the trade is booked as a loss of exactly 1 R (worst case). No trade if R (entry minus stop distance, incl. the spread) < 5 x the signal day's mean spread.
Stop: the opposite side of the signal day's range (L(d) for a long, H(d) for a short), checked on M1 (long: bid low <= stop; short: ask high >= stop), filled at the stop or worse (gap: the bar's open) with 0.2 bp slippage against us. Exit otherwise at the last M1 close of day d+3 (bid close for a long, ask close for a short). One position per pair at a time (a new signal while in a trade is skipped). Swap-free, no commission (MT5 broker No Commissions), spread from the bars.
Statistics (pooled over the 28 pairs): trades, win rate, mean R per trade (R = pnl / risk distance), profit factor on R, daily t-statistic (sum of the trades' R by CLOSE calendar day over all calendar days with bars, zero otherwise), number of pairs with mean R > 0.
Periods: DEV 2022-01-01..2024-12-31, VAL 2025, POOL 2022-2025, HOLD-OUT 2026-01-01..2026-09-30 (one look, only if DEV and VAL pass).

## Acceptance (all must hold; bars raised for the 40-variant family, Bonferroni)
1. DEV pooled: >= 500 trades, mean R > +0.05, profit factor >= 1.10, daily t >= 2.24.
2. VAL pooled: mean R > 0, profit factor >= 1.05, daily t >= 1.0.
3. Breadth (DEV+VAL pooled): mean R > 0 on at least 18 of the 28 pairs.
4. HOLD-OUT 2026 pooled: mean R > 0 (one look).
5. For any use: the leg must raise P(pass by 22 Dec) of the pair in the clean simulation without more than 1 point of extra breach.
If 1 fails the idea is closed (no hold-out); a pass on 1-3 and a fail on 4 is reported as failed, not retuned.

## Honest prior
Low (about 3%). NR7 / inside-day breakouts are old, widely traded and the overnight FX market is efficient; the 1,220-EA batch and the factor lab found nothing durable on FX. Value of a pass: an independent, once-a-day, small-risk leg on 28 pairs. Value of a fail: closes the compression family for the record.
