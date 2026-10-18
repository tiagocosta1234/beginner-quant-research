# UJ_C3C5_OOT result - both USDJPY confluences fail on the 2026 hold-out, and reverse (not confirmed)

Run 2026-10-17 23:56 local (local clock, second PC). Pre-registration `PREREG_UJ_C3C5_OOT.md` (registered 23:56; frozen by sha256 at
23:56:26 together with the unchanged `uj_conf.py`, `C:\work\scratch\uj_c3c5_freeze.txt`). Engine `uj_c3c5_oot.py`, output
`UJ_C3C5_OOT_OUTPUT.txt`. Part A (2026 hold-out, 2026-01-01..2026-10-16) run; part B (2020-21 HistData, main PC) is now moot for the
verdict, because a rule needed to pass both.

| rule | 2022-24 with / without | 2025 with / without | **2026 with / without** | 2026 t | part A |
|---|---|---|---|---|---|
| UJ + C3 risk-on alignment | +0.239 / -0.027 | +0.222 / -0.013 | **-0.043 / +0.304** (n 112 / 89) | -0.25 | FAIL |
| UJ + C5 FVG in the box | +0.277 / +0.014 | +0.250 / +0.036 | **-0.058 / +0.179** (n 58 / 143) | -0.28 | FAIL |
Base 2026 (already known): 201 trades, +0.111 R.

## Reading
- Both effects flip sign on the data they had never seen: in 2026 the flagged trades lose and the unflagged ones carry the
  base. Two years of agreement (2022-24 and 2025) was not enough: with trades from -1 R to +8 R, a 0.25 R gap between two
  halves of a few hundred trades appears and disappears by chance.
- Not confirmed; the USDJPY London breakout stays as it was: about +0.10 R a trade at today's spread on the bars, about zero
  on real ticks last year. The 2026 hold-out of these two rules is spent.
- Lesson for future rounds: a confluence that "repeats in validation" at t ~1.5 is still most likely noise; only an untouched
  period settles it, and it settled it here.

## Account environment (information only; 2022-26 trades, from 95,472, MT5 broker rules; pass% / breach% by 30 Jun 2027)
base $250: 8.8 / 47 (bars), 4.3 / 61 (with the 0.06 R tick haircut); the two subsets look better in-sample (e.g. UJ+C5 $250:
0.5 / 11) only because 2022-25 is where they were found. With the verdict negative, none of them is usable.
