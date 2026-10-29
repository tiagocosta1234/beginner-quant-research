# BRK_PATTERNS result - classic chart-pattern breakouts: 0 of 15 pass

Run 2026-10-16 18:08-18:13 local (local clock; file save times), second PC PC-2. Pre-registration `PREREG_BRK_PATTERNS.md`
(frozen 18:07:40 before the run; sha256 ecd68c81... prereg / 05ea53f9... engine, recorded in
`data\scratch\brk_patterns_freeze.txt`; not committed first because GitNexus cannot be installed on this ARM second PC,
see below). Engine `brk_patterns.py`; output `BRK_PATTERNS_OUTPUT.txt` (final), `BRK_PATTERNS_OUTPUT_run1_bugged.txt`
(first run, two bugs, kept for the record). Data: MT5 broker M1 bid/ask for 46 markets, 2021-12-01..2026-10-16, pulled read-only
from the second PC's MT5 broker terminal (`forex/ea_batch/mt5data_m1_export_laptop.py`). 107,627 trades. HOLD 2026 stays sealed.

## Verdict
**No chart pattern passes.** 14 of 15 trials lose money in DEV after costs; the two with a positive DEV mean (DARVAS H4
+0.042 R, HI52 D1 +0.022 R) have t +1.03 and +0.17 against the required 2.71, and both lose in VAL 2025
(-0.179 and -0.056 R). The pattern information over a random entry with the same stop / target / time stop is between
-0.06 and +0.07 R in every trial; the largest (DARVAS H4 +0.072 R, t 2.20) disappears in VAL (real -0.179 vs control -0.070).

| trial | DEV n | DEV net R | t | control | pattern info (t) | DEV years | VAL n | VAL net R |
|---|---|---|---|---|---|---|---|---|
| TRI_SYM H1 | 6927 | -0.197 | -6.44 | -0.232 | +0.035 (+1.16) | -0.08/-0.24/-0.27 | 2394 | -0.184 |
| TRI_SYM H4 | 1845 | -0.094 | -1.91 | -0.116 | +0.022 (+0.45) | -0.08/-0.20/+0.00 | 671 | -0.056 |
| TRI_FLAT H1 | 2939 | -0.229 | -7.27 | -0.211 | -0.017 (-0.53) | -0.18/-0.32/-0.19 | 977 | -0.203 |
| TRI_FLAT H4 | 830 | -0.021 | -0.26 | -0.077 | +0.056 (+0.73) | +0.22/-0.12/-0.15 | 272 | -0.201 |
| WEDGE H1 | 12594 | -0.145 | -8.84 | -0.139 | -0.006 (-0.44) | -0.11/-0.19/-0.13 | 4213 | -0.070 |
| WEDGE H4 | 3814 | -0.063 | -2.16 | -0.076 | +0.012 (+0.50) | -0.01/-0.12/-0.07 | 1242 | -0.050 |
| TLINE H1 | 12486 | -0.171 | -6.03 | -0.196 | +0.025 (+0.98) | -0.15/-0.22/-0.14 | 4035 | -0.160 |
| TLINE H4 | 4020 | -0.074 | -1.77 | -0.105 | +0.031 (+0.87) | -0.16/-0.11/+0.05 | 1319 | -0.073 |
| HS H1 | 2979 | -0.235 | -7.85 | -0.210 | -0.025 (-0.89) | -0.13/-0.41/-0.15 | 1005 | -0.130 |
| HS H4 | 774 | -0.136 | -2.35 | -0.078 | -0.058 (-1.07) | -0.17/-0.08/-0.15 | 284 | +0.047 |
| DARVAS H1 | 10815 | -0.117 | -4.28 | -0.139 | +0.022 (+1.12) | -0.09/-0.22/-0.02 | 3370 | -0.148 |
| DARVAS H4 | 3481 | +0.042 | +1.03 | -0.030 | +0.072 (+2.20) | +0.08/+0.02/+0.03 | 1161 | -0.179 |
| VCP H1 | 2080 | -0.181 | -2.42 | -0.173 | -0.008 (-0.12) | -0.10/-0.29/-0.14 | 676 | -0.162 |
| VCP H4 | 493 | -0.021 | -0.19 | -0.054 | +0.033 (+0.35) | -0.01/-0.22/+0.17 | 168 | -0.266 |
| HI52 D1 | 323 | +0.022 | +0.17 | +0.212 | -0.190 (-1.81) | -0.47/+0.01/+0.07 (2022 = Dec only) | 181 | -0.056 |

Bars: DEV n >= 200, net > 0, t >= 2.71 (Bonferroni, 15 trials), info > 0 with t >= 2.0, >= 2 positive DEV years.

