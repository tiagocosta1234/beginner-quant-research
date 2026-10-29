# The statistics behind the tests

The maths I kept needing during this project, written down so I can explain it, not just run it.
Every number here is checked by formula and by simulation in
[check_statistics.py](check_statistics.py) (`python docs/check_statistics.py`, about 20 seconds).

## 1. Why a 65% win rate can mean nothing

Take a trade with a stop 1R away and a target kR away, on a price with no drift. A driftless
random walk is a martingale: its expected value stays where it started. If p is the chance of
reaching the target first, then at the moment the trade ends

    p * k + (1 - p) * (-1) = 0    =>    p = 1 / (1 + k)

| target | chance of winning with no skill |
|---|---|
| 0.5R | 66.7% |
| 1R | 50% |
| 2R | 33.3% |

So "I win 65% of my trades" with a 0.5R target is slightly *worse* than a coin. Adding costs of c
(in R) per trade, break-even needs p * k - (1 - p) - c = 0, so p = (1 + c) / (1 + k). On micro gold
with a 2.8-point stop, costs are about 0.11R, so a 0.5R target needs **74%** wins just to break
even. That one line explains most of the failed intraday ideas in this repo.

The simulation lands within about 1 point of the formula. The gap is because the simulated walk
moves in small jumps and can jump past a line. Real prices gap too, which is one reason the
"stop assumed first" rule in [methods.md](methods.md) matters.

## 2. Random side versus a t-test

A t-test on the mean R of a rule asks "is the average trade above zero?". That is the wrong question
when the stop and target are asymmetric, or when the market drifts: a rule can have a positive mean
just from being long in a rising market.

The random-side test keeps everything about the trades (times, stops, targets, costs) and only
replaces the direction with a coin flip, thousands of times. The p-value is the share of coin-flip
copies that do at least as well as the real rule. It asks the right question ("does my *direction*
call add anything?"), and it needs no assumption about the shape of the returns.

It has a blind spot: if the rule is mostly long in a market that went up, it beats coin flips
because of the drift, not because of skill. That is why "always long" is a separate baseline.

## 3. Testing hundreds of ideas

If every idea is worthless and each is tested at the 5% level, the chance that at least one
"passes" is 1 - 0.95^m. For the 200+ tests in `forex/ea_research/`, that is 99.996%. In the
simulation, 8 of 200 pure-noise strategies had t above 1.645. One pass among hundreds of tries is
the expected result of luck.

What I did about it:

- **Fewer, pre-registered tests per idea**, each with the bar written down first.
- **A higher bar when there are variants.** The drift book had 4 variants, so the bar was one-sided
  5% / 4 = 1.25%, which is t ≥ 2.24 (the Bonferroni correction). D2 scored 2.42.
- **A hold-out opened once.** It is the only check that the luck from all the earlier choices
  can't reach.

What I didn't do, and should learn next: corrections that use the number of all ideas ever tried,
not just the variants of one (for example the deflated Sharpe ratio).

## 4. How much a Sharpe ratio is worth

For daily returns that are roughly independent, the standard error of an annualised Sharpe ratio
is about 1 / sqrt(years), and t ≈ Sharpe × sqrt(years).

| result | years | t |
|---|---|---|
| drift book hold-out, Sharpe 0.9 | 0.75 | 0.78 |
| one year at Sharpe 0.9 | 1 | 0.90 |
| drift book on free data since 2010, Sharpe 0.87 | 16.8 | 3.57 |

So the 2026 hold-out "passing" says very little on its own: a Sharpe 0.9 result over nine months is
well within noise. It was only meant to catch a result that collapsed, not to prove anything. The
16.8-year rerun is strong evidence that the book's return is above zero, but that return is mostly
a risk premium (being long stocks and gold), not a forecasting edge.

The same maths says what to expect when it is real: with a true Sharpe of 0.9 and normal
returns, a year loses money with probability Φ(-0.9) ≈ 18%, about one year in five.

## What I'd still like to learn

Time-series dependence (none of the above holds when returns are autocorrelated or volatility
clusters, and both happen), bootstrap methods that respect it (block bootstrap), and proper
multiple-testing control (Holm, false discovery rate, deflated Sharpe).
