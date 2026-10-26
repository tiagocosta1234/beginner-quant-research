# READ12: the 1:1 read on recent gold (training log; frozen with `python read12.py freeze` before the test draw)

Base: MANUAL_READ.md lessons 1-20, READ11.md T1-T6 (T5: the first allowed candle on the 30-minute-trend side unless a hard reason; T6: no trade when X is under 1.2 points), and the v9 constraints. Bracket fixed by PREREG_READ12.md (1:1 at X).

## Lessons from training (R001-R040, Feb-May 2026)
- **U1 (R001, R002) On big 2026 trend days a small 30-minute dip flips the allowed side against the day.** Both trades lost; the naive 08:00 side (with the day) won both. Rule from R003: when |30-minute trend| < 1 ATR and its sign is against the move since 06:00, no trade (the 30-minute sign is noise).
- U1 record in training: on R003, R010, R021, R024, R026, R027 the read stood aside; the naive side won on R003, R010, R026 and lost on R021, R024, R027 (3 / 3), so U1 neither helped nor hurt.

**Final training score (R001-R040, 26 Oct ~00:3x local clock):**
- read12: 34 trades, 19 W, mean R +0.109, excess +0.129 (P 0.20), realised 0.98:1 (2026 brackets of 5-30 points make costs small in R).
- naive 08:00 30-minute trend: 40 trades, 25 W, mean R +0.226, excess +0.259 (P 0.044), 0.95:1. Read minus naive on the read's days: -0.177.
- always long 08:02: -0.081.
- Biggest gap: R001, R002, R006, R018, R020, R029 the naive (08:00 entry, 08:00 trend sign) won where the read (08:02+ entry, later trend sign) lost. On 2026 volatility a few minutes and the sign of a noisy 30-minute window decide the trade.
