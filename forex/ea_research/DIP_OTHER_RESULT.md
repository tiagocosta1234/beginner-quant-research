# Family DD result: the frozen ManualDip rule on metals, energy and FX majors (2026-10-12)

Pre-registration: PREREG_DIP_OTHER.md. Same rule, same 15:49 New York clock for every asset. Unit = decision day, per-trade return in bp (ask in, bid out).

| Group | DEV 2022-24 (days, bp, t) | VAL 2025 (days, bp, t) | Accepted |
|---|---|---|---|
| DD1 metals (XAU, XAG) | 52, -6.3, -0.42 | 15, +31.9, 0.69 | no |
| DD2 energy (WTI, BRENT) | 62, **+51.7**, 1.78 | 14, **-46.9**, -0.56 | no (VAL negative) |
| DD3 FX majors (7) | 176, -1.1, -0.27 | 52, +6.4, 0.87 | no |
| control: the 4 indices | 68, +8.8, 0.58 | 28, +56.4, 1.48 | n/a |

## Verdict: no group passes, 2026 not opened.
Metals and FX have no dip reversal. Energy passes DEV (t 1.78) and then loses in 2025; with 14 VAL days that is not strong evidence either way, but the registered rule says no.

## Honest note on ManualDip itself
The control reproduces the machinery and exposes how thin ManualDip's own evidence is: on the 2022-24 DEV years alone the four indices average +8.8 bp per signal day (t 0.58); the pooled 2022-26 figure (+32 bp, 209 trades, DA2) leans on 2025-26 (+54 and +52 bp) while 2023 was negative. It is "real and uncorrelated" by the earlier verdict (1990-2017 data agree), but small and noisy, which is why it was sized at only 500 USD of day risk. Nothing changes live; the live log is its clean sample.
