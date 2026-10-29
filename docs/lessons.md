# Lessons

Short notes from the research and from the trading videos that were tested along the way. Each
one cost at least one wrong turn.

## About edges

- **Expect no edge.** The base rate for a new intraday rule was a small loss per trade, about the
  size of the trading costs. A result had to beat that, a random-side copy and a hold-out before
  it meant anything.
- **Direction is hard, size is not.** On Nasdaq futures, whether the first 30 minutes were up
  told you almost nothing about the rest of the day (about 54%, with 50% inside the error bars).
  How big the rest of the day would be was predictable: quiet mornings led to quiet days.
- **Win rate is not skill.** A 70% win rate at a 0.5R target is close to what a coin flip gives.
  Judge a rule by its average result after costs against a random baseline, not by how often it
  wins.
- **Slow premia beat fast tricks.** The only thing that passed every bar was a slow, long-only,
  trend-filtered drift book that needs overnight holding. See [swap-costs.md](swap-costs.md).
- **Costs decide intraday.** On a tight stop, a fixed per-contract cost is a big slice of each
  trade. Wider stops cost less in R but change the trade. Count costs in R before anything else.

## About testing

- **Write the bar down first.** Every result that was judged after seeing it looked better than
  it was. Pre-registration with a committed hash removed the temptation.
- **One look at the hold-out.** Re-opening a hold-out "just to check" turns it into training data.
- **Best-of-hundreds is not an edge.** Video claims like "+982% after hundreds of backtests" are
  the best of many tries; tested the same way, both video setups checked here (a New York 30-minute
  box breakout and a first-5-minute candle versus the 12 EMA) passed 0 of 4 variants.
- **Hindsight charts prove nothing.** A trade drawn on the chart after the move, with no account
  statement, is a picture, not a record.
- **Automated research finds noise too.** The self-improving loop found "edges" in placebo worlds
  as often as in real data; its survivors were noise until shown otherwise.
- **A few big days carry most strategies.** Several rules had a negative median day and a
  positive mean, which is fragile: miss a handful of days and the edge is gone.

## About software

- **Take numbers from the source of truth.** A bot once used a balance frozen at login; another
  read every position on the account and flattened a trade it did not own.
- **Refuse the trade that can cross the line.** A daily stop that only acts after a loss cannot
  stop the trade that breaks it; check the worst case before entering.
- **Clocks lie twice a year.** For two weeks in spring and autumn, the US and Europe change clocks
  on different dates; session times in UTC move by an hour.
- **A rule card has to fit on a card.** Entry, stop, target, size. If it does not fit, it cannot
  be coded, tested or followed.
