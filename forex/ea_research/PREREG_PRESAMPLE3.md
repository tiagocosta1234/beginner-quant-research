# Pre-registration PRESAMPLE3 (breakout day, round 35; written 2026-10-15 14:23 local, local clock, BEFORE downloading the data)
Post hoc hypothesis from PRESAMPLE / PRESAMPLE2: the London-open breakout works on the YEN (USDJPY passed out of time, CADJPY nearly), not on the dollar majors. Test it on the five JPY crosses not yet used out of time: EURJPY, GBPJPY, AUDJPY, NZDJPY, CHFJPY.
Rule: identical to PRESAMPLE L1 (box 08:00-08:30 London bid high/low, one-cancels-other stop orders until 11:00, stop at the other side, hold to 17:00 London; R >= 2 spreads).
Data: HistData.com 1-minute bid, 2020-01-02 .. 2021-11-30 (EST without DST -> UTC +5 h). Cost, stricter than before: ask = bid + MT5 broker's CURRENT median spread of the cross in 08:00-17:00 London (2025-10-01 .. 2026-10-02 MT5 broker M1 data).
Cell (one): J1 the five crosses pooled, daily mean R. Gate (one look): daily mean > 0 with Newey-West t >= 1.96 AND positive in 2020 and in 2021. Reported: each cross, random control, and the book with USDJPY + CADJPY at today's spreads.
Honest prior: about 20%.
