# EURUSD-EA1 result (2026-10-14): 24-cell search over six price-state archetypes, EURUSD only
Pre-registration `PREREG_EURUSD_EA1.md` (one amendment A1 before any P&L: S2 to Wilder RSI(2)), engine `eurusd_ea1.py`, output `EURUSD_EA1_OUTPUT.txt`. 791 Mon-Thu days 2022-03..2025-12; HOLD 2026 unread.
## Verdict: 0 survivors; the family is closed
- Placebo ceiling (500 permutations of the sign): max |t| over the 24 cells has median 2.18 and 95th percentile 3.10; the best real DEV cell is S1 fade/G1 with t +1.76 (+0.112R, 46% hit), then +0.004R (t 0.04) in 2025.
- Fades (against the daily stretch / weekly stretch / 24h move) are positive in DEV in most cells (+0.07..+0.14R) and then negative in 2025 (S5 fade G1 -0.30R, S6 fade -0.24..-0.31R, S4 fade G2 -0.32R, t -2.84): the same pattern as the FX3 fade lead, early years positive, fading to negative.
- Continuation cells are negative or zero everywhere.
- Daily-state archetypes of the kind a retail EA uses (stretch, RSI2, prior-day close location, overnight move, 24h move, weekly stretch), tested on 24-hour brackets or holds from the 10:00 server hour, contain no EURUSD edge after real bid/ask costs in 2022-25.
Nothing goes to multi_fx_ea/candidates. The pass condition for moving to the next pair has not been met, so EURUSD stays open.
