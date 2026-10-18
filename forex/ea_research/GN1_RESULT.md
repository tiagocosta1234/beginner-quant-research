# GN1 result - gold and Nasdaq long-only breakouts in the 200-day uptrend: 0 of 5 pass (2026-10-18 10:52 local, local clock, second PC)

Pre-registration `PREREG_GN1.md` (committed 887de6d8), engine `gn1.py` and dry run `GN1_DRYRUN.txt` (committed 42d322c5 before any
P&L), output `GN1_OUTPUT.txt`. MT5 broker M1 bid/ask, zero-spread minutes repaired; the regime (previous close above its SMA200) is on
71-72% of days since 2022. R = net P&L / (entry - stop); "control" = a random long in the same entry window, same stop distance,
same exit, 5 draws on every regime day.

| trial | DEV n | DEV mean R (t) | win | control (all regime days) | DEV years 22/23/24 | VAL 2025 mean R (t) | VAL control | verdict |
|---|---|---|---|---|---|---|---|---|
| G1 gold London, exit 17:00 | 355 | -0.090 (-0.77) | 20% | +0.011 | -0.31/-0.23/+0.03 | +0.250 (+1.31) | +0.093 | FAIL |
| G2 gold London, held to next day | 355 | +0.115 (+0.67) | 14% | +0.105 | -0.35/-0.05/+0.26 | +0.442 (+1.62) | +0.342 | FAIL |
| G3 gold New York | 315 | +0.088 (+1.09) | 43% | +0.042 | -0.41/+0.17/+0.05 | +0.192 (+1.85) | +0.071 | FAIL |
| N1 Nasdaq New York | 302 | +0.132 (+1.76) | 49% | +0.010 | +0.20/+0.07 (no 2022 trades) | +0.053 (+0.48) | -0.054 | FAIL |
| N2 Nasdaq New York, held to next day | 302 | +0.224 (+2.07) | 37% | +0.127 | +0.27/+0.18 | +0.087 (+0.61) | -0.095 | FAIL |

No trial reaches the DEV bar (t >= 2.33); the 2026 hold-out stays sealed for all five.

## What it says
- **In an uptrend, gold and Nasdaq long breakouts make money, and so does a random long.** Every control is >= 0 in DEV; the gold
  controls are +0.07..+0.34 R in 2025. The breakout's edge over the random long on all regime days is -0.10 (G1), +0.01 (G2),
  +0.05 (G3), +0.12 (N1), +0.10 (N2) R in DEV, and +0.16 / +0.10 / +0.12 / +0.11 / +0.18 R in 2025: about one spread to a tenth
  of a stop, the same size earlier rounds found, and not significant.
- **Design flaw in the registered "information" measure (reported, not used to change any verdict):** pairing the control with
  the breakout by day restricts it to days on which price later broke the box high, so the random entries before the break
  know the day goes up. That made the paired information negative (-0.03..-0.15 R). The fair yardstick is the unconditional
  control in the table above. The verdict does not depend on it: every trial already fails the DEV mean bar.
- **Holding into the next day (G2, N2) raises the mean by +0.1..+0.2 R and the control by the same amount**: overnight drift, not
  breakout. Nasdaq has no 2022 trades because it was below its 200-day average most of that year; the regime gate keeps the
  sample to 2023-24 in DEV.

## Account environment (2022-25 trades, from 95,472, MT5 broker rules, 5-day block bootstrap, pass% / breach%)
Best rows: N2 at $500 a trade 0.2/17 by 30 Nov, 0.9/26 by 22 Dec, 19.3/49 by 30 Jun 2027; G2+N2 at $250 a trade 0.1/16,
0.4/25, 14.0/51. **Every configuration breaches more often than it passes by every horizon.** Not usable.

## Ledger
5 rows (family gn1). Running count in this research window (from 18 Oct): 5 of 40 variants.
