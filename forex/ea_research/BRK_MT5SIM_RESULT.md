# BRK-MT5SIM (breakout day round 14, 2026-10-15 12:16): what the least-bad breakout systems would do on the MT5 broker account from today
Script `brk_mt5sim.py`, table `data\si_ledgers\BRK_MT5SIM.csv`. Start = today's balance 97,708.08 (counted -2,291.92): pass = counted +8,000 (+10,291.92 more; at most +2,000 counted a day), breach = static floor 92,000 or a -2,500 day (daily sums: intraday breaches with several trades a day are understated). Block bootstrap (5-day blocks) of business days from the recent pool (2025-26) and from all 2022-26. These series come from today's searches (leads, not validated edges), so the odds are optimistic.

| system, risk per trade | pass by 30 Oct | breach by 30 Oct | pass by 22 Dec | breach by 22 Dec | pass by 31 Mar 2027 | breach by 31 Mar 2027 |
|---|---|---|---|---|---|---|
| S1 card Nasdaq trend-direction, $1,000 (recent / all) | 0.2% / 0.4% | 2.5% / 2.0% | 15.6% / 23.2% | 22.3% / 19.2% | 42.3% / 53.8% | 34.4% / 29.2% |
| S1, $500 | 0% | 0% | 0.5% / 1.4% | 2.5% / 2.1% | 10.2% / 18.5% | 10.0% / 7.4% |
| S2 US index session ORB (3 indices), $250 | 0% | 0.5% / 0.4% | 2.0% / 5.2% | 19.0% / 12.0% | 11.2% / 27.2% | 38.4% / 22.6% |
| S2, $1,000 | 0.5% | 91-94% | 1% | 99% | 1% | 99% |
| S3 every market with a box >= 40 spreads, $250 | 0% | 18% / 54% | 8.6% / 5.8% | 59.5% / 92.4% | 17.9% / 6.6% | 77% / 93% |
Daily R (mean / sd): S1 +0.044 / 0.93 (recent), +0.074 (all); S2 +0.022 / 2.94 (recent); S3 +0.259 / 4.81 (recent).

Reading: no breakout system passes by 30 Oct (11 trading days); the only one with a usable shape is the card's Nasdaq trend-direction leg (one trade a day, a 2R target that fits the daily cap): at $1,000 a trade roughly 16-23% by 22 Dec and 42-54% by the end of March 2027, with a 20-34% chance of breaching first. Multi-trade breakout portfolios breach: several simultaneous stops make -2,500 days.
