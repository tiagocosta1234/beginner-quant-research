# Family SM result: ManualSDB on 12 other MT5 broker (2026-10-12)

Pre-registration: PREREG_SDB_MARKETS.md (written before any run). Full table: SDB_MARKETS_DEV.txt. Trials: 24 (12 markets x SM1 frozen / SM2 vol-scaled), DEV 2022-24, VAL 2025.

## Verdict: NO market-variant passes. The 2026 hold-out was never opened.
Rule: DEV pooled PF >= 1.20, >= 2 of 3 DEV years with PF >= 1.0, >= 60 DEV trades, VAL 2025 PF >= 1.10. All 24 trials have `to_holdout = False`.

Closest misses (none was rescued by relaxing the rule):
- USDJPY SM2: DEV PF 1.18 (163 trades, +13.3k), VAL PF 1.35 (+8.7k). Fails DEV by 0.02. With 24 trials about one near-pass is expected by luck.
- DOW SM1: DEV PF 1.09, VAL 1.43. Fails DEV. (2026 look at DOW was descriptive only and is not evidence.)
- SP SM2: DEV PF 1.21 but VAL 0.78.
- GBPUSD SM2: DEV 1.10, VAL 1.08. Fails both.

Clearly dead: ETH (SM1 DEV PF 0.46, -72k), WTI (0.82 both), BTC (0.91 / 0.80), NSDQ, DAX, NIKKEI on DEV, EURUSD/AUDUSD/USDJPY SM1 on VAL (PF 0.24-0.44).

## Gaps (tester timed out twice at 900 s)
DOW SM2 2024, ETHUSD SM1 2024, WTI SM2 2023 and 2025. None can change the verdict: DOW SM2 already fails VAL (0.87), ETH SM1 DEV is 0.46 without 2024, WTI SM2 DEV is 0.82 without 2023.

## Conclusion
The frozen ManualSDB logic (and the vol-scaled variant) has no edge outside gold on this test. Consistent with the earlier silver failure and with the view that SDB is tuned to gold's 2021-26 history. Gold stays the only market for SDB. USDJPY SM2 may be re-registered as a new forward-only test; it is not a candidate now.
