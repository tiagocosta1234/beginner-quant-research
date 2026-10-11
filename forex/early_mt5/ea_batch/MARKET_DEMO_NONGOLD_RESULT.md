# Market demo screen, NON-GOLD amendment: stage 1 (MT5 broker real ticks, 2025Q4 + 2026, default inputs, USD 100K) - 2026-10-11

| EA (symbol) | 2025Q4 net | 2026 net | pooled PF | trades | net / max eq DD | stage 1 |
|---|---|---|---|---|---|---|
| **Quantum Commander (DOW+)** | **+22,222** | **+115,509** | **2.85** | 349 | **7.8** | **PASS** (M5 = H1, identical deals) |
| Market Anomalies EA (USDJPY+) M15 / H1 | +24,576 / +24,892 | +33,429 / +27,629 | 1.36 / 1.33 | 746 | 3.0 / 2.6 | FAIL only on lot ratio 8.6 (lot does NOT follow losses: corr(lot, balance) -0.03, next lot after a loss 2.79 vs win 3.09: risk-based sizing on a variable stop, not martingale); 5 losing months of 12 |
| ORB Revolution (NSDQ+) | +13,173 | +19,721 | 1.28 | 258 | 1.4 | FAIL (PF, net/DD, lot ratio) |
| Asura Strike US100 (NSDQ+) | +1,451 | -614 | 1.03 | 277 | 0.3 | FAIL |
| Range Breakout EA (USDJPY/BTC/DOW/DAX, gold off) | +9,688 | -15,130 | 0.96 | 447 | -0.3 | FAIL |
| Chiroptera (EURUSD+ chart) | +6,503 | no deals | - | - | - | FAIL (no 2026 trades: the demo / its pair list did not trade in the tester in 2026; not investigated) |

Quantum Commander details: lots scale with the balance (corr +0.98, compounding; after a loss 3.00 vs after a win 2.96: not martingale);
11 of 12 months positive; 76% winning days; avg win +878 / avg loss -697 at about 3 lots of DOW (very large default size);
worst trade -9,289 (2026-09-17: a 400-point DOW drop in 26 minutes at 4.64 lots), next worst -4,114. Entries cluster at server 14:00,
18:00, 09:00 and some at 23:00 / 01:00 (rollover window). Next: stage 2 (2022-2025 modelled ticks), then fixed-lot sizing for MT5 broker,
correlation with the pair, and the v5 account test. Nothing bought (Market product, 899.99 USD; the trader decides).

## Stage 2 and the forward check (2026-10-11): Quantum Commander REJECTED
Stage 2 (modelled ticks, default inputs): 2022 +52,869 PF 2.83 | 2023 +30,244 PF 2.59 | 2024 +34,585 PF 2.05 | 2025 +112,168 PF 3.40: passes
the registered bar easily. But the product page says it was PUBLISHED on 2026-09-01 (v3.0, updated 2026-09-20), so 2022 .. Aug 2026 is
the period it was built and tuned on, and only September 2026 onward is out of sample. Out of sample it loses:
- the seller's own live signal (mql5.com/en/signals/2388460, US30 on IC Markets, started 2026-08-27, 64 trades): growth -20.31%,
  max drawdown 36% by balance;
- our MT5 broker real-tick run: September 2026 is its only losing month of twelve (-2,292 USD at the default size).
A perfect in-sample record next to a losing first live month is the signature of a curve-fitted Market EA. Not bought, not used.
Lesson for the screen: check the PUBLICATION date first; only the months after it count as evidence.

## FREE non-gold EAs, stage 1 (MT5 broker real ticks, 2025Q4 + 2026, default inputs) - 2026-10-11 evening: all five fail
| EA (symbol) | 2025Q4 | 2026 | pooled PF | after its last update | verdict |
|---|---|---|---|---|---|
| Havana EA (DOW+ M5) | -21,934 | -38,903 | 0.51 | -60,837 (4,487 trades since 2025-05-16) | FAIL |
| RangeBreakout EA MT5, Claye Weight (NSDQ+ M15) | +979 | -958 | 1.00 | +22 (341 trades since 2025-01-07) | FAIL: no edge |
| Dark Moon MT5 (EURUSD+ M15) | +114 | -348 | 0.82 | -252 | FAIL (up to 13 positions at once: grid) |
| Universal Breakout MT5 (USDJPY+ M15) | -1,457 | -36,962 | 0.73 | - | FAIL |
| Dark Venus MT5 (EURUSD+ M15) | +668 | +2,581 | 2.11 | +321 since 2026-08-19 | FAIL: grid (31 positions at once, lot ratio 28) |
Nothing usable. The only own non-gold edge remains ManualDip.
