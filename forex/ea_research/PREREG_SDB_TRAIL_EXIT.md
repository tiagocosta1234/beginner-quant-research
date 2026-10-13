# Pre-registration: does a trailing exit instead of the fixed 1.9% target make the SDB entries earn more on MT5 broker gold? (family X, one variant)

Written 2026-10-09 just after 16:15 local (local clock), BEFORE any simulation of this variant. the trader: "(original wording omitted)" (idea 4 of 4 listed: exits of the SDB on gold; ideas 1 and 3 failed, see the INDEX_INTRADAY_MOM and DAILY_TREND_BASKET results). Ledger 50 of 51 before this trial; this is the 51st and last of the +3 amendment. Bonferroni bar: paired t >= 2.5.
Idea: the frozen SDB rule enters on a stochastic turn with a stop and a target at the same distance (1.9% of the order price). In a trending regime (gold 2024-2026) a fixed target caps the winners while a trailing exit lets them run; the entries stay IDENTICAL, only the exit changes, so the comparison is paired and cheap. This is a modification of OUR OWN implementation (ManualSDB), not of the public EA.

## Variant X1 (fixed now, no tuning)
Entries: exactly the frozen rule of forex/intraday_lab/sdb.py (pct 1.9, expiry 9 bars, K23 / D3 / S7, Bollinger 9 / 2.0, H1; stop orders at yesterday's high / low), simulated on MT5 broker's own M1 bid/ask bars (forex/data_mt5/XAUUSD_M1_rates.parquet), no commission (MT5 broker 'No Commissions'), spread from the bars, no slippage (as the baseline).
Baseline B0 (frozen exits): stop = target = 1.9% of the order level, stop first, one position at a time (the EA places no new order while a position is open).
Variant X1: the same initial stop (1.9% of the level) and NO target; a trailing stop that follows the best price at a distance of 1.9% of the level: for a long, stop_j = max(initial stop, highest BID high up to the previous bar - 1.9% x level); for a short, stop_j = min(initial stop, lowest ASK low up to the previous bar + 1.9% x level); a long exits when the bid low <= stop_j (fill min(stop_j, that bar's bid open)), a short when the ask high >= stop_j (fill max(stop_j, that bar's ask open)). No time limit. The one-position-at-a-time rule follows X1's own exits (its trades may hold longer and skip signals the baseline took). R = net P&L / (1.9% x level).
Statistics per period: trades, mean R, profit factor, total net R and net R per year for B0 and X1; on the entries COMMON to both (same entry minute): the paired difference R(X1) - R(B0): mean, t-statistic; mean holding time in days; largest single-trade R.
Periods: DEV 2022-01-01..2024-12-31, VAL 2025, POOL 2022-2025, HOLD-OUT 2026-01-01..2026-09-30 (one look, only if DEV and VAL pass).

## Acceptance
1. DEV: paired mean difference > 0 with t >= 2.5 on the common entries, AND X1 total net R > B0 total net R, AND X1 profit factor >= B0 profit factor.
2. VAL 2025: paired mean difference > 0 with t >= 1.0 and X1 total net R > B0 total net R.
3. HOLD-OUT 2026: X1 total net R >= B0 total net R (one look).
4. Gate for any use: in the clean simulation the SDB leg with X1 exits raises P(pass by 22 Dec) of the pair at least 2 points with at most 1 point of extra breach (a longer hold raises floating exposure at the daily line); MQL5 change in ManualSDB (a trailing input), validation in the MT5 broker tester against the Python trades (>= 90% match), the guard unchanged; deploy only with the trader's explicit go.
If 1 fails the idea is closed (no hold-out).

## Honest prior
About 10-15%. Trailing exits help in trends and hurt in ranges; 2022-2023 gold was mostly range-bound, the gain in 2024-26 trends may not generalise, and the 1.9% trail is wide (it gives back up to 1.9% of every winner). The paired design gives power, but SDB makes only about 40-60 trades a year.
