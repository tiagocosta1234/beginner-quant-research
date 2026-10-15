# WEEKEND_GAP_RESULT - fading the weekend reopen gap (2026-10-15, local clock 15:41)
Pre-registration `PREREG_WEEKEND_GAP.md` (commit 8bbd8b4a). Code `weekend_gap.py`, output `WEEKEND_GAP_OUTPUT.txt`, rows `D:/finance/si_ledgers/WEEKEND_GAP_RUN.csv`. HOLD not opened.

## Verdict: 0 of 4; closed. Weekend gaps on MT5 broker do not fill by Monday 10:00 or 16:00 server.
| cell | OOT 2020-21 | DEV 2022-24 | VAL 2025 | DEV+VAL t (bar 2.50) |
|---|---|---|---|---|
| G1 FX majors, exit 10:00 | +1.08 bp | -0.85 | -0.29 | -0.55 |
| G2 FX majors, exit 16:00 | +3.31 | -2.01 | +4.50 | -0.20 |
| G3 indices + gold, exit 10:00 | +9.94 (38 Mondays) | -3.34 | -10.36 | -1.58 |
| G4 indices + gold, exit 16:00 | +10.03 (38 Mondays) | -4.64 | -13.21 | -1.74 |
Monday-cluster means, bp net of MT5 broker's spread (entry spread at 01:05: FX ~0.6 bp, indices / gold ~1.1-1.5 bp). The gap at 01:05 server (median 6-7 bp on FX, 18-25 bp on indices and gold) is information, not noise: on indices and gold the fade loses (the gap tends to continue), on FX it is zero. OOT on HistData has only 38 index Mondays (late HistData Sunday opens).
