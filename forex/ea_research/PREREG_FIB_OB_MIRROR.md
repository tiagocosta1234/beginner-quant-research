# Pre-registration: the Fibonacci 79% + order-block idea INVERTED (short), tested on 2026 (written 2026-10-12, before any inverted trade was computed)

the trader: "(original wording omitted)". The causal long version lost in 2022-25 (FO1 mean -0.196 R / -0.311 R, FO2 -0.088 R / -0.224 R, `FIB_OB_RESULT.md`).
**Declared contamination:** choosing the opposite side after seeing both losing windows is selection on those windows, so 2022-25 cannot prove the mirror. the trader asked for 2026, and 2026 was supposed to be the clean hold-out, BUT the previous run printed a by-year line that included it for the LONG rule (FO1 2026: 335 trades, mean -0.185 R; FO2 2026: 143 trades, mean +0.124 R). So 2026 is no longer unseen: the direction of the FO1 mirror in 2026 is partly known (positive), that of FO2 (negative). No earlier unseen Nasdaq data exists on disk (MT5 broker data start 2021-12, MT5 broker 15 m data only 2026-06..10). The 2026 result is therefore informative mainly if it CONTRADICTS what the long results imply; a pass is a candidate to be confirmed forward, never proof.

## The inverted strategy (same signals, opposite side; nothing re-tuned)
Same 15 m / 1 h construction, causal rules, sessions, news embargo and forced exits as PREREG_FIB_OB.md (OB usable after the next bar closes; swing high usable after two further hourly bars close; 20-bar range from the prior bars). SHORT instead of long, with the roles of the levels swapped:
- entry: FM1 (stop-sell at the fib): the bar's bid-low reaches the fib, fill at min(fib, bid-open) (bid); FM2 (confirmed): signal bar with `Low <= fib < Close`, sell at the NEXT bar's BID-open.
- stop (buy-stop) = the original TARGET (the last known 1 h swing high); target (buy-limit) = the original STOP (the prior 20-bar low). Cover at the ask (bid + the bar-open spread). Forced cover at the close of the 15:45 / 01:45 bars. Order of checks: forced exit, then stop, then target (stop before target when both). On the fill bar of FM1, if the bar's ask-high also reaches the stop, the trade is stopped at once (conservative).
- market NSDQ (the MNQ stand-in); SP and DOW descriptive.
Result: bp of the entry price and R = P&L / (stop - entry); USD at 500 risk per trade = 500 x R (R is small here because the stop is far: report bp as the main number).

## Window and acceptance
HOLD = entries 2026-01-01 .. 2026-09-30, one look. Accept (each variant): >= 40 trades, mean >= +10 bp per trade after the spread, PF(bp) >= 1.3, one-sided t >= 1.65 (day-averaged) AND the same inverted rule has a positive mean bp over 2022-25 (consistency, cannot prove). Also reported: trades, win rate, mean R, total bp, by year 2022-26, and the exact opposite of FO1/FO2 on the same signals as a cross-check.
Two trials (FM1, FM2). A pass is a candidate only: forward/demo confirmation first; nothing goes live from this round.

## Honest prior
Low. A pure mirror of a losing pattern loses the spread twice over; the long's mean of -0.2 R on a stop of about 40 bp is only about -8 bp, close to the cost of one spread, so the mirror is likely near zero or negative after costs. The mirror of FO1 has a tiny win/loss asymmetry (small targets, far stops): high win rate, rare big losses.
