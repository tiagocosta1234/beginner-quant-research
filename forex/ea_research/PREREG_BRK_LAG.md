# Pre-registration BRK-LAG (breakout day, round 31; written 2026-10-15 14:05 local, local clock, before any code or result)
Question: when most of a group of related markets has broken out of its opening box in the same direction, does the member that has NOT moved yet catch up (laggard entry)? Round 12 tested the opposite (a breakout confirmed by its partner); this round buys the market that is still inside its box.
Groups (same session clock, round-1 sessions, member sign = its direction for the group's common move):
US indices SP, NSDQ, DOW (+1 each; NY 09:30); USD-weak FX EURUSD, GBPUSD, AUDUSD, NZDUSD (+1), USDCHF, USDCAD, USDJPY (-1) (London 08:00); JPY-weak EURJPY, GBPJPY, AUDJPY, CADJPY, CHFJPY, NZDJPY, USDJPY (+1) (London); metals XAUUSD, XAGUSD; energy BRENT, WTI (NY 09:00); crypto BTC, ETH, SOL, XRP, ADA, LTC, BCH, BNB (NY 09:30).
Each member's box = bid high / low of the first 30 minutes of its session; a member's breakout = its first stop-order fill in the 3 hours after the box (round 1). Quorum: at least max(1, ceil((n-1)/2)) OTHER members have broken out in the same group direction.
- **Z1 laggard entry:** at the first minute the quorum is met while member m has not broken out yet, enter m at the next minute's open (market, ask / bid) in the group direction; stop one box width away (R = m's box, >= 2 spreads); hold to the session close (capped 22:55 server); no entry in server hours 23 / 0; one entry per member and day.
Control: the same member and minute, random side, same R and exit. Reported by group.
Gates (DEV 2022-24, VAL 2025, 2026 non-clean): 1. DEV mean >= +0.05 R and t >= 1.96 (daily NW lag 1, one cell). 2. VAL mean > 0 and t >= 1.65. 3. Beats its control by >= 0.05 R in DEV and VAL.
Honest prior: about 5%.
