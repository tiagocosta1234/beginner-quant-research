# Factor lab pre-registration (Track A), written 2026-10-07 before any result

Purpose: look for a VALID edge in FX using 24 years of independent daily data (FRED), which the 5-year MT5 broker files cannot give. Written BEFORE running anything; no parameter changes after a result. Separate folder / file on purpose (the second PC session edits `forex/early_mt5/intraday_lab/PREREG.md`): merge into the shared lab docs later.

## Data (all public, no key)
- Spot: FRED H.10 noon-New-York rates, daily, USD per EUR / GBP / AUD / NZD and units per USD for JPY / CAD / CHF / NOK / SEK (`DEXUSEU`, `DEXUSUK`, `DEXUSAL`, `DEXUSNZ`, `DEXJPUS`, `DEXCAUS`, `DEXSZUS`, `DEXNOUS`, `DEXSDUS`). EUR from 1999-01. Files in `forex/early_mt5/factor_lab/data/fred/`.
- Rates: OECD 3-month interbank, monthly (`IR3TIB01xxM156N`, xx = US, EZ, GB, AU, NZ, JP, CA, CH, NO, SE). JPY from 2002-04; EUR and GBP end 2026-01 (the carry tests end 2025-12).
- Universe: 9 currencies vs USD (10 incl. USD). Sample start 2002-05 (first month all 10 rates exist, rates lagged one month).

## Return construction (monthly tests H1-H3)
Signal at the last business day of month t from information available then (3-month rate of month t-1, spot history to that day); position held for month t+1 and rebalanced. Long the top 3 and short the bottom 3 currencies by the signal, each leg weight 1/3 of notional (long side 1, short side 1, gross 2, net USD-neutral). Return of a leg = side x (spot return vs USD over the month + (r_ccy - r_usd)/12). Monthly net return = sum of legs minus costs.
COSTS (the broker view, MT5 broker-like): trading 1.2 bp per unit of notional traded for EUR / GBP / JPY, 1.5 bp for AUD / NZD / CAD / CHF, 4 bp for NOK / SEK; financing markup 1.5% a year on every unit of gross notional on top of the interbank rate (assumed from the swap measured in MT5 broker tester deals, about 1.4 bp a night for two legs, NOT read from MT5 broker's rate card). Reported both ways: INTERBANK (no markup, the academic premium) and MT5 broker-LIKE (the binding one).

## Hypotheses (k = 4, one frozen definition each)
- H1 CARRY: signal = lagged 3-month rate; long the 3 highest, short the 3 lowest.
- H2 MOMENTUM: signal = 12-1 month spot return (return from t-12 to t-1 months); long the 3 highest, short the 3 lowest.
- H3 COMBO: signal = average of the cross-sectional ranks of H1 and H2.
- H4 TURN-OF-MONTH USD (daily): long the equal-weighted USD basket (short the 9 currencies) from the close of the last business day of the month through the close of the 3rd business day of the next month; flat otherwise. Costs: 9 legs x 1.5 bp each way, twice a month, no financing markup (4-5 days a month).
Mechanisms: carry = compensation for crash risk / funding-liquidity; momentum = slow-moving capital and central-bank-driven trends; combo = diversification of the two; turn-of-month = month-end portfolio rebalancing flows into USD.

## Phases
DEV 2002-05..2014-12, VAL 2015-01..2020-12, HOLD 2021-01..2025-12 (FRED prices with the MT5 broker-like cost model; the MT5 broker tick files cover the same years). HOLD is printed ONLY for a hypothesis that passes the DEV+VAL rule.

## HIT rule (per hypothesis, MT5 broker-LIKE costs)
1. DEV+VAL pooled (2002-05..2020-12, 224 months): annualised net Sharpe >= 0.4 AND the t-stat of the mean monthly return >= 2.5 (raised for k = 4; low power is accepted and stated: a true Sharpe 0.5 gives t about 2.2 over 18.7 years, so this bar may reject real but small premia).
2. Positive net mean in both DEV and VAL separately.
3. Not one currency: drop each of the 9 non-USD currencies in turn (re-rank the other 8, long 3 / short 3), net Sharpe >= 0.25 for at least 7 of the 9 drops. (For H4: the USD-basket window return is positive for at least 7 of the 9 currencies individually.)
4. HOLD (2021-2025): net Sharpe > 0 and positive in both halves (2021-23, 2024-25).
Reported always: annualised return, volatility, Sharpe, worst drawdown and worst month of each hypothesis at unit gross notional, in INTERBANK and MT5 broker-LIKE terms, by phase and by year, plus the leverage needed to reach 1% a month (descriptive: what the premium means for an MT5 broker account with an 8% drawdown limit).
After any hit: placebo (random ranking, 200 draws) and the MT5 broker simulation of the return stream scaled to a drawdown that fits the account, before any claim. If NO hypothesis passes: Track A is closed; nothing is tuned.
Dry run: `python -m mt5broker.factor_lab.factor_test --dry-run` prints only the data coverage and the number of monthly observations per phase (no returns).

DRY-RUN AMENDMENT 2026-10-07 (before any return was computed): the universe has 9 non-USD currencies (USD is the numeraire), so condition 3 reads '7 of 9 drops' instead of '8 of 10'; HOLD is 2021-01..2025-12 by holding month; H4 per-currency check added as stated above.
