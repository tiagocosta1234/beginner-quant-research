# I20_CONF result - no confluence improves the post-expansion-day fade consistently (0 of 7 kept)

Run 2026-10-17 23:29 local (local clock, second PC). Pre-registration `PREREG_I20_CONF.md` (registered 23:29, frozen by sha256 at
23:29:43 in `data\scratch\i20_conf_freeze.txt`). Engine `i20_conf.py`, output `I20_CONF_OUTPUT.txt`. In-sample by design:
I20 was chosen as the best of 54 ideas on these same 2022-25 trades (762: 564 in 2022-24, 198 in 2025). No 2026 row was read.

| confluence | with: n, R | without: n, R | diff t | 2022-24 with / without | 2025 with / without | kept |
|---|---|---|---|---|---|---|
| C1 continuation attempt (touch in the expansion's direction) | 630, +0.184 | 132, +0.016 | +1.48 | +0.093 / +0.142 | +0.468 / -0.228 | no |
| C2 yesterday closed at the extreme | 535, +0.130 | 227, +0.212 | -0.79 | +0.082 / +0.147 | +0.283 / +0.360 | no |
| C3 stretched 5 days (>= 1.5 ATR) | 318, +0.102 | 444, +0.192 | -0.94 | -0.031 / +0.185 | +0.406 / +0.217 | no |
| C4 daily RSI(2) extreme | 288, +0.108 | 474, +0.183 | -0.75 | -0.026 / +0.175 | +0.464 / +0.207 | no |
| C5 morning touch (before 12:00) | 405, +0.076 | 357, +0.244 | -1.79 | +0.073 / +0.135 | +0.088 / +0.502 | no |
| C6 slow approach | 481, +0.115 | 281, +0.223 | -1.04 | +0.103 / +0.095 | +0.153 / +0.527 | no |
| C7 isolated spike | 429, +0.096 | 333, +0.230 | -1.36 | +0.104 / +0.095 | +0.070 / +0.549 | no |

## Reading
- Six of the seven "obvious" exhaustion confluences make the fade WORSE on the pooled sample (C2-C7: the trades without them do
  better). The only one that looks better pooled, C1 (fading a second push in the expansion's direction), gets its whole
  advantage from 2025 and is worse in 2022-24: not consistent, so not kept.
- Splits of 130-630 trades out of a 762-trade, best-of-54 sample cannot separate structure from luck: the swings between
  periods (e.g. C5 +0.088 vs +0.502 in 2025) are larger than any difference the confluences produce.
- Descriptive only (not pre-registered): by market class I20 is +0.413 R on indices (136 trades), +0.122 on FX (534), slightly
  negative on metals and energy. A class choice would be one more selection on the same data.

## In the account's environment (I20 as is, in-sample 2022-25 trades, from 95,472, MT5 broker rules)
| sample | trades, R | 22 Dec | 31 Mar 2027 | 30 Jun 2027 |
|---|---|---|---|---|
| NSDQ + XAUUSD, $250 | 57, +0.309 | 0.0% / 0% | 0.0% / 0% | 0.0% / 0% |
| 38 markets, $50, <= 5 a day | 644, +0.078 | 0.0% / 0% | 0.0% / 0% | 0.0% / 0% |
| 38 markets, $250, <= 5 a day | 644, +0.078 | 0.0% / 2% | 0.1% / 11% | 0.8% / 16% |
(pass % / breach %). Even in-sample and at $250 a trade on every market, breach is 20 times more likely than a pass by mid-2027.

## Next
I20 goes to the 2020-21 out-of-time check unchanged (no confluence), on the main PC where the HistData files are. 2026 stays sealed.
