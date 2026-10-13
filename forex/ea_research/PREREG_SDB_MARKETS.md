# Pre-registration: Family SM, our ManualSDB logic on the other MT5 broker (written 2026-10-11 ~21:15, before any run)

the trader: "yes" to trying the SDB logic outside gold. The EA is ours (ManualSDB.mq5, the live code), run in the portable MT5 broker tester, guard OFF,
sizing InpRiskPct 1.0 of 100,000 (so results are comparable in R across markets), all other inputs = the live defaults.
Prior: the frozen SDB failed on silver (2026-10-09). Gold control on MT5 broker data: DEV 2022-24 PF 1.22, VAL 2025 PF 1.37.

Markets (12): NSDQ+, SP+, DOW+, DAX+, NIKKEI+, BTCUSD+, ETHUSD+, WTI+, EURUSD+, GBPUSD+, USDJPY+, AUDUSD+. Chart H1.
Variants (2 per market = 24 trials):
- SM1 FROZEN: InpStopPct = InpTargetPct = 1.9 (gold's values).
- SM2 VOL-SCALED: InpStopPct = InpTargetPct = 1.9 x (market daily-return std / gold daily-return std), the ratio measured on
  2021-12-01..2022-02-28 MT5 broker closes (overlaps the first two DEV months; declared): NSDQ 2.54, SP 1.74, DOW 1.44, DAX 1.82, NIKKEI 1.62,
  BTC 5.06, ETH 5.97, WTI 2.65, EURUSD 0.61, GBPUSD 0.51, USDJPY 0.43, AUDUSD 0.86.
Years: DEV 2022, 2023, 2024 (modelled ticks), VAL 2025 (partly real), HOLD 2026 (real ticks), each a separate tester run.

## Acceptance (fixed now)
Hold-out opened only for market-variants with DEV pooled PF >= 1.20, at least 2 of 3 DEV years with PF >= 1.0, >= 60 DEV trades,
VAL 2025 PF >= 1.10. Pass = HOLD 2026 PF >= 1.10 and net > 0. With 24 trials about one false DEV+VAL pass is expected by luck, so a
pass is a candidate for a forward check, not an edge claim. Then: correlation with the live pair and the account test.
