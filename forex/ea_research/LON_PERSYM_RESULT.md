# LON_PERSYM_RESULT - one London-open breakout strategy per symbol, chosen and validated separately (2026-10-15, local clock 21:23)
Pre-registration PREREG_LON_PERSYM.md (commit at 21:22). Code lon_persym.py, output LON_PERSYM_OUTPUT.txt, tables data/si_ledgers/LON_PERSYM*.csv.

## Verdict: 0 of 46 symbols has a London-open breakout strategy that survives
1. Best of 72 London rules per symbol, chosen on 2022-24: average **+0.258 R** a trade in 2022-24 -> **-0.037** in 2025 (17 of 46 positive) -> **-0.107** in 2026 (16 of 46 positive). The choice is mostly the failed-break fade or small squeeze samples, which look best in sample by chance.
2. Kept because positive in both 2025 and 2026: 7 (DAX, DOW, USDJPY, EURUSD, NIKKEI, XAUUSD, GBPCAD): about what chance gives (46 x 0.5 x 0.5 = 11.5 if every rule were a coin).
3. Out of time 2020-21 (HistData, today's MT5 broker London spread; bar t >= 2.45, both years positive): DAX -0.544 R (13 trades), EURUSD +0.014, GBPCAD -0.067, NIKKEI +0.061, **USDJPY +0.153 (t 1.38; 2020 +0.036, 2021 +0.273)**, XAUUSD -0.177 (t -2.26); DOW has no HistData series. **0 pass.**

## Reading for the trader
Choosing a London strategy for each symbol separately does not work: the rule that looks best in 2022-24 averages +0.26 R and then loses in 2025 and 2026. Of the seven that held up in 2025 and 2026, none holds in 2020-21. USDJPY is again the only one above zero in every period (+0.11..+0.22 R), and again not significant.
