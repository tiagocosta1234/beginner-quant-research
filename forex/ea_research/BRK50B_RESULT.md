# BRK50B result - 50 more breakout ideas on gold and Nasdaq: 0 pass

Run 2026-10-18 17:31 local (local clock, second PC PC-2). Pre-registration `PREREG_BRK50B.md` (registered 17:27; SHA-256
a5e81f3b70bd7bc37b8c1c9eedab891d3f7b57b96a4eebd6aa2aac49d9125cfe recorded in `data\scratch\brk50b_prereg.sha256` before any
P&L, because the trader asked for no more commits on 18 Oct), engine `brk50b.py` (BRK50's `Mkt` engine), dry run `BRK50B_DRYRUN.txt`
(truncation identical on NSDQ and XAUUSD), output `BRK50B_OUTPUT.txt`, table `BRK50B_SUMMARY.csv`, 50 ledger rows.
Bars per idea: DEV 2022-24 n >= 100, mean > 0 with t >= 3.09 (Bonferroni for 50), >= 2 of 3 years positive, direction information
over the mirror trade t >= 2.0; then VAL 2025 t >= 1.65; out of time and the 2026 hold-out only for passers.

## Verdict: 0 of 50; the 2026 hold-out stays sealed; nothing reached the out-of-time stage
- DEV t-values: mean +0.50, SD 1.32; 34 of 50 positive; 6 above t 1.65 (about 2.5 expected by luck); 1 above 3.09 (J17, on 3
  trades: its ER > 0.4 morning filter almost never fires, so it fails n >= 100).
- The mild positive tilt is mostly one shared ingredient: about half the ideas trade the Nasdaq New York box, which earned about
  +0.1 R in 2022-25 on MT5 broker and failed its 2020-21 out-of-time check (BREAKOUT_KNOWLEDGE section 2). Those ideas are not independent.

## The closest ideas (all fail)
| idea | DEV 2022-24 | info over mirror (t) | years | VAL 2025 | why it fails |
|---|---|---|---|---|---|
| J01 PDH/PDL held through Europe, broken in New York | +0.133 R (t 2.96), n 368 | +0.231 (2.97) | +0.24 / +0.18 / -0.01 | +0.117 (t 1.55) | DEV t below 3.09; VAL t below 1.65 |
| J36 Nasdaq box in the direction of the Nikkei session | +0.156 (t 2.18), n 391 | +0.306 (2.55) | +0.21 / +0.13 / +0.14 | +0.057 (t 0.44) | DEV t; VAL |
| J16 unfilled-gap session break | +0.150 (t 2.11), n 446 | +0.306 (2.49) | +0.13 / +0.02 / +0.27 | +0.026 | DEV t; VAL |
| J04 reversal break after three lower highs / higher lows | +0.157 (t 1.97), n 164 | +0.293 (2.16) | +0.08 / +0.16 / +0.23 | -0.095 | DEV t; VAL negative |
| J49 failed-breakout day, opposite break next day | +0.115 (t 1.97), n 280 | +0.202 (1.93) | +0.20 / +0.11 / +0.04 | +0.024 | DEV t |
| J27 VIX close change sets the Nasdaq box side | +0.186 (t 1.45), n 120 | +0.440 (2.26) | -0.07 / +0.29 / +0.33 | **-0.369 (t -3.07)** | reversed in 2025 |
Gold alone is weaker than Nasdaq almost everywhere: of the ideas trading both, the Nasdaq leg is the better one in 2022-24 in most
cases (J01 +0.19 vs +0.05, J16 +0.21 vs +0.11, J14 +0.19 vs -0.06).

## Account view (2022-25 trades, from 95,472, MT5 broker rules)
Best rows: J16 at $500 a trade 0.1% pass / 22% breach by 22 Dec, 14.2% / 42% by 30 Jun 2027; J36 at $500 10.0% / 32% by June 2027;
J01 at $500 1.7% / 4%. Nothing passes before it breaches.

## Reading
Fifty more fixed rules on gold and the Nasdaq, about half using information outside the chart (Nikkei, DAX, USDJPY, BTC, oil,
copper, silver, VIX, 10-year notes, CME volume, FOMC and release calendars), give the distribution that noise plus the 2022-25
Nasdaq drift would give. J01 is the most consistent shape, positive in 2022, 2023 and 2025 and flat in 2024, but at t 2.96 / 1.55
it does not clear the bars, and the 2026 hold-out is not spent on it.
