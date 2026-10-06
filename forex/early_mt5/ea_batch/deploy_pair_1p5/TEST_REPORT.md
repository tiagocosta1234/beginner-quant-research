# Test report -- the pair at 1.5 x on an MT5 broker 2-Step account (2026-10-06)

Everything below was run in this repo; scripts are named in each section. "Replay" = the equity-aware replay on the 2022-2026 real-tick tester runs (equity rebuilt on MT5 broker 1-minute bid / ask bars, both EAs on one
clock). MT5 broker 2-Step: +10% then +5%, 5% daily loss, static 10% floor, >= 4 trading days per phase, no time limit. A test is started on every weekday 2022-2026 and runs until it passes or breaches.

## 1. Do the loadable lots reproduce the replay's sizes? (`verify_scaled.py`, real-tick Strategy Tester)
Stochastic Daily Breakout at 0.31 lots and XAUUSD 5 minute at 0.10 lots, every year, against 31 x / 10 x the 0.01-lot runs:

| EA | Year | Deals (tester / baseline) | Net ratio | Equity-DD ratio | Daily P&L correlation |
|---|---|---|---|---|---|
| Stochastic 0.31 | 2026 / 2025 / 2024 / 2023 / 2022 | 86/86, 88/88, 74/74, 68/68, 78/78 | 0.997 / 0.982 / 0.907 / 1.002 / 0.995 | 1.002 / 1.008 / 1.027 / 1.001 / 1.000 | 1.00 |
| XAU5min 0.10 | 2026 / 2025 / 2024 / 2023 / 2022 | 814/814, 712/712, 574/574, 490/490, 638/638 | 0.997 / 0.987 / 0.971 / 0.918 / 1.080 | 1.003 / 1.002 / 1.007 / 1.021 / 1.023 | 1.00 |

Ladder lots in 2026: Stochastic 0.21 / 0.10 and XAU5min 0.07 / 0.03 also scale exactly (net ratio 0.997). The net-ratio gaps in 2022-2024 are small-net years (differences under $500, commission rounding at 0.01 lots in the baseline).

## 2. Stress tests on 2-Step (`pair_stress.py`), loadable lots, no deadline, all starts
| Case | Pass | Breach | Median trading days to finish both phases |
|---|---|---|---|
| Both at exactly 1.5 | 51% | 49% | 58 |
| Loadable 0.31 / 0.10 | 54% | 46% | 58 |
| + $15 / $30 / $60 per lot per side (worse broker) | 53% / 49% / 46% | 47% / 51% / 54% | 61 / 64 / 67 |
| MT5 broker's daily reset at Prague midnight (server - 1 h) | 54% | 46% | 58 |
| Everything: lots + $30 + Prague | 49% | 51% | 64 |
| Block bootstrap of the daily results (20-day blocks, 150 paths) | 57% | 41% (2% open) | up to 500 days |

Scale grid (exact scales, no guard): 1.0 -> 66% / 33%; 1.25 -> 58% / 42%; 1.5 -> 51% / 49%; 2.0 -> 31% / 69%.

## 3. A daily guard does not lower 2-Step breaches
Day guard at 2.5% / 3% / 4% of $100K: pass 42% / 49% / 51%, breach 57% / 51% / 49% at 1.5 x (126 / 78 / 24 day stops over 1,225 trading days). Breaches come from the slide to the static -10% floor, not from one bad day, so the guard
is a safety net (gaps, runaway EAs, slippage), not a way to pass more often. With the loadable lots, extra costs and Prague days the 4% guard lowers the pass rate by 1-4 points (54 -> 52, 53 -> 49 at +$15, 49 -> 48 at +$30, 46 -> 45 at +$60).

## 4. What does lower breaches: de-risk after a drawdown (`pair_ladder.py`, ladders fixed before the run)
Step is chosen from the previous day's balance relative to the phase start (dd), lots in brackets (Stochastic / XAU5min):

| Ladder | All starts pass / breach (median days) | Starts 2022-23 | Starts 2024+ | Same with +$30 and Prague days |
|---|---|---|---|---|
| L0 constant 1.5x (0.31 / 0.10) | 54% / 46% (58) | 18% / 82% | 82% / 18% | 49% / 51% |
| LA 1.5 / 1.0 / 0.5 at -3% / -6% | 65% / 35% (65) | 26% / 74% | 96% / 4% | 61% / 39% |
| **LB 1.5 / 1.0 / 0.6 / 0.3 at -2% / -4% / -6%** (0.31 / 0.21 / 0.12 / 0.06 and 0.10 / 0.07 / 0.04 / 0.02) | **72% / 28% (75)** | 43% / 57% | 95% / 4% | **69% / 31%** |
| LC = LA + 1.0x once +6% ahead | 64% / 35% (68) | 25% / 75% | 95% / 4% | 59% / 41% |

Constant smaller scales for comparison (no ladder): 0.4 -> 93% / 0% (302 days); 0.5 -> 91% / 4% (230); 0.6 -> 86% / 10% (168); 0.8 -> 76% / 22% (124); 1.0 -> 67% / 32% (92). With +$30 and Prague days: 0.5 -> 83% / 12% (224).
So a 1.5 x start with ladder LB roughly halves the breach rate of constant 1.5 x but does not come close to constant 0.4-0.5 x; what it buys is time (75 trading days instead of 230-300).

## 5. AccountGuard in the real-tick tester (`verify_guard.py`, `verify_guard2.py`; `GuardSelfTest.mq5` = the guard code + a stubborn driver)
The real EAs cannot be run together with the guard in one tester run, so the guard code was tested with a driver that opens 1.0 lot XAUUSD on a schedule and retries every 10 s whenever flat, even while stopped (a worst case).

| Test | Result |
|---|---|
| G4 guard on, thresholds that cannot trigger | identical to guard off: net -11,510.81 vs -11,510.81, 1,400 deals each (the guard does not interfere) |
| Day stop 4% | fired when equity was 4.01% below the day's reference; 3,100 of 3,100 re-opens during the stop were closed within 3 s |
| Emergency stop (floor 1.5% in the test) | fired at equity 98,497 against 98,500; 2,539 of 2,539 re-opens closed within 3 s |
| Day boundary | new day at server 01:05 (Prague midnight + the first quote) in the March 2025 run |
| Pass lock, minimum 4 trading days | did NOT fire on days 1-3 although equity was above target (correct) |
| Pass lock, minimum 1 day, target 0.5% + 0.3% | fired at equity 100,801 with balance 100,801 (positions closed so the balance holds the profit) |
| **Finding: the re-open churn** | without a kill switch the retrying driver bled the account from about $93.5K to $1.2K through spread, although every open was closed fast |
| **Kill switch (3 forced closes, then stop the EA)** | day stop run ended at $93,418 (cost $140); emergency run lowest $98,339 (cost $158); lock run $100,736 (cost $65) |

Not exercised: the live `TerminalClose(0)` call (the tester run used `ExpertRemove()` for the same hook), the interaction with the real XAUUSD 5 minute (closed source) and Stochastic EAs, and VPS restarts.
The real EAs trade far less often than the test driver (about 5 and 45 trades a month), so the churn cost is much smaller than in the worst case, but the kill switch is the safeguard.

## 6. Not tested / open
MT5 broker's rules for third-party and Market EAs (in writing); live execution versus the tester (forward test on demo); a different gold regime; margin/requote behaviour beyond the tester's model; the Market EA's licence on the target account.
