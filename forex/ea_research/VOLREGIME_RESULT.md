# VOLREGIME_RESULT - volatility-regime filter on opening-range breakouts and fades (2026-10-16, local clock ~10:05 local)
Pre-registration `PREREG_VOLREGIME.md` (commit 323480e1, 09:54, before any filtered P&L); code `volregime.py`; output
`VOLREGIME_OUTPUT.txt`; cell table `data/scratch/volregime_cells.csv`. 184 streams (46 MT5 broker x London/NY x breakout/fade),
112,201 stream-days, DEV 2021-12..2024-12, VAL 2025-01..2026-10-02, MT5 broker M1 bid/ask, 1-minute bars (real-tick cost not included).

## Verdict: no edge; 0 of 4 pooled tests and 0 of 1,104 cells pass
1. **Pooled effect**: in every stream/measure the HIGH-volatility tercile is the least bad, in DEV and in VAL (breakout V1: -0.080 DEV,
   -0.037 VAL; V2: -0.065, -0.059; fades -0.11..-0.14), but every tercile is negative with clustered t <= -2.3. The consistent
   ordering is a cost effect (a wider box makes the fixed spread a smaller share of 1 R), not a tradeable edge. 0 of 4 pass.
2. **Cells**: 0 DEV passes at t >= 3.9; best DEV t 3.03 (USDJPY NY breakout, mid V1: +0.331 DEV -> +0.034 VAL). 16 cells had
   DEV t >= 2 against ~25 expected by chance; their VAL mean +0.027 R (62% positive) - noise-sized, below real-tick cost.
3. **Flagships** (reported, not selected): USDJPY London breakout is positive in most terciles of both periods (V1 low/mid
   +0.12..+0.27, high -0.02/+0.08), so the filter does not sharpen it. EURJPY London fade, V2 LOW tercile: +0.150 DEV (182) /
   +0.258 VAL (236), the most consistent single line in the table; it is one of 1,104 cells, does not reach the DEV bar (t well
   below 3.9), and EURJPY was named after looking at its 2026 result today: a lead to pre-register on 2020-21 HistData, not an edge.

the trader's question answered: a volatility-regime filter does not turn session-open breakouts or fades into an edge on MT5 broker data.
Also run today (descriptive, scratch, not in the ledger): breakout management (targets/BE/trailing/partials: plain hold-to-close
best), NY-open screen of 46 markets (best USDJPY/SP/NSDQ +0.10 R, ~0 in 2025-26), fades (2-4 of 46 positive), follow-recent-
winners walk-forward (next month negative in all 12 variants), random-data search demo (22 rules >0.99 R in DEV, none after).
