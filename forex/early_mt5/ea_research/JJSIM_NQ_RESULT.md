# JJ Simon "6 PM / 8 PM session" setup automated on MT5 broker's Nasdaq CFD: result (2026-10-09 ~01:15 local)

Pre-registration: `PREREG_JJSIM_NQ_SESSIONS.md` (written before any simulation). Simulator: `jjsim_sessions.py`. Trial ledger: `LEDGER.csv`. Data: MT5 broker's own `NSDQ+` M1 bars (bid + bar spread of the live No-Commissions account), 2021-12-01..2026-10-08; the 2026 hold-out was NOT opened.

## Verdict: T1 FAILS every acceptance criterion; the strategy as automated has a negative edge after costs. No EA was built.
| trial | DEV 2022-24 net pts | PF | evening t | VAL 2025 net pts | PF | evening t |
|---|---|---|---|---|---|---|
| T1 primary (TP 38, SL 25, threshold 30) | -3,514 (1,543 trades) | 0.79 | -3.82 | -929 (775) | 0.90 | -1.29 |
| T2 TP 25 / SL 25 | -2,917 | 0.83 | -3.41 | -1,620 | 0.84 | -2.55 |
| T3 TP 50 / SL 25 | -2,617 | 0.84 | -2.63 | -627 | 0.93 | -0.82 |
| T4 TP 38 / SL 38 | -2,753 | 0.83 | -2.83 | -1,688 | 0.84 | -2.09 |
| T5 + structure break | -2,584 | 0.80 | -3.27 | -1,406 | 0.80 | -2.53 |
| T6 continuation only | -2,520 | 0.76 | -3.59 | -418 | 0.90 | -0.90 |
| T7 reversion only | -1,052 | 0.87 | -1.61 | -997 | 0.86 | -1.66 |
| T8 6 PM only | -2,106 | 0.70 | -3.77 | -342 | 0.92 | -0.65 |
| T9 Asian only | -1,571 | 0.86 | -2.08 | -1,010 | 0.83 | -1.78 |
| T10 threshold 20 | -3,399 | 0.82 | -3.49 | -1,552 | 0.86 | -1.98 |
| T11 threshold 40 | -3,459 | 0.77 | -3.89 | -880 | 0.90 | -1.23 |
| T12 no break-even move | -2,577 | 0.84 | -2.80 | -1,604 | 0.84 | -2.22 |
All 12 trials lose on both periods (acceptance needed >= 300 / 100 trades, positive expectancy, PF >= 1.15 / 1.10, t >= 2.0 / 1.0, and 7 of 11 other trials positive on DEV: 0 of 11). T1 wins 33.8% of its trades (DEV) against a break-even of about 40% for a 38 / 25 bracket with costs.

## Diagnostics after the verdict (not registered trials, not used for any decision)
- Cost split: the same T1 rules with ZERO spread and ZERO slippage give DEV -424 pts (PF 0.97, t -0.48) and VAL +805 pts (PF 1.09, t +1.13): before costs there is no edge in DEV and a weak one in VAL. The average bar spread of `NSDQ+` in the 18:00-22:00 NY window is 1.46 points; spread plus 0.3 slippage costs about 2.0 points per trade, and the strategy trades about 1.9 times per evening, so costs alone take roughly 3.8 points a night from an edge of about zero.
- MT5 broker Pro 100K replay of T1, 2022-2025 only, every evening as a start day, our 2.0% daily cap on, 8% target with 2% a day counted, 2.5% hard daily line, 8% floor: 2 lots (0.25% risk a trade): pass 0%, breach 85% (median 149 evenings), P&L -44,422 USD over four years, worst evening -1,771; 4 lots (0.5% risk a trade): pass 3%, breach 88% (median 58 evenings), P&L -88,844 USD, worst evening -3,542, 31 evenings hit the 2% cap.

## What this does and does not say
- It tests the rules as they could be written down from the video: displacement-candle entries, continuation / reversion to the 18:00 open, 38 / 25 bracket, break-even at 20:00. It does not test the presenter's discretion (break-of-structure judgement, early exits when "the unfair move is not happening", layering several positions, sizing per account), which is where he says the real profit comes from; that part cannot be automated without inventing rules.
- The instrument is MT5 broker's Nasdaq CFD on a feed whose evening open is 18:05 NY, not the CME futures he trades; the 1.46-point average spread is that feed's real spread on the account we hold. A raw-spread account (0.4 points plus 6 USD a lot) would cost about the same per trade (about 1.6 points).
- His own caveats stand: one month of examples, win rate "much lower" than shown at 1.5R, a "$400k in 90 days" claim that cannot be checked.
- Lesson for the research programme (`../PLAN_2026-10-09.md`): on `NSDQ+` any design that trades more than about once a day needs an expected move per trade far above 2 points; a high-turnover mean-reversion rule starts about 4 points a night behind.

## Inversion (Amendment 1 of the pre-registration, run 2026-10-09 ~01:30; the trader: "tenta inverter")
Signal exactly as T1, order direction flipped. Bar for acceptance: Bonferroni for 14 trials (DEV evening t >= 2.69), VAL net > 0; both periods are no longer clean for these trials, the 2026 hold-out stayed closed.
| trial | DEV 2022-24 net pts | PF | evening t | win | VAL 2025 net pts | PF | evening t | win |
|---|---|---|---|---|---|---|---|---|
| I1 flipped, TP 38 / SL 25 | -3,442 (1,525 trades) | 0.79 | -3.85 | 34.0% | -1,795 (795) | 0.83 | -2.50 | 35.7% |
| I2 flipped, TP 25 / SL 38 (exact mirror) | -2,299 (1,558) | 0.86 | -2.61 | 43.8% | -2,076 (803) | 0.81 | -2.77 | 48.3% |
Verdict: both inversions fail. Reading: the flipped strategy loses the same as the original (I1 DEV -3,442 vs T1 -3,514 points), which is the signature of a signal with no directional information: whichever way you trade, the 2 points of spread and slippage a trade (about 4 points a night at 1.9 trades) are paid. There is nothing to invert; the cost is the whole result. No MT5 broker replay, no hold-out, no EA.

