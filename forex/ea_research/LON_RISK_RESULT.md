# LON_RISK_RESULT - risk-per-trade sweep for the 7 kept London rules and their 127 combinations (2026-10-15, local clock 21:42)
Pre-registration PREREG_LON_RISK.md (commit at 21:40); code lon_risk.py (vectorised cycles; engine check equal to the loop version); output LON_RISK_OUTPUT.txt; table D:/finance/si_ledgers/LON_RISK.csv (3,705 combination x scheme x risk cells). Sizing: FLAT (same risk on every symbol) and EQRISK (risk inversely proportional to each symbol's 2022-24 daily-R volatility), 100-1,500 USD a trade.

## Verdict: no risk level makes any combination pass the account; 0 of 3,705 cells are promising in 2020-21
1. **Best monthly (30-day) pass with breach <= 10%:** 13.8% chosen on 2026 (DOW + XAUUSD EQRISK $1,400; in 2020-21 5.1% pass / 24.4% breach), 15.7% chosen on 2022-25 (DAX + EURUSD + XAUUSD EQRISK $1,100; in 2020-21 5.4% / 38.9%), 4.3% chosen on 2020-21 itself. Frontier: at most 18.5% (2026), 19.2% (2022-25), 9.6% (2020-21) within 30 days at ANY breach level.
2. **Best 90-day pass with breach <= 10%:** chosen on 2022-25, DAX + USDJPY + XAUUSD EQRISK $800: 50.9% / 9.1% in 2022-25 but **17.3% / 63.0% in 2020-21** and 9.8% / 1.1% in 2026. Chosen on 2026, DAX + DOW + XAUUSD EQRISK $1,100: 25.4% / 0% in 2026, 49.7% / 14.3% in 2022-25, **8.8% / 64.2% in 2020-21**.
3. Every configuration that looks good in 2022-25 or 2026 breaches 50-65% of 2020-21 starts within 90 days; the configurations that are safe in 2020-21 (small risk, $300-400) pass about 10% within 90 days and 0% in 2026.
4. Sizes per symbol alone: best 30-day pass with breach <= 10% in 2026 is 1.8% (XAUUSD $1,400); USDJPY $900 1.1%.

## Reading for the trader
Changing the risk per trade only moves along one line: small risk never reaches 8% in a month, large risk breaches. Equal-risk weighting helps a little in sample, but no combination and no risk level holds up in 2020-21, the only period never used to choose these rules. Gold is in most of the "best" combinations because 2022-26 was a gold bull market; in 2020-21 the same combinations breach most of the time.

## Addendum (21:44): the trader asked for 2026 only, from the real account state (lon_oct2026.py, LON_OCT2026_OUTPUT.txt)
Every configuration (3,705) over all 187 eleven-trading-day windows of 2026 (in-sample), starting from balance 97,708 (floor 5,708 away, target +10,292): the best pass rate is **2.1%**, at 43-54% breach (DAX + NIKKEI + XAUUSD or EURUSD + NIKKEI + XAUUSD, equal-risk, $1,400-1,500 a trade). With breach <= 10% the best pass rate is **0%**. A first run counted 11 TRADE days instead of 11 business days and was corrected before reporting.
