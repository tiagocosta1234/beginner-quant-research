# HWR result - high win rate and small daily wins are achievable; a profit that passes MT5 broker is not (0 of 3 pass)

Run 2026-10-18 00:07 local (local clock, second PC). Pre-registration `PREREG_HWR.md` (registered 00:06; frozen by sha256 at 00:07:25 in
`C:\work\scratch\hwr_freeze.txt`). Engine `hwr.py`, output `HWR_OUTPUT.txt`, trades `C:\work\scratch\hwr_*.parquet`. Six indices
(SP NSDQ DOW DAX NIKKEI ASX), MT5 broker M1 bid/ask, long only, stop 3 daily SD, R = P&L / risk to the stop. HOLD 2026 sealed.

## Trials
| trial | DEV 2022-24: n, R (t) | win | avg win / avg loss | DEV years | VAL 2025: n, R (t), win |
|---|---|---|---|---|---|
| DIP6 (dip rule on 6 indices, 1-day hold) | 89, +0.056 (0.80) | 54% | +0.37 / -0.31 | -0.10 / +0.14 / +0.18 | 32, -0.014 (-0.07), 44% |
| DIP6-TP (+1 SD target, up to 3 days) | 87, +0.026 (0.34) | 70% | +0.33 / -0.69 | -0.09 / +0.08 / +0.10 | 32, -0.139 (-0.94), 62% |
| CONNORS-RSI2 (above SMA200, RSI2 < 10, exit above SMA5) | 138, +0.122 (2.14) | **72%** | +0.44 / -0.68 | **+0.11 / +0.12 / +0.13** | 52, -0.038 (-0.30), 62% |
None passes DEV (t >= 2.4). CONNORS-RSI2 is the closest to the request: 72% wins, positive in all three DEV years, but t 2.14 and
negative in 2025. The target in DIP6-TP raises the win rate from 54% to 70% and lowers the result: the geometry buys win rate
with expectancy, as expected.

## MT5 broker fit (2022-25)
- Small daily wins: yes. Winning days 58-67% of trading days; at $500 a trade 0.0-1.3% of days exceed $2,000 (the cap is no
  longer the problem).
- Passing: no. Back-to-back fresh evaluations 2022-25: 0 passes at $250 and $500 for all three; at $1,000 CONNORS 2 passes vs 46
  breaches. From the live balance (95,472) by 30 Jun 2027: 0.0-0.5% pass at every size; breach 0.1-0.6% at $250, 33-75% at
  $500, 64-97% at $1,000.
- Why the breaches: dip signals cluster (up to 5 indices on the same decision day, up to 6 positions open at once), so a
  sell-off stacks the floating loss to -2,800-2,900 at $500 a trade, past the -2,500 daily line. With one position at a time
  across all markets (descriptive, not registered) breach falls to 0.1-0.5% at $500, but the pass chance stays 0%: about 15-20
  trades a year at +0.03..+0.06 R x $500 is $300-600 a year against $12,528 needed.

## Reading for the trader
A strategy with a ~70% win rate and small daily wins exists in the data (CONNORS-RSI2 on indices), and it is not a way to
pass MT5 broker: its edge is small (+0.08 R a trade 2022-25), it fires about 50 times a year across six indices, and its trades bunch on
the same sell-off days. The one validated route that produces SMALL, FREQUENT, REALISED wins with a real edge is still the D2
drift book with a profit skim (`D2_MT5RULE_RESULT.md`: about 30% by Mar 2027, 50-60% by Jun 2027, 2-4% breach at 100k gross;
needs MT5 broker's written OK for a next-day re-entry after a profit close).
