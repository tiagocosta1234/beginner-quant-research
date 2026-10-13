# Follow-ups (2026-10-12): live log, hedge cost, risk by regime

## 1. Live forward log: `forex/tools/live_log.py` (read-only, writes `forex/forward_test/live_trades.csv`)
Closed positions per EA from the running MT5 broker terminal plus ManualDip's decision lines from the Experts log. Since 2026-10-05: 2 closed XAU5 trades (net -24 USD), no SDB or ManualDip trade yet. ManualDip's first live decision is logged: `DAX+ 2026.10.12: z3 0.57 sigma60 0.0079` (no signal, z3 positive), so the EA decides as designed. Re-run it after each ManualDip signal; its live trades are the clean out-of-sample (the backtest sits on 2022-26 data).

## 2. Cost of holding long and short gold (`hedge_cost.py`, SDB x1.5 + XAU5 x1.5, news-flat on)
| | MT5 broker 12 months | FT 2022-26 |
|---|---|---|
| trades | 559 | 1,806 |
| time with both sides open (of the time in a position) | 14% | 25% |
| ounces hedged (of all open ounces) | 10% | 24% |
| trades the no-hedge rule would drop | 45 (8%) | 262 (14%) |
| P&L of those trades | **+3,587** | **+4,460** |
| spread they cost | 141 | 690 |
| net effect of dropping them | **-3,727** | **-5,150** |
The offset trades are net winners and the spread they cost is small, so holding both sides is not a leak: it is why `InpGuardNoHedge` stays false (consistent with FASTEST_CONFIG2: +2.8 points of pass probability by 30 Nov with no-hedge off). The felt "weakness" is the gold range, not the hedge.

## 3. The pair in the bad regime, by risk multiplier (`risk_regime.py`, FT pool, guard 1,500, no ManualDip)
| mult | 2022-23 net | 2022-23 max DD | 2024-26 net | 2024-26 max DD |
|---|---|---|---|---|
| 1.0 | +6,844 | 7,873 | +69,150 | 4,614 |
| 1.2 | +7,940 | 9,721 | +81,456 | 5,367 |
| **1.5 (live)** | **+4,386** | **16,007** | +98,252 | 6,761 |
| 1.8 | +7,576 | 17,388 | +116,107 | 7,362 |
| 2.0 | +2,528 | 24,726 | +127,718 | 7,986 |
With a gold tailwind (2024-26) profit scales with size and the drawdown stays small. Without it (2022-23) size adds drawdown and no profit: from x1.0 to x1.5 the drawdown doubles (7.9k to 16.0k) while the 2022-23 net falls from 6.8k to 4.4k. The MT5 broker buffer is 8k, so at the live x1.5 a 2022-23-like stretch is the way the account dies; the breach seen in the pass simulation (about 3%) is that scenario weighted by how often the pool says it happens. Idea (not tested, not registered): a drawdown throttle that cuts size after a loss streak. Needs its own pre-registration.
