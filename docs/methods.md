# Methods

Most ideas in this repo failed. These are the habits that made the failures trustworthy, and
caught the few results that only looked good.

## Pre-registration

Every serious test starts with a `PREREG_*.md` file written before any result is computed:
the rule, the data, the cost model, the split into periods, and the exact bar a result must
clear. The file was committed (and its hash recorded) before the run, so the bar could not move
after seeing the numbers. Amendments were allowed only before any P&L was looked at, and were
written down as amendments. A test is scored once; a "nearly passed" result stays failed.

Each result has a matching `*_RESULT.md` (or `*_OUTPUT.txt`) next to its prereg. The indexes
(`forex/ea_research/INDEX.md`) list them by family with the verdict.

## Splits and hold-outs

- **DEV**: the period where ideas may be tuned.
- **VAL**: a later period used to confirm the DEV pick, with no further tuning.
- **OOT** (out of time): an earlier period or another data source, as an extra check.
- **HOLD**: the most recent months, kept unopened until a rule passed everything else, then
  opened exactly once.

Walk-forward variants refit only on data before each test window. Several "great" results died
at VAL or HOLD; the closest misses were logged and never reopened.

## Baselines that a result has to beat

- **Random side.** The same entries with a coin-flip direction, thousands of times. If the real
  rule does not beat most coin-flip copies, the direction carries no skill.
- **Random-walk win rates.** With a stop of 1 and a target of k, a random walk wins about
  1/(1+k) of the time. A 65% win rate at a 0.5R target is what chance gives.
- **Always long** (for markets with drift) and **naive versions** of the same idea.
- **Placebo worlds** for the automated research loop: shuffled or synthetic markets where no
  edge can exist. Any "edge" the loop found there showed how often it finds noise.
- **Truncation checks**: rerunning with the last part of the data cut off, to catch results that
  depend on a handful of days.

## Costs

Every result is net of realistic costs. On CME micros that means the exchange and broker fees
plus one tick of slippage per round trip (about 0.32 points on micro gold, $3.20 per contract).
On MT5 it means the broker's actual bid/ask spread at the time of the trade and, for held
positions, the swap. Costs are counted in R (risk units): on a 2.8-point gold stop, 0.32 points
is already 0.11R, which is why tight-stop intraday ideas struggle.

## Look-ahead and data checks

- Signals use only bars that were closed at the time of the decision; higher-timeframe values
  are taken from the previous completed candle.
- When a stop and target are touched in the same bar, the stop is assumed first.
- Results were cross-checked between data sources (futures versus CFD prices, two data vendors)
  and against the MT5 tester for EAs.
- Clock and time-zone handling was checked explicitly; one daylight-saving bug moved timestamps
  by an hour during the US/EU clock-change gap and was fixed in every affected script.

## Blind tests for discretionary reads

Chart-reading skill (`forex/apprentice/`, `forex/ea_research/ema12/`) was tested blind: a local
replay app served one bar at a time, never a future bar, and logged each decision before the
next bar was shown. Days were drawn at random from a sealed pool. A read counted as skill only if
it beat the random-side baseline on days nobody had looked at.
