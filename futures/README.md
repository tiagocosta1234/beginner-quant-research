# futures/

CME futures research: Nasdaq (NQ/MNQ), S&P 500 (ES/MES), gold (GC/MGC), silver and a few others,
mostly on 1-minute bars with exchange fees and one tick of slippage per round trip.

| folder | what it holds |
|---|---|
| `engine/` | the main research engine, one numbered round per idea; see [engine/INDEX.md](engine/INDEX.md) |
| `london_open_gold/` | the last week (October 2026): London-open gold rule, Tokyo MNQ test, half-R comparison; see its [README](london_open_gold/README.md) |
| `live_bot/` | the live-trading scaffold that ran on a practice account; see its [README](live_bot/README.md) |
| `_archive/` | earlier experiments: a testing suite, NinjaTrader strategy backups, Pine scripts, a knowledge-graph export |
| `docs/` | design notes (AI bridge, meta-labeling plan, idea ledger) and a backtesting journal export |
| `strategies/`, `experiments/` | a few standalone strategy and experiment files |

Earlier futures work that was later deleted from the working tree is still in the commit history:
the first MNQ simulation backend (June 2026, `futures/early_sim/`), a reinforcement-learning
scalper (`futures/ai_research/`) and NinjaScript strategies (`futures/ninjascript/`).

## Main findings

- Opening-range, VWAP z-score, support/resistance, value-area and fair-value-gap rules all showed
  in-sample leads that faded out of sample; the strongest (point-of-control reversion and
  value-area rejection on NQ, rounds 178-186) were the closest misses.
- Meta-labeling (a model that decides which signals to take) improved in-sample numbers and did
  not survive a clean out-of-sample test.
- At the micro-contract level, costs are 10-16% of a typical intraday risk unit, which is larger
  than most of the gross edges found.
