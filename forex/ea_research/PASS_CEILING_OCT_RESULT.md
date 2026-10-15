# PASS_CEILING_OCT_RESULT - the most any strategy can reach by 30 Oct 2026 (2026-10-15, local clock 20:00)
the trader's goal (/goal): "70% de chance de passar a conta este mes". Code pass_ceiling_oct.py (dynamic programming, exact on a 100-USD grid).
Model: from balance 97,700, 11 trading days (16-30 Oct), each day the trader picks the BEST possible two-outcome day: win +g (g <= 2,000, the counted cap) or lose -L (L <= 2,400, just under the 2,500 hard breach), with the win probability given by the edge (expected day result = edge x L); floor 92,000, target 108,000. This is an upper bound: a real strategy cannot shape its days into exact two-outcome bets, slippage and gaps are ignored, and all-or-nothing betting is banned by MT5 broker.
| edge per day (in units of the day's risk L) | max P(pass by 30 Oct) |
|---|---|
| 0 (no edge) | 15.0% |
| 0.05 | 20.0% |
| 0.10 | 26.3% |
| 0.20 | 44.6% |
| 0.30 | 69.0% |
Reading: 70% by 30 Oct needs an edge above 0.30 R EVERY day, sized as an all-or-nothing daily bet. The best edges found in two weeks of research are about 0 to 0.1 R (D2 about +50 USD a day on about 1,000 USD of daily risk per 100k = 0.05). The goal is not reachable by any legitimate strategy; the realistic ceiling this month is about 15-20%, and only with banned gambling-style sizing.

## Addendum (20:21): by 30 Nov 2026 (32 trading days)
Same upper-bound model: no edge 37.2%, 0.05 R a day 53.5%, 0.10 R 75.5%, 0.15 R 96.2%. 70% by 30 Nov needs about 0.09-0.10 R EVERY day in the optimal all-or-nothing day shape (banned by MT5 broker); no tested strategy has that (best about 0-0.1 R, and not in that shape). Actual D2 (MT5 broker-rule simulation, d2_nov_lookup.py, 181 starts): by 30 Nov W1 100k 0.0% pass / 0.0% breach, 150k 0.0 / 1.1, 200k 0.0 / 7.7; next-day re-entry 200k 3.3 / 19.9. The switched-off gold pair: about 18% by 30 Nov, in-sample (PAIR_FROM_TODAY_RESULT.md).
