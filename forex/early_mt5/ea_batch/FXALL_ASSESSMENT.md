# FX all-pairs screen: what the registered "CONFIRMED" verdict hides (2026-10-09 ~10:28 local)

The screen (`PREREG_FX_ALLPAIRS_EAS.md`, Amendment 1; result `FXALL_RESULT.md`) ended with ONE confirmed EA: 21759 RSI_Expert (edge on 11 of 28 pairs in 2026; EDGE2 on 8 of 11 in 2025 and 9 of 11 in 2024). Reading the deals shows it is not usable on MT5 broker:

| 11 confirmed pairs, 0.1 lot each | 2024 | 2025 | 2026 |
|---|---|---|---|
| trades | 521 | 492 | 395 |
| net USD | +4,024 | **-3,103** | +5,948 |
| worst single closed trade | -452 | **-1,387 (USDCHF)** | -126 |
- Over three years the 11 pairs net +6,869 USD on 1,408 trades (+4.9 USD a trade) at a total exposure of 1.1 lots; one pair-year (USDCHF 2025) lost -5,550 USD, more than the other ten pairs made together that year.
- All 26 pairs together in 2026 net only +465 USD. The EA holds positions a median of 1-15 days (up to 76), stacks up to 8, has no usable stop (equity drawdown far above balance drawdown), and single trades reach -1.4% of a 100K account at 0.1 lot, so a safe MT5 broker size is a few hundredths of a lot, which earns nothing.
- Why the rule confirmed it anyway: EDGE2 counts pairs with net > 0 and PF >= 1.1; a negative-skew EA wins small on most pairs and loses big on a few. The registered rule counts cells, not the pooled result, nor the worst loss.
Verdict: 21759 is closed as not suitable; no MT5 broker-data verification, no floating replay. Lesson for the next screen (post-hoc, unregistered): require a pooled positive net across all tested pairs in EACH year and a worst single trade below 0.5% of the account at the tested lot, in addition to the cell count.
