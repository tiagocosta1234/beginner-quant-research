# Apprentice: blind chart reading and the 1-minute open

Despite living under `forex/`, most of this folder tests gold at the London open on futures data
(GC, 2019-2026), with a few CFD and index checks. The question throughout was whether a human (or
an AI) reading the 1-minute chart at the open can pick the day's direction better than chance.

## How the blind tests worked

- **Rules card first.** `desk.py` holds the rules card (one trade a day, entry between 08:00 and
  08:15 London, a fixed stop-and-target bracket) and a grading rubric for each setup.
- **One bar at a time.** Days were drawn at random from a sealed pool; the replay showed one bar
  at a time and logged each call (side, stop, target, time) before revealing the next bar.
- **Scored against chance.** Every read was compared with a random-side copy of the same trades
  and with simple mechanical rules on the same days (`manual_read_baselines.py`).
- **Pre-registered.** Each test has a `PREREG_*.md` with the bar, written and committed first;
  amendments were only made before any result was seen.

## What was found

| test | result |
|---|---|
| The grading rubric coded and run over 2020-2025 (`rubric_backtest.py`) | 632 trades, 50.6% wins at 1:1, -0.114 R a trade |
| Read v9 on 100 blind days (`READ_TEST2_RESULT.md`) | +0.093 R, P 0.038 against a bar of 0.03: not shown |
| The same frozen rules on 100 fresh days from 2020-21 (`PREREG_READ_TEST3.md`) | +0.026 R, P 0.167: replication failed |
| A 1:1 read trained on 40 days, scored on 150 sealed days (`READ11.md`) | no skill in training; naive rule -0.135 R |
| The same on recent 2026 gold (`READ12.md`) | +0.053 R, P 0.26: not shown |
| A London EMA12 "A+" rule, 313 trades 2019-2026 (`LONDON12_APLUS_OUTPUT.txt`) | 56% wins, -0.023 R net; side choice beat random (P 0.012) but costs ate the +0.08 R gross |
| Direction models on 81 features, walk-forward (`ML_DIRECTION2_OUTPUT.txt`) | AUC 0.49-0.51, every cell negative after costs |
| Higher targets (`HIGHER_RR_OUTPUT.txt`) | win rates 49 / 39 / 33 / 28% at 1 / 1.5 / 2 / 3 R, what a random walk gives |
| Published effects (`PUBLISHED_EFFECTS_OUTPUT.txt`, `TOM_HOLDOUT_OUTPUT.txt`) | the overnight drift had faded since 2021; a turn-of-month result failed its 1993-2019 hold-out |

The honest summary: on 1-minute gold at the London open, direction is close to a coin flip for
rules, models and hand reads alike, and a 0.1 R cost per trade turns a coin flip negative. The
one lead (the A+ rule's side choice) is real but smaller than the cost of trading it with tight
stops.

## Notable files

- `LESSONS.md`, `BIAS8_LESSONS.md`, `FXR_CLAUDE_LESSONS.md`: running lessons from the blind sessions
- `MANUAL_READ.md`, `PROTOCOL_DAILY_READ.md`: the manual reading protocol
- `edge_lab/`: the shared backtest helpers (data loading, costs, random-side tests, ML features)
- `*.pine`: TradingView versions of the rules; `bias.js`, `b8view.py`: small chart helpers
- `phase3_blind/`, `state_*`: blind-test sessions and the replay app's saved state
