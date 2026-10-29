# The journey: futures, forex, and back to futures

This is the story of five months of beginner quant research (June to October 2026), told in the
order it happened. The commit history of this repo is the same story in detail: the old commits
were kept with their original dates.

## 1. June: a simulation environment for Nasdaq futures

The first commit (23 June 2026) is a small Python backend for simulating MNQ (micro Nasdaq
futures) trades from order-flow data (`futures/early_sim/`, now only in the history). It answered
nothing yet, but it set
the habit that stayed for the whole project: write the rule down as code, run it on history, and
look at the numbers before believing anything.

## 2. July to September: the futures research engine

Most of the futures work lives in `futures/engine/` as numbered "rounds" (one script and one
result per idea), with older experiments in `futures/_archive/`. NinjaScript strategies
(`futures/ninjascript/`) and a reinforcement-learning scalper (`futures/ai_research/`) were built
in this period and later deleted; they remain in the commit history.

The ideas covered the usual intraday playbook on NQ/MNQ, ES, GC/MGC and SI: opening-range
breakouts, VWAP z-score fades, support and resistance bounces, value-area and point-of-control
reversion, fair-value gaps and OTE retracements, time-of-day filters, and machine-learning
filters on top of them. The data was CME 1-minute bars, so costs (fees plus one tick of
slippage) could be modelled per contract.

In September a live bot was built around the best candidates (`futures/live_bot/`) and run on a
practice account. It worked as software: risk limits, fills, reconciliation and tests. As
trading, none of the strategies kept an edge once tested on data they had not been tuned on.

## 3. Late September to October: forex and CFDs on MetaTrader 5

At the end of September the research moved to an MT5 account (`forex/`). Three things made the
switch attractive:

- **One terminal, many markets.** Forex pairs, gold and silver, stock indices, oil and crypto,
  all with the same tools, which made it cheap to test an idea across dozens of markets at once.
- **A strategy tester.** Expert advisors (EAs) could be run in batches on tick data
  (`forex/ea_batch/`, `forex/expert_advisors/`), and every Python result could be checked
  against MT5's own tester.
- **Swap-free holding.** The account charged no overnight swap, which opened a whole family of
  slow ideas that simply do not work when holding costs money. That turned into the one result
  in this repo that passed all of its bars; see [swap-costs.md](swap-costs.md).

The forex period is the densest part of the repo: more than 200 written results in
`forex/ea_research/` (see its [INDEX.md](../forex/ea_research/INDEX.md)), blind chart-reading
tests in `forex/apprentice/`, and an automated "self-improving" research loop in
`forex/self_improving/` that was tested against placebo (fake-signal) worlds.

## 4. Late October: back to futures

The MT5 account ended in late October, and the last week went back to CME futures, mostly micro
gold (MGC) at the London open (`futures/london_open_gold/`): a London-open indicator, a Tokyo
session test on MNQ, and a pre-registered test of a half-R (0.5 reward-to-risk) discretionary
setup played on replayed history. Futures have one central exchange, clean historical data and
fees you can count to the cent, which made the cost questions easy to answer honestly.

## What came out of it

- **No fast intraday edge survived** realistic costs and out-of-sample testing, in either
  market. Across roughly 1,400 logged tests the typical result was a small loss per trade that
  matched the cost of trading.
- **Direction at the open is close to a coin flip.** Model after model (rules, gradient boosting,
  hand-made reads) scored around 50% on direction once tested honestly. Volatility, on the other
  hand, was predictable.
- **Win rates follow the target.** For a stop of 1 and a target of k, the win rate came out close
  to 1/(1+k) (49/39/33/28% at 1, 1.5, 2 and 3R), which is what a random walk gives. A high win
  rate at a small target is not evidence of skill by itself.
- **The one slow edge that passed** was a long-only, trend-filtered "drift" book that only works
  when holding positions overnight is free. That is the forex-to-futures difference in one line,
  explained in [swap-costs.md](swap-costs.md).
- **The method mattered more than any idea.** Pre-registering each test, keeping a hold-out
  period unopened, and comparing against a random-side baseline killed many results that looked
  great in-sample. See [methods.md](methods.md) and [lessons.md](lessons.md).
