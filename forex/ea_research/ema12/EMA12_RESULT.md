# EMA12 result: the mechanical 12 EMA session-open rule has no edge on MT5 broker gold or Nasdaq (0 of 32), 2026-10-19

Pre-registration `PREREG_EMA12.md` (+ amendment 1 before any P&L; sha256 f1ba67b9..., commit 0ae6ed12, 11:32 local clock). Engine `ema12_test.py`, output `EMA12_OUTPUT.txt`, table `EMA12_TRIALS.csv`.
MT5 broker M1 bid/ask, 2022-2025 (2026 hold-out sealed, not computed). Dry-run: 0 mismatches in 640 sessions recomputed with the future cut.

## Verdict
**0 of 32 trials pass** (2 markets x London/NY x 2 stops x r 0.525/1.0 x filter F0 first-cross / F30 cross in the direction of the previous 30-minute move).
DEV 2022-24 mean R is negative in 31 of 32 trials (-0.02 to -0.14 R a trade, 580-700 trades each; the best is +0.001); win rate 58-64% at r 0.525 (the break-even is 66%),
44-50% at r 1.0. VAL 2025 is negative in 30 of 32. Gold London and NSDQ London are the worst (-0.08 to -0.14), the cost of one spread per trade is the same order as the whole result.

## Does the rule reproduce the trader's trades? No
- Dry-run: the first-cross rule fires on 28 of his 30 gold session-days but in his direction on only 14 (coin flip). His direction agrees with the move over the previous 30 minutes on 23 of 30
  (against it 11 of 30): momentum, not "first cross". (`infer_rule.py`, `infer_direction.py`.)
- Over his own four weeks (2025-04-14..05-12) the mechanical rule earned -0.15 R (F0, 36 trades) and -0.05 R (F30, 32 trades) against his +0.22 R on MT5 broker prices
  (24/30 wins), and about the same as the rest of 2025 (-0.10 / -0.12): that month was not unusually good for the rule. Only F30 gold London in that window shows +0.22 R (15 trades, 80% wins),
  and F30 NY there shows -0.28: noise at n = 15 (`window_check.py`, exploratory).
So whatever produced his +0.22 R is NOT the rule written here: it is either his selection of setups (which the 30 trades cannot separate from luck: t 1.93) or chance.

## What this does and does not say
It says a mechanical "cross of the 1-minute EMA12 in the first 15 minutes after the open, with a stop of 2.5 x ATR or the 15-minute swing and a 0.5-1 R target" loses its spread on gold and Nasdaq 2022-25.
It does not say his discretionary trades have no edge: they remain 30 trades of one month (t 1.93) plus one live trade on 2026-10-19 (Short London, +0.53 R, logged in Notion). Next evidence is forward only:
keep logging every session in Notion with entry, stop, target and the reason for skipping; at 100+ forward trades compare with this -0.08 R baseline.

## Addendum 2026-10-19 (afternoon): does his DIRECTION beat chance? Yes on the 30 trades, and no simple rule reproduces it (`direction_skill.py`, `infer_context.py`; descriptive, not pre-registered)
Same entry minute, same USD stop and target distances, MT5 broker bid/ask, 30 dated gold trades (14 Apr-12 May 2025):
| direction at his entry minutes | mean R | wins |
|---|---|---|
| his own | **+0.219** | 24/30 |
| the mirror trade (opposite side) | -0.439 | 11/30 |
| random side (200k draws) | -0.110 (5-95%: -0.34..+0.12) | about 18 |
| random side keeping his 11 long / 19 short | -0.077 | |
| always long / always short | -0.238 / +0.017 | |
| momentum of the previous 30 min | -0.036 | 19/30 |
| momentum since the session open | -0.034 | 19/30 |
| price vs the mean of the last 12 minutes | -0.135 | 17/30 |
P(random side >= his +0.219) = 0.7% (1.2% keeping his long/short split); sign test on the 25 trades where the two sides differ: his side wins 19, the mirror 6 (p 0.007).
ICT-style context does not explain his side either (`infer_context.py`): following the daily-open bias 19/30, fading or following Asian-range and previous-day-high/low sweeps 5-12 of 11-21 applicable, i.e. chance.
Reading: on these 30 trades the choice of side beats a coin flip (about 2.5 sigma), and the 8 trades where a momentum rule disagrees with him are where his edge sits; the
rules tried here give -0.04 to -0.14 R at the same minutes. What cannot be separated from the data: (a) skill, (b) hindsight in FX Replay (entry timing after seeing the move develop),
(c) luck over 20 trading days (same-day trades are correlated). Forward evidence is the way: log before entering (side, reason, time) and compare with the mirror trade on MT5 broker data afterwards.
