# X1: SDB entries with a 1.9% trailing exit instead of the fixed 1.9% target, MT5 broker gold: result (2026-10-09 16:07 local, 2026-10-09)

Pre-registration `PREREG_SDB_TRAIL_EXIT.md`, simulator `sdb_trail_exit.py` (entries from intraday_lab/sdb.py on MT5 broker M1 bars, no commission), output `SDB_TRAIL_EXIT_OUTPUT.txt`, ledger family sdb_trail_exit (ledger 51 of 51). The 2026 hold-out was NOT opened.
## Verdict: FAILS acceptance 1 and 2; the fixed target is at least as good; idea closed
| period | B0 frozen: trades / mean R / net R / PF | X1 trail: trades / mean R / net R / PF | common entries: paired dR / t |
|---|---|---|---|
| DEV 2022-24 | 107 / +0.140 / +15.0 / 1.33 | 103 / +0.074 / +7.7 / 1.23 | 62: +0.062 / +0.61 |
| VAL 2025 | 46 / +0.217 / +10.0 / 1.56 | 41 / +0.209 / +8.6 / 1.70 | 33: -0.103 / -0.76 |
| 2022-25 | 153 / +0.163 / +25.0 / 1.39 | 144 / +0.113 / +16.2 / 1.36 | 95: +0.005 / +0.06 |
## Reading
- The trailing exit earns LESS than the frozen exits in both periods (net R 7.7 vs 15.0 in DEV, 8.6 vs 10.0 in VAL) and the paired difference on the same entries is indistinguishable from zero (t +0.61, -0.76): letting winners run (largest +4.0 R) is paid back by trades that the 1.9% trail gives away.
- Side finding (not a trial): the frozen SDB has a small positive edge on MT5 broker data (mean +0.14 R, PF 1.33 in 2022-24; +0.22 R, PF 1.56 in 2025), the same order as the numbers behind the pair; with about 35-45 trades a year it cannot be told from luck alone (DEV t about 1.4).
