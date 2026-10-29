# futures/strategies

Write-ups of the strategies that got furthest in the futures phase, each with its rules, its
backtest numbers and why it was not trusted with money:

- `live_ready/manual_tod_vwapz.md`: the time-of-day filter plus VWAP-Z combination run by the live
  bot's `manual` strategy.
- `live_ready/support_resistance_bounce_mgc.md`: the micro-gold support/resistance bounce.
- `promising/meta_labeling_poc_round198.md`: point-of-control reversion with a meta-label filter
  (engine round 198), the basis of the live bot's `combined` strategy.

"Live ready" meant the code was wired into the live bot for practice runs, not that the edge held
out of sample.