## What it says (in line with `BREAKOUT_KNOWLEDGE.md`)
1. **Same story as the session breakouts, one timeframe up.** The pattern carries +0.02..+0.07 R of information over a
   random entry in most trials (about the +0.03..+0.05 R the anatomy round measured), and it is smaller than the cost.
   H&S and flat triangles carry none or a negative amount.
2. **Wider stops help, but only to zero.** By width in spreads (DEV + VAL): 3 spreads -0.456 R, 13 -0.093, 27 -0.084,
   54 -0.027, 161 -0.011; the random control follows the same curve (-0.410 / -0.156 / -0.104 / -0.058 / -0.017). Cost
   per R falls with width; the pattern adds nothing once costs are small. Fact 6 again: wide is necessary, not sufficient.
3. **HI52 is drift, not breakout.** 74% of its trades are longs; the random-entry control at the same side and 2-ATR
   stop earns +0.212 R (DEV) and +0.319 R (VAL), more than the 52-week breakouts (+0.022 / -0.056); its longs alone:
   real +0.166 vs control +0.325 (DEV + VAL). Buying a 52-week high is worse than buying at a random time in the same
   rising markets. That drift is what D2 already holds.
4. **By class (DEV + VAL): metals are positive in 6 of 7 H4 trials (+0.15..+0.48 R; WEDGE H4 -0.19) and HI52 metals
   +0.96; crypto loses in 13 of 15 trials (down to -0.44 R; spreads 15-70 bp).** The metal numbers are 2 markets in a
   gold/silver bull run, picked out after the fact: not a lead without a new pre-registration measured against the
   long-only drift yardstick.
5. Longs beat shorts in all 7 H4 patterns (e.g. VCP H4 long +0.207 vs short -0.381): the 2022-26 long drift; the
   random control shows the same tilt in most of them (VCP H4 control long +0.031 vs short -0.176).

## Bugs found and fixed (amendment 2, after run 1, before the final run)
- Amendment 1's zero-spread rule produced NaN spreads for crypto from 2021-12 to 2022-03, when MT5 broker's feed has spread 0
  on 100% of crypto minutes: NaN comparisons silently disable stops. Fix: such months take the next month's median
  (cost only); the engine now asserts finite spreads.
- The random-entry control entered at the first minute of each drawn bar and dropped bars starting in the rollover
  window: every D1 bar (00:00 server), so HI52's control came from a biased handful of days and run 1 printed an
  inconsistent "info +0.278" (real +0.040, control +0.148). Fix: enter at the first minute outside the window.
- Run 1 and run 2 agree on every verdict (0/15, same signs); only HI52's information figure changed materially.
  Run 1 is kept in `BRK_PATTERNS_OUTPUT_run1_bugged.txt`.

## Also found this round (matters for every earlier round)
- **The MT5 broker MT5 M1 spread field is 0 on many minutes:** EURUSD 35% of minutes 2022-26 (70-85% in early 2022), AUDUSD 31%,
  NZDCHF 19%, USDJPY 15%, USDCAD 12%, USDCHF 9%, and 100% of crypto minutes until 2022-03. Every earlier round that used
  `forex/data_mt5/*_M1_rates.parquet` (ask = bid + bar spread) filled those minutes at no cost. That is part of the known
  ~0.03 R bar-vs-tick optimism; it makes the earlier negatives conservative in the right direction (the truth is worse),
  but any earlier positive on those pairs (the USDJPY London-open lead included) should be re-checked with the
  zero-spread rule or on ticks.

## Process notes
- GitNexus could not be bootstrapped on this second PC (npm 11 `npx` crash; `npm install gitnexus` fails building
  `@ladybugdb/core`, no Windows ARM64 binary), so `detect-changes` cannot run here and nothing was committed. All
  changes are new files (`brk_patterns.py`, `mt5data_m1_export_laptop.py`, the prereg / result / output files, 46 data
  files); no existing function was edited.
- The data pull opened a second session on account <acct> (the trader's OK 17:10); the terminal log shows 0 positions,
  0 orders, Algo Trading off; closed cleanly at 18:00.

## In the account's environment (standing rule from 2026-10-16)
No MT5 broker replay was needed to decide this round: 14 of 15 trials have a negative mean after costs and the other two lose
in 2025, and with a negative expectancy the only absorbing state the account can reach from 95,472 is the 92,000 floor
(how fast depends only on size). For scale: the least-bad trial, Darvas H4, has a 2025 mean of -0.18 R a trade; at
$150 a trade that is -$27 a trade on average against a $3,472 buffer. The USDJPY London lead, which does have a positive
bar expectancy, was put through the full account replay the same evening (`USDJPY_ACCOUNT_ENV_RESULT.md`): it cannot
pass either.

## Window
Chart-pattern family: 15 of 40 variants used; family closed.
