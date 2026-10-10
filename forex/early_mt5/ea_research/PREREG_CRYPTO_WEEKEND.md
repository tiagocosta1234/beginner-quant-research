# Pre-registration: crypto on weekends (family W, three trials)

Written 2026-10-10 (time = the commit adding this file), BEFORE any statistic. the trader: "testar cripto" (idea 3: earn on Saturday/Sunday, when the gold pair cannot trade). MT5 broker crypto CFDs trade on weekends (about 82% of minutes present), spreads BTC 7.8 bp, ETH 16.4 bp (median, weekend); LTC (63 bp) and XRP are left out.

## Universe and clock
BTCUSD and ETHUSD, equal notional, MT5 broker M1 bid/ask, server clock. Weekend window = Saturday 01:05 -> Sunday 22:50 server (clear of the 23:00-01:00 rollover hours). Trade P&L = bid/ask at both minutes + 0.1 bp per side, in bp, averaged over the two coins.

## Trials
W1 weekend drift: long Saturday 01:05 -> Sunday 22:50.
W2 weekend reversal: r = return Saturday 01:05 -> Sunday 12:00 (mid); if |r| > 1.0 x the coin's daily sd (sd of the last 20 daily close-to-close returns, known on Saturday) take -sign(r) at Sunday 12:02, exit Sunday 22:50; else flat.
W3 weekend 4-hour fade: 4-hour blocks starting 01:05, 05:05, 09:05, 13:05, 17:05 server on Saturday and Sunday; if a block's return is beyond +-2 x the coin's 4-hour sd (sd of the previous 30 days of 4-hour block returns, all days), take the opposite side at the next minute and hold to the next block end (Sunday's last block exits at 22:50). Diagnostic (not a trial): the same W3 rule on weekdays.
Periods: DEV 2022-01 .. 2024-12, VAL 2025, HOLD-OUT 2026-01 .. 2026-09 (one look).

## Acceptance (Bonferroni, three trials)
1. DEV: mean net bp per trade > 0, t >= 2.4, >= 100 trades (W1: >= 100 weekends).
2. VAL 2025 mean > 0.
3. HOLD-OUT mean > 0.
Goal relevance: a passing rule adds its average per weekend to the account's Saturday/Sunday results (days the pair cannot use) at 1% risk per idea.

## Honest prior
About 8% that any passes. Our BTC rules on M1, M5 and daily trend failed this week; weekend liquidity is thinner (reversion is plausible), but BTC's spread (about 8 bp) is large against a weekend's typical move.

## Amendment (2026-10-10, after a first run whose W3 numbers were INVALID)
Bug: W3 entered at the START of the block whose return was the signal (it traded the same block backwards: 0% wins). Fixed to the registered rule: enter one minute after the signal block ENDS, hold the next block. Data fact found at the same time: MT5 broker has almost no weekend crypto minutes in 2022 (4% coverage; 79% in 2023, 89% in 2024, 100% in 2025), so DEV is in practice 2023-24 (about 90-100 weekends); the trade-count floor of 100 for W1 is kept as registered. W1 and W2 code is unchanged.
