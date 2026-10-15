# PREREG_D2PLUS - four refinements of the D2 swap-free drift book from the trader's 50-hypothesis list (written 2026-10-15 local clock 19:00, before any P&L)
Source: the trader's pasted list, items 41, 42, 43, 47 (44 / 45 / 48 / 49 are sizing-only, already D2's band, intraday-only or undefined; 46 = XS_MOM_IDX, failed).

## Base
D2 exactly as in swapfree_drift.py (SP, NSDQ, DAX, NIKKEI, XAUUSD; inverse 60-day-vol weights; held only above the 200-day SMA; Monday 18:00 server decisions; 25% no-trade band; MT5 broker M1 bid/ask 2022+, HistData 2020-21 with MT5 broker spreads, DAX out of the HistData period per Amendment 1).

## Variants (one fixed rule each, no parameter search)
- P41 BREADTH: as D2, but the whole book is flat when fewer than 3 of the 5 markets are above their 200-day SMA.
- P42 CORR: weights proportional to 1 / (vol x (1 + mean 60-day correlation with the other four markets)), normalised; trend filter as D2.
- P43 DOWNVOL: weights inverse to the 60-day downside semi-deviation instead of the full volatility; trend filter as D2.
- P47 HYST: a market switches on when its close is > 1.01 x SMA200 and off when it is < 0.99 x SMA200 (state carried week to week); weights as D2.

## Tests (periods: DEV 2022-24, VAL 2025, OOT 2020-21; the 2026 HOLD was spent on D2 and is reported for context only)
A variant counts as an improvement only if (a) its DEV+VAL t >= 2.50 (D2's bar 2.24 tightened for 4 variants), (b) its OOT mean > 0, and (c) the paired daily difference variant - D2 over DEV+VAL+OOT has mean > 0 with t >= 2.24 (one-sided 5% / 4). Otherwise D2 stays as it is.

## Honest prior
The variants change weights or the on/off rule of a five-market book; daily P&L will correlate > 0.9 with D2, so a difference t of 2.24 is unlikely. Expected: no improvement.
