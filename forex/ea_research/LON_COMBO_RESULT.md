# LON_COMBO_RESULT - MT5 broker cycles of the 7 kept London rules, alone and in all 127 combinations (2026-10-15, local clock 21:38)
Pre-registration PREREG_LON_COMBO.md (commit at 21:35); code lon_combo.py; output LON_COMBO_OUTPUT.txt; table data/si_ledgers/LON_COMBO.csv (127 combinations x 3 sizes x 2 daily-line modes).

## Verdict: no symbol or combination passes the account in a month; 0 of 381 combination-size cells pass more than they breach in both 2020-21 and 2022-25
1. **Each symbol alone (pass / breach within 30 days of a start, optimistic line):** 0% / 0% for every symbol at $250 and $500 a trade in 2026; at $1,000 a trade the best is USDJPY 1.1% / 2.1% in 2026 (2020-21: 0.3% / 17.3%). One trade a day at most per symbol cannot make 8% in 30 days without sizes that breach.
2. **All 127 combinations, best by 2026:** EURUSD + NIKKEI + USDJPY + XAUUSD at $500 a trade: 6.6% pass / 0.7% breach within 30 days in 2026 (in-sample by construction), 1.7% / 0.8% for 2022-25 starts, 2.2% / 7.2% for 2020-21 starts. The top 10 by 2026 average 5.6% / 13.4% in 2026, 3.2% / 14.5% in 2022-25 and 2.4% / 20.3% in 2020-21.
3. **Within 90 days** (same top combinations): EURUSD + NIKKEI + USDJPY + XAUUSD $500: 2026 starts 3.1% / 5.1%, 2022-25 23.2% / 2.3%, 2020-21 24.7% / **37.8%**; DAX + EURUSD + USDJPY + XAUUSD $500: 2.0% / 0.0%, 38.6% / 3.5%, 18.2% / **37.7%**. $1,000 a trade breaches 71-98% within 90 days in every period.
4. In 2020-21 (the only period never used to choose anything) every combination breaches about as often as or more than it passes.

## Reading for the trader
The 2026 numbers look tidy only because these symbols were picked for being positive in 2026. Even so, no combination passes more than about 7% of the time within a month. Over 90 days a four-symbol book at $500 a trade passed 20-40% of 2022-25 starts with little breach, but in 2020-21, where nothing was chosen, it breached about 38%: the edge is not reliable enough to carry the account.
