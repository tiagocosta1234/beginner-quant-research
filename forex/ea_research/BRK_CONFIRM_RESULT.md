# BRK_CONFIRM result - a candle close beyond the box: fewer bounces, but worse trades (0 of 4 pass)

Run 2026-10-16 19:48-19:49 local (local clock, second PC). Pre-registration `PREREG_BRK_CONFIRM.md` (registered 19:34, amendment 1
before any P&L; frozen by sha256 at 19:48:25 in `data\scratch\brk_confirm_freeze.txt`, not committed first because GitNexus
cannot run on this second PC). Engine `brk_confirm.py`, output `BRK_CONFIRM_OUTPUT.txt`. 268,114 trades, 38 non-crypto MT5 broker, 2022-01..2026-10-16, real bid/ask with zero-spread minutes repaired. HOLD 2026 stays sealed (no trial reached it).

## Verdict
| trial | DEV n | DEV net R (t) | vs TOUCH same days (t) | DEV years | VAL net R (t) |
|---|---|---|---|---|---|
| LDN-C5 | 28,203 | -0.039 (-1.77) | -0.021 (-2.66) | +0.04 / -0.12 / -0.04 | -0.077 (-2.27) |
| LDN-C15 | 27,391 | -0.038 (-1.81) | -0.041 (-3.97) | +0.03 / -0.12 / -0.03 | -0.089 (-2.84) |
| NY-C5 | 27,902 | -0.026 (-1.68) | -0.040 (-5.02) | -0.01 / -0.03 / -0.04 | -0.021 (-0.73) |
| NY-C15 | 26,744 | -0.021 (-1.46) | -0.064 (-6.12) | +0.00 / -0.03 / -0.03 | -0.022 (-0.83) |
Yardsticks (TOUCH): LDN -0.029 (DEV) / -0.074 (VAL); NY -0.008 / -0.010. **Waiting for a 5- or 15-minute close is worse than
entering on the touch in all four trials, significantly (paired t -2.7 to -6.1), and negative in DEV and VAL.**

## What it says about "will the high / low continue or bounce?" (DEV + VAL, descriptive)
| box | entry | back inside the box within 60 min ("bounce") | win rate | +1R before -1R | R a trade | median entry delay |
|---|---|---|---|---|---|---|
| London | touch | 96.7% | 26.9% | 45.7% | -0.040 | 3 min |
| London | 5-min close | 82.7% | 30.4% | 44.3% | -0.048 | 20 min |
| London | 15-min close | 73.2% | 32.2% | 43.5% | -0.051 | 30 min |
| New York | touch | 95.6% | 39.3% | 39.8% | -0.008 | 2 min |
| New York | 5-min close | 81.6% | 42.9% | 33.4% | -0.025 | 15 min |
| New York | 15-min close | 71.0% | 44.4% | 29.6% | -0.021 | 30 min |
- **A close beyond the level does identify continuation better:** the share of breaks that come back inside the box within an
  hour falls from ~96% (touch) to ~82% (5-min close) to ~72% (15-min close), and the win rate rises by 3-5 points.
- **But the market has already paid for it.** The confirmed entry is later and further from the box (wider stop, worse
  price), so the chance of making +1R first falls and the result per trade is lower. The information in the close is real and
  already in the price by the time the candle closes.
- By class (DEV + VAL): indices are the only class around zero or slightly positive in every mode (+0.015..+0.070); energy and
  metals in London lose most; confirmation does not change which classes work. By year: 2022 is the only positive year in
  London; New York is slightly negative every year in every mode.

## Pre-registered control: flawed, reported as is
The random-timing control (same side, random minute of the window, same stop level) came out positive (+0.055..+0.153). It
uses the side the market broke to LATER, and its random minute often falls before the break, so it carries look-ahead on the
direction; it cannot be read as "random entries beat the rule". The verdict above rests only on the net result and the paired
comparison with the touch entry, which fail regardless. Future rounds: a control must not know a side chosen after its entry.

## In the account's environment (standing rule; NSDQ + XAUUSD, $250 a trade, from 95,472, MT5 broker rules; pass% / breach%, bootstrap | replay)
| box / entry | R a trade on the two markets | 22 Dec | 30 Jun 2027 |
|---|---|---|---|
| London touch | +0.058 | 1.6 / 47 \| 0.6 / 47 | 14.0 / 72 \| 3.9 / 81 |
| London 5-min close | +0.033 | 1.3 / 43 \| 0.1 / 46 | 13.7 / 69 \| 2.7 / 79 |
| London 15-min close | +0.061 | 1.5 / 37 \| 0.1 / 41 | 18.1 / 61 \| 7.9 / 67 |
| New York touch | +0.064 | 0.1 / 13 \| 0.0 / 5 | 14.5 / 30 \| 20.5 / 19 |
| New York 5-min close | +0.028 | 0.0 / 12 \| 0.0 / 5 | 2.7 / 36 \| 0.0 / 16 |
| New York 15-min close | +0.031 | 0.0 / 6 \| 0.0 / 0 | 1.4 / 25 \| 0.0 / 7 |
(Both markets traded every day, stop at the other side of the box, held to the session end.) Breach exceeds pass in every row
except the New York touch replay (20.5 vs 19 by mid-2027), which is the already-known US-index session breakout (it failed its
2020-21 out-of-time check, `BREAKOUT_KNOWLEDGE.md` section 2) on two markets picked by the trader, not something this round found.
Confirmation lowers the pass chance in New York and lowers breach mostly by trading less.

## Practical reading for the trader
- If the question is "is this break real?", a 15-minute close outside the box cuts the chance of an immediate return
  inside (within an hour) from ~96% to ~72%. That is the best "continuation detector" tested so far.
- It does not make money, because the entry after the close is worse by about as much as the information is worth. On MT5 broker
  the touch entry is (slightly) less bad. Confirmation does not rescue the breakout.

## Window
Confirmation family: 4 of 40 variants; family closed.
