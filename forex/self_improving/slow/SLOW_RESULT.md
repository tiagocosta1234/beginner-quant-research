# New information at horizons of 1, 5 and 20 days: result (2026-10-13)

Pre-registration: PREREG_SLOW_INFO.md. Code: fetch_alfred.py, slow_lab.py. Ledgers: data\si_ledgers\SLOW_real.csv, SLOW_placebo71..73.csv. Macro surprises in data\data_macro\alfred. 2026 never loaded.

## Information added to price
CFTC Commitments of Traders positioning (legacy futures-and-options combined, 2020-2026, as-of Tuesday, usable from the Friday release: non-commercial and commercial net over open interest, 156-week percentile, 1- and 4-week changes; currency pairs as base minus quote of CME EUR/GBP/JPY/AUD/CAD/CHF/NZD, plus gold, silver, WTI, S&P, Nasdaq, DJIA, Nikkei, bitcoin, ether), naive macro-release surprises from ALFRED first-release vintages (NFP, unemployment, CPI against the previous three prints, FOMC target change; 46 / 47 / 47 / 32 releases, one vintage missing), macro regime with a two-day lag, event timing, lagged cross-asset returns (15 series), price features. About 70 features, decisions at 12:00 server each weekday, H = 1, 5, 20 trading days, real bid / ask, windows A / B / VAL 2025, 2026 sealed.

## Calibration: PASSED
Placebo worlds 71, 72, 73: 0 of 12 cells pass in each; noise ceiling max excess z 2.22. The information coefficient is unreliable with overlapping 20-day targets (placebo IC up to +0.35) and is not used for decisions.

## Real run
0 of 12 cells pass.
| class | H | VAL trades | VAL clusters | VAL net bp | VAL z |
|---|---|---|---|---|---|
| fx | 1 / 5 / 20 d | 725 / 67 / 121 | 21 / 11 / 9 | -1.7 / +50.3 / -3.6 | 0.01 / 2.32 / 0.06 |
| idx | 1 / 5 / 20 d | 228 / 67 / 29 | 11 / 18 / 0 | +11.4 / -45.7 / -10.5 | 1.34 / -0.68 / nan |
| cmd | 1 / 5 / 20 d | 2 / 85 / 38 | 0 / 34 / 12 | +98.1 / -21.4 / -172.0 | nan / 0.33 / 0.67 |
| crypto | 1 / 5 / 20 d | 118 / 207 / 74 | 9 / 42 / 11 | -113.7 / -139.7 / -146.1 | -1.45 / -0.84 / -0.16 |
Best excess z 2.32 (fx, 5 days, 67 trades on 11 clusters, p 0.021 against a Bonferroni bar of 0.0042 and a floor of 20 clusters): at the placebo noise ceiling (2.22). The models stop after 1-26 trees (early stopping on B finds almost nothing to learn), and no cell has even the minimum number of clusters together with a positive net.

## Limits of this answer
Power is low: with 46 markets, 4 independent windows of a year and 20-day holds, a cell yields tens to a few hundred non-overlapping trades; an effect of a few basis points per trade cannot be separated from zero. The surprise proxies are naive (no consensus forecasts). COT is weekly, crowded and public. So 'nothing detectable' with these tools, not 'nothing exists'.

## Verdict
Positioning, naive macro surprises and lagged cross-asset returns, added to price at horizons of 1-20 days, give no cell that beats costs and the noise. The installed system stays.
